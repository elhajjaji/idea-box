from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Optional
import csv
import io
from bson import ObjectId

from src.models.user import User
from src.models.subject import Subject
from src.services.auth_service import get_current_user, get_password_hash
from src.services.user_service import create_user, get_users, add_role_to_user, remove_role_from_user
from src.services.database import Database
from src.services.metrics_service import MetricsService

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "templates"))

async def get_current_superadmin(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, detail="Not authenticated", headers={"Location": "/auth/login"})
    if "superadmin" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits de superadmin")
    return current_user

@router.get("/superadmin/dashboard", response_class=HTMLResponse)
async def superadmin_dashboard(request: Request, current_user: User = Depends(get_current_superadmin)):
    # Récupérer les métriques pour le superadmin
    metrics = await MetricsService.get_superadmin_dashboard_metrics()
    
    users = await get_users()
    subjects = await Database.engine.find(Subject)
    # Create a new list of subjects with string IDs
    subjects_for_template = []
    for subject in subjects:
        subject_dict = subject.dict()
        subject_dict["id"] = str(subject.id)
        subjects_for_template.append(subject_dict)
    user_emails = {str(user.id): user.email for user in users}
    
    # Préparer le contexte avec les informations de l'organisation
    from src.utils.template_helpers import add_organization_context
    context = {
        "request": request, 
        "users": users, 
        "subjects": subjects_for_template, 
        "current_user": current_user, 
        "user_emails": user_emails, 
        "metrics": metrics,
        "show_sidebar": True
    }
    
    # Ajouter les informations de l'organisation
    context = await add_organization_context(context)
    
    return templates.TemplateResponse("superadmin/dashboard.html", context)

@router.get("/superadmin/users/add", response_class=HTMLResponse)
async def add_user_form(request: Request, current_user: User = Depends(get_current_superadmin)):
    # Récupérer tous les sujets pour les afficher dans le formulaire
    subjects = await Database.engine.find(Subject)
    subjects_for_template = []
    for subject in subjects:
        subject_dict = subject.dict()
        subject_dict["id"] = str(subject.id)
        subjects_for_template.append(subject_dict)
    
    from src.utils.template_helpers import add_organization_context
    context = await add_organization_context({
        "request": request, 
        "current_user": current_user, 
        "subjects": subjects_for_template,
        "show_sidebar": True
    })
    return templates.TemplateResponse("superadmin/add_user.html", context)

@router.post("/superadmin/users/add", response_class=HTMLResponse)
async def add_user(
    request: Request, 
    email: str = Form(...), 
    nom: str = Form(...), 
    prenom: str = Form(...), 
    password: str = Form(...),
    roles: List[str] = Form(default=["user"]),
    managed_subjects: List[str] = Form(default=[]),
    current_user: User = Depends(get_current_superadmin)
):
    try:
        # Vérifier que l'email n'est pas déjà utilisé
        existing_user = await Database.engine.find_one(User, User.email == email)
        if existing_user:
            from src.utils.flash_messages import flash
            flash(request, "Cette adresse email est déjà utilisée.", "error")
            return RedirectResponse(url="/superadmin/users/add", status_code=303)

        # Validation: si gestionnaire est sélectionné, au moins un sujet doit être assigné
        if "gestionnaire" in roles and not managed_subjects:
            from src.utils.flash_messages import flash
            flash(request, "Un gestionnaire doit avoir au moins un sujet assigné.", "error")
            return RedirectResponse(url="/superadmin/users/add", status_code=303)

        # Créer l'utilisateur
        hashed_password = get_password_hash(password)
        user = User(
            email=email.strip().lower(),
            nom=nom.strip(),
            prenom=prenom.strip(),
            pwd=hashed_password,
            roles=roles
        )
        await create_user(user)
        
        # Si l'utilisateur est gestionnaire, l'ajouter aux sujets sélectionnés
        if "gestionnaire" in roles and managed_subjects:
            user_id = str(user.id)
            for subject_id in managed_subjects:
                try:
                    subject = await Database.engine.find_one(Subject, Subject.id == ObjectId(subject_id))
                    if subject:
                        # Ajouter l'utilisateur comme gestionnaire du sujet
                        if user_id not in subject.gestionnaires_ids:
                            subject.gestionnaires_ids.append(user_id)
                        # Ajouter aussi l'utilisateur aux utilisateurs du sujet
                        if user_id not in subject.users_ids:
                            subject.users_ids.append(user_id)
                        await Database.engine.save(subject)
                except Exception as e:
                    print(f"❌ Erreur lors de l'ajout du gestionnaire au sujet {subject_id}: {e}")

        from src.utils.flash_messages import flash
        flash(request, f"L'invité {prenom} {nom} a été créé avec succès.", "success")
        return RedirectResponse(url="/superadmin/users", status_code=303)
        
    except Exception as e:
        print(f"❌ Erreur lors de la création de l'utilisateur: {e}")
        from src.utils.flash_messages import flash
        flash(request, "Erreur lors de la création de l'utilisateur.", "error")
        return RedirectResponse(url="/superadmin/users/add", status_code=303)

@router.get("/superadmin/users/import", response_class=HTMLResponse)
async def import_users_form(request: Request, current_user: User = Depends(get_current_superadmin)):
    from src.utils.template_helpers import add_organization_context
    context = await add_organization_context({"request": request, "current_user": current_user})
    return templates.TemplateResponse("superadmin/import_users.html", context)

@router.post("/superadmin/users/import", response_class=HTMLResponse)
async def import_users(request: Request, file: UploadFile = File(...), current_user: User = Depends(get_current_superadmin)):
    from src.utils.template_helpers import add_organization_context
    
    if not file.filename.endswith(".csv"):
        context = await add_organization_context({
            "request": request, 
            "current_user": current_user, 
            "error": "Veuillez télécharger un fichier CSV."
        })
        return templates.TemplateResponse("superadmin/import_users.html", context)

    content = await file.read()
    csv_file = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(csv_file)
    
    imported_count = 0
    errors = []

    for row in reader:
        try:
            email = row["email"]
            nom = row["nom"]
            prenom = row["prenom"]
            password = row["password"]

            existing_user = await Database.engine.find_one(User, User.email == email)
            if existing_user:
                errors.append(f"L'utilisateur avec l'email {email} existe déjà.")
                continue

            hashed_password = get_password_hash(password)
            user = User(email=email, nom=nom, prenom=prenom, pwd=hashed_password)
            await create_user(user)
            imported_count += 1
        except KeyError as e:
            errors.append(f"Colonne manquante dans le fichier CSV: {e}. Assurez-vous d'avoir les colonnes 'email', 'nom', 'prenom', 'password'.")
        except Exception as e:
            errors.append(f"Erreur lors de l'importation de la ligne {row}: {e}")

    from src.utils.template_helpers import add_organization_context
    context = await add_organization_context({
        "request": request,
        "current_user": current_user,
        "message": f"{imported_count} utilisateurs importés avec succès.",
        "errors": errors
    })
    return templates.TemplateResponse("superadmin/import_users.html", context)

@router.get("/superadmin/subjects/create", response_class=HTMLResponse)
async def create_subject_form(request: Request, current_user: User = Depends(get_current_superadmin)):
    from src.utils.template_helpers import add_organization_context
    users = await get_users()
    context = await add_organization_context({
        "request": request,
        "current_user": current_user,
        "users": users
    })
    return templates.TemplateResponse("superadmin/create_subject.html", context)

@router.post("/superadmin/subjects/create", response_class=HTMLResponse)
async def create_subject(request: Request, name: str = Form(...), description: Optional[str] = Form(None), gestionnaires_ids: List[str] = Form([]), current_user: User = Depends(get_current_superadmin)):
    subject = Subject(name=name, description=description, superadmin_id=str(current_user.id), gestionnaires_ids=gestionnaires_ids)
    await Database.engine.save(subject)

    # Correction robuste : vérifie l'existence de chaque utilisateur avant d'ajouter le rôle
    for user_id in gestionnaires_ids:
        try:
            user = await Database.engine.find_one(User, User.id == ObjectId(user_id))
        except Exception as e:
            print(f"[ERREUR] Mauvais format d'ID pour gestionnaire : {user_id} ({e})")
            continue
        if user:
            if "gestionnaire" in user.roles:
                print(f"[INFO] L'utilisateur {user.email} (id={user.id}) a déjà le rôle gestionnaire.")
            else:
                result = await add_role_to_user(str(user.id), "gestionnaire")
                if not result:
                    print(f"[ERREUR] Impossible d'ajouter le rôle gestionnaire à l'utilisateur {user.email} (id={user.id})")
        else:
            print(f"[ERREUR] Utilisateur non trouvé pour l'id {user_id}")

    return RedirectResponse(url="/auth/logout", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/superadmin/subjects/{subject_id}/edit", response_class=HTMLResponse)
async def edit_subject_form(subject_id: str, request: Request, current_user: User = Depends(get_current_superadmin)):
    try:
        from src.utils.template_helpers import add_organization_context
        subject = await Database.engine.find_one(Subject, Subject.id == ObjectId(subject_id))
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé")
        
        users = await get_users()
        context = await add_organization_context({
            "request": request, 
            "subject": subject, 
            "users": users, 
            "current_user": current_user
        })
        return templates.TemplateResponse("superadmin/edit_subject.html", context)
    except Exception as e:
        context = await add_organization_context({
            "request": request, 
            "error": f"Erreur: {e}", 
            "current_user": current_user
        })
        return templates.TemplateResponse("superadmin/edit_subject.html", context)

@router.post("/superadmin/subjects/{subject_id}/edit", response_class=HTMLResponse)
async def edit_subject(subject_id: str, request: Request, name: str = Form(...), description: Optional[str] = Form(None), gestionnaires_ids: List[str] = Form([]), current_user: User = Depends(get_current_superadmin)):
    try:
        subject = await Database.engine.find_one(Subject, Subject.id == ObjectId(subject_id))
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé")
        
        # Update subject
        subject.name = name
        subject.description = description
        
        # Remove gestionnaire role from users who are no longer gestionnaires
        for old_gestionnaire_id in subject.gestionnaires_ids:
            if old_gestionnaire_id not in gestionnaires_ids:
                # Check if user is gestionnaire of other subjects
                other_subjects = await Database.engine.find(Subject, {"gestionnaires_ids": {"$in": [old_gestionnaire_id]}, "_id": {"$ne": subject.id}})
                if not other_subjects:
                    # Remove gestionnaire role if not gestionnaire of other subjects
                    await remove_role_from_user(old_gestionnaire_id, "gestionnaire")
        
        subject.gestionnaires_ids = gestionnaires_ids
        await Database.engine.save(subject)
        # Ajout du rôle gestionnaire à tous les gestionnaires sélectionnés (en parallèle)
        import asyncio
        await asyncio.gather(*(add_role_to_user(user_id, "gestionnaire") for user_id in gestionnaires_ids))

        # Force re-authentication to update roles in JWT
        # return RedirectResponse(url="/auth/logout", status_code=status.HTTP_303_SEE_OTHER) # Commented out for now

        # Re-fetch users and subject to pass updated data to template
        users = await get_users()
        subject = await Database.engine.find_one(Subject, Subject.id == ObjectId(subject_id)) # Re-fetch subject to get updated gestionnaires_ids

        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "subject": subject,
            "users": users,
            "message": "Sujet modifié avec succès !",
            "current_user": current_user
        })
        return templates.TemplateResponse("superadmin/edit_subject.html", context)
    except Exception as e:
        from src.utils.template_helpers import add_organization_context
        users = await get_users()
        context = await add_organization_context({
            "request": request, 
            "error": f"Erreur: {e}", 
            "users": users, 
            "current_user": current_user
        })
        return templates.TemplateResponse("superadmin/edit_subject.html", context)

@router.get("/superadmin/users", response_class=HTMLResponse)
async def superadmin_users(request: Request, current_user: User = Depends(get_current_superadmin)):
    from src.utils.template_helpers import add_organization_context
    users = await get_users()
    subjects = await Database.engine.find(Subject)
    # Correction : Afficher les deux rôles même si c'est sur les mêmes sujets
    user_subject_stats = {}
    for user in users:
        user_id = str(user.id)
        managed_subjects = [s.name for s in subjects if user_id in s.gestionnaires_ids]
        invited_subjects = [s.name for s in subjects if user_id in s.users_ids]
        nb_gestionnaire = len(managed_subjects)
        nb_invite = len(invited_subjects)
        user_subject_stats[user_id] = {
            "nb_gestionnaire": nb_gestionnaire,
            "nb_invite": nb_invite,
            "managed_subjects": managed_subjects,
            "invited_subjects": invited_subjects
        }
    context = await add_organization_context({
        "request": request,
        "users": users,
        "user_subject_stats": user_subject_stats,
        "current_user": current_user
    })
    return templates.TemplateResponse("superadmin/users.html", context)

@router.get("/superadmin/subjects", response_class=HTMLResponse)
async def superadmin_subjects(request: Request, current_user: User = Depends(get_current_superadmin)):
    from src.utils.template_helpers import add_organization_context
    subjects = await Database.engine.find(Subject)
    # Create a new list of subjects with string IDs
    subjects_for_template = []
    for subject in subjects:
        subject_dict = subject.dict()
        subject_dict["id"] = str(subject.id)
        subjects_for_template.append(subject_dict)
    users = await get_users()
    user_emails = {str(user.id): user.email for user in users}
    context = await add_organization_context({
        "request": request, 
        "subjects": subjects_for_template, 
        "current_user": current_user, 
        "user_emails": user_emails
    })
    return templates.TemplateResponse("superadmin/subjects.html", context)

@router.get("/superadmin/settings", response_class=HTMLResponse)
async def superadmin_settings(request: Request, current_user: User = Depends(get_current_superadmin)):
    from src.utils.template_helpers import add_organization_context
    context = await add_organization_context({
        "request": request, 
        "current_user": current_user
    })
    return templates.TemplateResponse("superadmin/settings.html", context)

@router.get("/superadmin/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(user_id: str, request: Request, current_user: User = Depends(get_current_superadmin)):
    """Formulaire de modification d'un utilisateur"""
    try:
        # Convertir l'ID string en ObjectId
        user_to_edit = await Database.engine.find_one(User, User.id == ObjectId(user_id))
        if not user_to_edit:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        # Récupérer tous les sujets pour les afficher dans le formulaire
        subjects = await Database.engine.find(Subject)
        subjects_for_template = []
        for subject in subjects:
            subject_dict = subject.dict()
            subject_dict["id"] = str(subject.id)
            subjects_for_template.append(subject_dict)
        
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "user_to_edit": user_to_edit,
            "subjects": subjects_for_template,
            "show_sidebar": True
        })
        return templates.TemplateResponse("superadmin/edit_user.html", context)
    except Exception as e:
        print(f"❌ Erreur lors de la récupération de l'utilisateur: {e}")
        return RedirectResponse(url="/superadmin/users", status_code=303)

@router.post("/superadmin/users/{user_id}/edit")
async def edit_user(
    user_id: str,
    request: Request,
    nom: str = Form(...),
    prenom: str = Form(...),
    email: str = Form(...),
    roles: List[str] = Form(default=[]),
    managed_subjects: List[str] = Form(default=[]),
    current_user: User = Depends(get_current_superadmin)
):
    """Modifier un utilisateur existant"""
    try:
        # Convertir l'ID string en ObjectId
        user_to_edit = await Database.engine.find_one(User, User.id == ObjectId(user_id))
        if not user_to_edit:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        # Vérifier que l'email n'est pas déjà utilisé par un autre utilisateur
        existing_user = await Database.engine.find_one(User, User.email == email)
        if existing_user and str(existing_user.id) != user_id:
            from src.utils.flash_messages import flash
            flash(request, "Cette adresse email est déjà utilisée par un autre utilisateur.", "error")
            return RedirectResponse(url=f"/superadmin/users/{user_id}/edit", status_code=303)

        # Validation: si gestionnaire est sélectionné, au moins un sujet doit être assigné
        if "gestionnaire" in roles and not managed_subjects:
            from src.utils.flash_messages import flash
            flash(request, "Un gestionnaire doit avoir au moins un sujet assigné.", "error")
            return RedirectResponse(url=f"/superadmin/users/{user_id}/edit", status_code=303)

        # Récupérer tous les sujets pour gérer les changements
        all_subjects = await Database.engine.find(Subject)
        
        # Retirer l'utilisateur de tous les sujets où il était gestionnaire
        for subject in all_subjects:
            if user_id in subject.gestionnaires_ids:
                subject.gestionnaires_ids.remove(user_id)
                await Database.engine.save(subject)
        
        # Ajouter l'utilisateur comme gestionnaire des nouveaux sujets sélectionnés
        if "gestionnaire" in roles and managed_subjects:
            for subject_id in managed_subjects:
                try:
                    subject = await Database.engine.find_one(Subject, Subject.id == ObjectId(subject_id))
                    if subject:
                        # Ajouter l'utilisateur comme gestionnaire du sujet
                        if user_id not in subject.gestionnaires_ids:
                            subject.gestionnaires_ids.append(user_id)
                        # Ajouter aussi l'utilisateur aux utilisateurs du sujet
                        if user_id not in subject.users_ids:
                            subject.users_ids.append(user_id)
                        await Database.engine.save(subject)
                except Exception as e:
                    print(f"❌ Erreur lors de l'ajout du gestionnaire au sujet {subject_id}: {e}")
        
        # Mettre à jour les informations de l'utilisateur
        user_to_edit.nom = nom.strip()
        user_to_edit.prenom = prenom.strip()
        user_to_edit.email = email.strip().lower()
        user_to_edit.roles = roles if roles else ["user"]
        
        # Sauvegarder les modifications
        await Database.engine.save(user_to_edit)
        
        from src.utils.flash_messages import flash
        flash(request, f"L'utilisateur {prenom} {nom} a été modifié avec succès.", "success")
        return RedirectResponse(url="/superadmin/users", status_code=303)
        
    except Exception as e:
        print(f"❌ Erreur lors de la modification de l'utilisateur: {e}")
        from src.utils.flash_messages import flash
        flash(request, "Erreur lors de la modification de l'utilisateur.", "error")
        return RedirectResponse(url="/superadmin/users", status_code=303)

@router.post("/superadmin/users/{user_id}/delete")
async def delete_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(get_current_superadmin)
):
    """Supprimer un utilisateur"""
    try:
        # Convertir l'ID string en ObjectId
        user_to_delete = await Database.engine.find_one(User, User.id == ObjectId(user_id))
        if not user_to_delete:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        # Vérifier qu'on ne supprime pas le dernier superadmin
        if "superadmin" in user_to_delete.roles:
            all_superadmins = await Database.engine.find(User, {"roles": {"$in": ["superadmin"]}})
            if len(all_superadmins) <= 1:
                from src.utils.flash_messages import flash
                flash(request, "Impossible de supprimer le dernier super administrateur.", "error")
                return RedirectResponse(url="/superadmin/users", status_code=303)
        
        # Vérifier qu'on ne supprime pas soi-même
        if str(user_to_delete.id) == str(current_user.id):
            from src.utils.flash_messages import flash
            flash(request, "Vous ne pouvez pas supprimer votre propre compte.", "error")
            return RedirectResponse(url="/superadmin/users", status_code=303)
        
        # Retirer l'utilisateur de tous les sujets
        subjects = await Database.engine.find(Subject)
        for subject in subjects:
            if user_id in subject.users_ids:
                subject.users_ids.remove(user_id)
                await Database.engine.save(subject)
            if user_id in subject.gestionnaires_ids:
                # Si c'est le dernier gestionnaire du sujet, on ne peut pas le supprimer
                if len(subject.gestionnaires_ids) <= 1:
                    from src.utils.flash_messages import flash
                    flash(request, f"Impossible de supprimer l'utilisateur car il est le dernier gestionnaire du sujet '{subject.name}'.", "error")
                    return RedirectResponse(url="/superadmin/users", status_code=303)
                subject.gestionnaires_ids.remove(user_id)
                await Database.engine.save(subject)
        
        # Supprimer l'utilisateur
        await Database.engine.delete(user_to_delete)
        
        from src.utils.flash_messages import flash
        flash(request, f"L'utilisateur {user_to_delete.prenom} {user_to_delete.nom} a été supprimé avec succès.", "success")
        return RedirectResponse(url="/superadmin/users", status_code=303)
        
    except Exception as e:
        print(f"❌ Erreur lors de la suppression de l'utilisateur: {e}")
        from src.utils.flash_messages import flash
        flash(request, "Erreur lors de la suppression de l'utilisateur.", "error")
        return RedirectResponse(url="/superadmin/users", status_code=303)
