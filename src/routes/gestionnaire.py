from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Optional
import csv
import io

from src.models.user import User
from src.models.subject import Subject
from src.services.auth_service import get_current_user, get_password_hash
from src.services.user_service import create_user, get_users, add_role_to_user, remove_role_from_user
from src.services.subject_service import (
    get_subject, get_subjects_by_gestionnaire, update_subject, add_user_to_subject,
    remove_user_from_subject, activate_emission, deactivate_emission, activate_vote, close_vote, abandon_vote
)
from src.services.database import Database
from src.services.activity_log_service import log_activity, get_subject_activities

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "templates"))

async def get_current_gestionnaire(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, detail="Not authenticated", headers={"Location": "/auth/login"})
    # Check if user is gestionnaire of at least one subject
    subjects = await get_subjects_by_gestionnaire(str(current_user.id))
    if not subjects:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits de gestionnaire")
    return current_user

@router.get("/gestionnaire/dashboard", response_class=HTMLResponse)
async def gestionnaire_dashboard(request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subjects = await get_subjects_by_gestionnaire(str(current_user.id))
    active_subject_id = request.session.get("active_subject_id")
    active_subject = None
    if active_subject_id:
        active_subject = await get_subject(active_subject_id)

    return templates.TemplateResponse("gestionnaire/dashboard.html", {"request": request, "subjects": subjects, "active_subject": active_subject, "current_user": current_user, "show_sidebar": True})

@router.get("/gestionnaire/subjects", response_class=HTMLResponse)
async def gestionnaire_subjects(request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subjects = await get_subjects_by_gestionnaire(str(current_user.id))
    
    # Récupérer le nombre d'idées pour chaque sujet
    from src.services.idea_service import get_ideas_by_subject
    subjects_with_ideas = []
    for subject in subjects:
        ideas = await get_ideas_by_subject(str(subject.id))
        subject.ideas_count = len(ideas)
        subjects_with_ideas.append(subject)
    
    return templates.TemplateResponse("gestionnaire/subjects.html", {
        "request": request, 
        "subjects": subjects_with_ideas, 
        "current_user": current_user, 
        "show_sidebar": True
    })

@router.get("/gestionnaire/users", response_class=HTMLResponse)
async def gestionnaire_users(request: Request, current_user: User = Depends(get_current_gestionnaire)):
    # Récupérer tous les sujets gérés par le gestionnaire
    subjects = await get_subjects_by_gestionnaire(str(current_user.id))
    
    # Récupérer tous les utilisateurs assignés aux sujets du gestionnaire
    all_users = await get_users()
    managed_users = []
    
    for subject in subjects:
        for user in all_users:
            if str(user.id) in subject.users_ids and user not in managed_users:
                managed_users.append(user)
    
    return templates.TemplateResponse("gestionnaire/users.html", {
        "request": request, 
        "users": managed_users,
        "subjects": subjects,
        "current_user": current_user, 
        "show_sidebar": True
    })

@router.post("/gestionnaire/set_active_subject/{subject_id}")
async def set_active_subject(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await get_subject(subject_id)
    print(f"DEBUG: subject_id = {subject_id}")
    print(f"DEBUG: current_user.id = {current_user.id}")
    print(f"DEBUG: str(current_user.id) = {str(current_user.id)}")
    if subject:
        print(f"DEBUG: subject.gestionnaires_ids = {subject.gestionnaires_ids}")
        print(f"DEBUG: type of gestionnaires_ids[0] = {type(subject.gestionnaires_ids[0]) if subject.gestionnaires_ids else 'empty'}")
    else:
        print("DEBUG: subject is None")
    
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    request.session["active_subject_id"] = subject_id
    return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/gestionnaire/subject/{subject_id}/manage_users", response_class=HTMLResponse)
async def manage_subject_users_form(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    
    all_users = await get_users()
    subject_users = [user for user in all_users if str(user.id) in subject.users_ids]
    available_users = [user for user in all_users if str(user.id) not in subject.users_ids]
    
    # Récupérer les gestionnaires du sujet
    subject_managers = [user for user in all_users if str(user.id) in subject.gestionnaires_ids]
    
    # Récupérer les utilisateurs qui peuvent devenir gestionnaires (tous les utilisateurs existants sauf ceux déjà gestionnaires de ce sujet)
    potential_managers = [user for user in all_users if str(user.id) not in subject.gestionnaires_ids]

    # Convertir les objets User en dictionnaires pour la sérialisation JSON
    available_users_dict = [
        {
            "id": str(user.id),
            "email": user.email,
            "prenom": user.prenom,
            "nom": user.nom
        }
        for user in available_users
    ]

    return templates.TemplateResponse("gestionnaire/manage_users.html", {
        "request": request, 
        "subject": subject, 
        "subject_users": subject_users, 
        "subject_managers": subject_managers,
        "available_users": available_users,
        "potential_managers": potential_managers,
        "available_users_dict": available_users_dict,
        "current_user": current_user,
        "show_sidebar": True
    })

@router.post("/gestionnaire/subject/{subject_id}/add_user")
async def add_user_to_subject_route(subject_id: str, request: Request, user_id: str = Form(...), current_user: User = Depends(get_current_gestionnaire)):
    subject = await add_user_to_subject(subject_id, user_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible d'ajouter l'utilisateur au sujet.")
    # Ajout du rôle gestionnaire si l'utilisateur est dans gestionnaires_ids
    if str(user_id) in subject.gestionnaires_ids:
        await add_role_to_user(user_id, "gestionnaire")
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/add_users")
async def add_users_to_subject_route(subject_id: str, request: Request, user_ids: str = Form(...), current_user: User = Depends(get_current_gestionnaire)):
    """
    Ajoute plusieurs utilisateurs au sujet en une seule fois
    """
    import json
    try:
        user_ids_list = json.loads(user_ids)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Format des IDs utilisateurs invalide.")
    
    success_count = 0
    failed_count = 0
    
    for user_id in user_ids_list:
        try:
            subject = await add_user_to_subject(subject_id, user_id)
            if subject:
                # Ajout du rôle gestionnaire si l'utilisateur est dans gestionnaires_ids
                if str(user_id) in subject.gestionnaires_ids:
                    await add_role_to_user(user_id, "gestionnaire")
                success_count += 1
            else:
                failed_count += 1
        except Exception:
            failed_count += 1
    
    if success_count > 0:
        request.session["success_message"] = f"{success_count} utilisateur(s) ajouté(s) au sujet avec succès."
    if failed_count > 0:
        request.session["error_message"] = f"Échec pour {failed_count} utilisateur(s)."
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/remove_user")
async def remove_user_from_subject_route(subject_id: str, request: Request, user_id: str = Form(...), current_user: User = Depends(get_current_gestionnaire)):
    subject = await remove_user_from_subject(subject_id, user_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de retirer l'utilisateur du sujet.")
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/remove_users")
async def remove_users_from_subject_route(subject_id: str, request: Request, user_ids: str = Form(...), current_user: User = Depends(get_current_gestionnaire)):
    """
    Retire plusieurs utilisateurs du sujet en une seule fois
    """
    import json
    try:
        user_ids_list = json.loads(user_ids)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Format des IDs utilisateurs invalide.")
    
    success_count = 0
    failed_count = 0
    
    for user_id in user_ids_list:
        try:
            subject = await remove_user_from_subject(subject_id, user_id)
            if subject:
                success_count += 1
            else:
                failed_count += 1
        except Exception:
            failed_count += 1
    
    if success_count > 0:
        request.session["success_message"] = f"{success_count} utilisateur(s) retiré(s) du sujet avec succès."
    if failed_count > 0:
        request.session["error_message"] = f"Échec pour {failed_count} utilisateur(s)."
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/activate_emission")
async def activate_emission_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await activate_emission(subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible d'activer l'émission d'idées.")
    
    # Log de l'activité
    await log_activity(
        action="activate_emission",
        subject_id=subject_id,
        user=current_user,
        description=f"Activation de l'émission d'idées pour le sujet '{subject.name}'",
        details="État précédent: Inactive",
        request=request
    )
    
    # Redirection vers la page d'origine ou par défaut vers /gestionnaire/subjects
    referer = request.headers.get("referer", "/gestionnaire/subjects")
    if "subjects" in referer:
        return RedirectResponse(url="/gestionnaire/subjects", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/deactivate_emission")
async def deactivate_emission_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await deactivate_emission(subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de désactiver l'émission d'idées.")
    
    # Log de l'activité
    await log_activity(
        action="deactivate_emission",
        subject_id=subject_id,
        user=current_user,
        description=f"Désactivation de l'émission d'idées pour le sujet '{subject.name}'",
        details="État précédent: Active",
        request=request
    )
    
    # Redirection vers la page d'origine ou par défaut vers /gestionnaire/subjects
    referer = request.headers.get("referer", "/gestionnaire/subjects")
    if "subjects" in referer:
        return RedirectResponse(url="/gestionnaire/subjects", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/activate_vote")
async def activate_vote_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await activate_vote(subject_id)
    if not subject:
        # Vérifier si c'est à cause du manque d'idées
        from src.services.idea_service import get_ideas_by_subject
        ideas = await get_ideas_by_subject(subject_id)
        if not ideas:
            request.session["error_message"] = "Impossible d'activer le vote : aucune idée n'a été soumise pour ce sujet."
        else:
            request.session["error_message"] = "Impossible d'activer la session de vote."
        
        # Redirection vers la page d'origine
        referer = request.headers.get("referer", "/gestionnaire/subjects")
        if "subjects" in referer:
            return RedirectResponse(url="/gestionnaire/subjects", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    
    # Log de l'activité
    await log_activity(
        action="activate_vote",
        subject_id=subject_id,
        user=current_user,
        description=f"Activation de la session de vote pour le sujet '{subject.name}'",
        details="Émission d'idées automatiquement désactivée",
        request=request
    )
    
    request.session["success_message"] = f"Session de vote activée pour le sujet '{subject.name}'."
    
    # Redirection vers la page d'origine ou par défaut vers /gestionnaire/subjects
    referer = request.headers.get("referer", "/gestionnaire/subjects")
    if "subjects" in referer:
        return RedirectResponse(url="/gestionnaire/subjects", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/close_vote")
async def close_vote_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await close_vote(subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de clôturer la session de vote.")
    
    # Log de l'activité
    await log_activity(
        action="close_vote",
        subject_id=subject_id,
        user=current_user,
        description=f"Clôture de la session de vote pour le sujet '{subject.name}'",
        details="Résultats finalisés",
        request=request
    )
    
    # Redirection vers la page d'origine ou par défaut vers /gestionnaire/subjects
    referer = request.headers.get("referer", "/gestionnaire/subjects")
    if "subjects" in referer:
        return RedirectResponse(url="/gestionnaire/subjects", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/abandon_vote")
async def abandon_vote_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await abandon_vote(subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible d'abandonner la session de vote.")
    
    # Log de l'activité
    await log_activity(
        action="abandon_vote",
        subject_id=subject_id,
        user=current_user,
        description=f"Abandon de la session de vote pour le sujet '{subject.name}'",
        details="Session annulée - retour à l'émission d'idées possible",
        request=request
    )
    
    # Redirection vers la page d'origine ou par défaut vers /gestionnaire/subjects
    referer = request.headers.get("referer", "/gestionnaire/subjects")
    if "subjects" in referer:
        return RedirectResponse(url="/gestionnaire/subjects", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/create_and_add_user")
async def create_and_add_user_route(
    subject_id: str, 
    request: Request, 
    email: str = Form(...),
    prenom: str = Form(...),
    nom: str = Form(...),
    password: str = Form(...),
    current_user: User = Depends(get_current_gestionnaire)
):
    # Vérifier que l'utilisateur est gestionnaire du sujet
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    
    try:
        # Créer l'objet utilisateur avec mot de passe hashé
        from src.services.auth_service import get_password_hash
        hashed_password = get_password_hash(password)
        
        new_user = User(
            email=email,
            pwd=hashed_password,  # Utiliser 'pwd' au lieu de 'password'
            prenom=prenom,
            nom=nom,
            roles=["user"]
        )
        
        # Sauvegarder l'utilisateur
        created_user = await create_user(new_user)
        if created_user:
            # Ajouter l'utilisateur au sujet
            await add_user_to_subject(subject_id, str(created_user.id))
            # Ajout du rôle gestionnaire si l'utilisateur est dans gestionnaires_ids
            subject = await get_subject(subject_id)
            if str(created_user.id) in subject.gestionnaires_ids:
                await add_role_to_user(str(created_user.id), "gestionnaire")
            request.session["success_message"] = f"Utilisateur {email} créé et ajouté au sujet avec succès."
        else:
            request.session["error_message"] = "Erreur lors de la création de l'utilisateur."
    except Exception as e:
        request.session["error_message"] = f"Erreur lors de la création de l'utilisateur: {str(e)}"
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/import_users")
async def import_users_route(
    subject_id: str,
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_gestionnaire)
):
    # Vérifier que l'utilisateur est gestionnaire du sujet
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    
    if not file.filename.endswith('.csv'):
        request.session["error_message"] = "Veuillez sélectionner un fichier CSV."
        return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)
    
    try:
        # Lire le fichier CSV
        content = await file.read()
        csv_data = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        created_count = 0
        added_count = 0
        errors = []
        
        for row in csv_reader:
            if not all(key in row for key in ['email', 'prenom', 'nom', 'password']):
                errors.append("Format CSV invalide. Colonnes requises: email, prenom, nom, password")
                break
            
            try:
                # Créer l'objet utilisateur avec mot de passe hashé
                hashed_password = get_password_hash(row['password'])
                
                new_user = User(
                    email=row['email'],
                    pwd=hashed_password,  # Utiliser 'pwd' au lieu de 'password'
                    prenom=row['prenom'],
                    nom=row['nom'],
                    roles=["user"]
                )
                
                # Sauvegarder l'utilisateur
                created_user = await create_user(new_user)
                if created_user:
                    created_count += 1
                    # Ajouter l'utilisateur au sujet
                    if str(created_user.id) not in subject.users_ids:
                        await add_user_to_subject(subject_id, str(created_user.id))
                        added_count += 1
                    # Ajout du rôle gestionnaire si l'utilisateur est dans gestionnaires_ids
                    subject = await get_subject(subject_id)
                    if str(created_user.id) in subject.gestionnaires_ids:
                        await add_role_to_user(str(created_user.id), "gestionnaire")
                else:
                    errors.append(f"Impossible de créer l'utilisateur {row['email']} (déjà existant ?)")
            except Exception as e:
                errors.append(f"Erreur pour {row['email']}: {str(e)}")
        
        # Message de résultat
        if created_count > 0:
            request.session["success_message"] = f"{created_count} utilisateurs créés, {added_count} ajoutés au sujet."
        if errors:
            request.session["error_message"] = f"Erreurs: {'; '.join(errors[:3])}" + ("..." if len(errors) > 3 else "")
    
    except Exception as e:
        request.session["error_message"] = f"Erreur lors de l'import: {str(e)}"
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

# Nouvelles routes pour actions groupées
@router.post("/gestionnaire/subjects/batch_activate_emission")
async def batch_activate_emission(request: Request, subject_ids: List[str] = Form(...), current_user: User = Depends(get_current_gestionnaire)):
    """
    Active l'émission d'idées pour plusieurs sujets en même temps
    """
    success_count = 0
    failed_subjects = []
    
    for subject_id in subject_ids:
        try:
            subject = await activate_emission(subject_id)
            if subject and str(current_user.id) in subject.gestionnaires_ids:
                # Log de l'activité
                await log_activity(
                    action="activate_emission",
                    subject_id=subject_id,
                    user=current_user,
                    description=f"Activation en lot de l'émission d'idées pour le sujet '{subject.name}'",
                    details="Action groupée",
                    request=request
                )
                success_count += 1
            else:
                failed_subjects.append(subject_id)
        except Exception:
            failed_subjects.append(subject_id)
    
    if success_count > 0:
        request.session["success_message"] = f"Émission d'idées activée pour {success_count} sujet(s)."
    if failed_subjects:
        request.session["error_message"] = f"Échec pour {len(failed_subjects)} sujet(s)."
    
    return RedirectResponse(url="/gestionnaire/subjects", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subjects/batch_deactivate_emission")
async def batch_deactivate_emission(request: Request, subject_ids: List[str] = Form(...), current_user: User = Depends(get_current_gestionnaire)):
    """
    Désactive l'émission d'idées pour plusieurs sujets en même temps
    """
    success_count = 0
    failed_subjects = []
    
    for subject_id in subject_ids:
        try:
            subject = await deactivate_emission(subject_id)
            if subject and str(current_user.id) in subject.gestionnaires_ids:
                # Log de l'activité
                await log_activity(
                    action="deactivate_emission",
                    subject_id=subject_id,
                    user=current_user,
                    description=f"Désactivation en lot de l'émission d'idées pour le sujet '{subject.name}'",
                    details="Action groupée",
                    request=request
                )
                success_count += 1
            else:
                failed_subjects.append(subject_id)
        except Exception:
            failed_subjects.append(subject_id)
    
    if success_count > 0:
        request.session["success_message"] = f"Émission d'idées désactivée pour {success_count} sujet(s)."
    if failed_subjects:
        request.session["error_message"] = f"Échec pour {len(failed_subjects)} sujet(s)."
    
    return RedirectResponse(url="/gestionnaire/subjects", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subjects/batch_activate_vote")
async def batch_activate_vote(request: Request, subject_ids: List[str] = Form(...), current_user: User = Depends(get_current_gestionnaire)):
    """
    Active la session de vote pour plusieurs sujets en même temps
    """
    success_count = 0
    failed_subjects = []
    
    for subject_id in subject_ids:
        try:
            subject = await activate_vote(subject_id)
            if subject and str(current_user.id) in subject.gestionnaires_ids:
                # Log de l'activité
                await log_activity(
                    action="activate_vote",
                    subject_id=subject_id,
                    user=current_user,
                    description=f"Activation en lot de la session de vote pour le sujet '{subject.name}'",
                    details="Action groupée - Émission d'idées automatiquement désactivée",
                    request=request
                )
                success_count += 1
            else:
                failed_subjects.append(subject_id)
        except Exception:
            failed_subjects.append(subject_id)
    
    if success_count > 0:
        request.session["success_message"] = f"Session de vote activée pour {success_count} sujet(s)."
    if failed_subjects:
        request.session["error_message"] = f"Échec pour {len(failed_subjects)} sujet(s)."
    
    return RedirectResponse(url="/gestionnaire/subjects", status_code=status.HTTP_303_SEE_OTHER)

# Route pour la page de gestion/modification d'un sujet
@router.get("/gestionnaire/subject/{subject_id}/manage", response_class=HTMLResponse)
async def manage_subject(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """
    Page de gestion/modification d'un sujet avec ses idées
    """
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    
    # Récupérer les idées du sujet
    from src.services.idea_service import get_ideas_by_subject
    from src.services.user_service import get_user
    ideas = await get_ideas_by_subject(subject_id)
    
    # Convertir les idées en dictionnaires enrichis
    enriched_ideas = []
    for idea in ideas:
        # Récupérer l'auteur de l'idée
        author = await get_user(idea.user_id)
        author_name = f"{author.prenom} {author.nom}" if author else "Utilisateur inconnu"
        
        # S'assurer que description n'est jamais None
        description_content = idea.description if idea.description is not None else ""
        
        # Créer un dictionnaire avec toutes les informations
        idea_dict = {
            "id": str(idea.id),
            "title": idea.title,
            "content": description_content,  # Mapping description -> content pour le template
            "description": description_content,  # Garder aussi description pour compatibilité
            "author_name": author_name,
            "author_id": idea.user_id,
            "votes_count": len(idea.votes),
            "votes": idea.votes,
            "created_at": idea.created_at,
            "subject_id": idea.subject_id
        }
        
        enriched_ideas.append(idea_dict)
    
    return templates.TemplateResponse("gestionnaire/manage_subject.html", {
        "request": request,
        "subject": subject,
        "ideas": enriched_ideas,
        "current_user": current_user,
        "show_sidebar": True
    })

# Route pour modifier une idée
@router.post("/gestionnaire/subject/{subject_id}/edit_idea/{idea_id}")
async def edit_idea(
    subject_id: str, 
    idea_id: str,
    request: Request,
    title: str = Form(...),
    content: str = Form(...),  # Le formulaire envoie 'content'
    current_user: User = Depends(get_current_gestionnaire)
):
    """
    Modifie le titre et le contenu d'une idée
    """
    # Vérifier que l'utilisateur est gestionnaire du sujet
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    
    # Récupérer l'idée pour avoir l'ancien contenu pour le log
    from src.services.idea_service import get_idea, update_idea
    idea = await get_idea(idea_id)
    
    if not idea or idea.subject_id != subject_id:
        request.session["error_message"] = "Idée non trouvée."
        return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage", status_code=status.HTTP_303_SEE_OTHER)
    
    # Sauvegarder l'ancien contenu pour le log
    old_title = idea.title
    old_description = idea.description or ""
    
    try:
        # Utiliser la fonction update_idea du service
        updated_idea = await update_idea(idea_id, title.strip(), content.strip())
        
        if updated_idea:
            # Log de l'activité
            await log_activity(
                action="edit_idea",
                subject_id=subject_id,
                user=current_user,
                description=f"Modification de l'idée '{old_title}' par le gestionnaire",
                details=f"Ancien titre: '{old_title}' → Nouveau titre: '{title}' | Ancien contenu: '{old_description[:50]}...' → Nouveau contenu: '{content[:50]}...'",
                request=request
            )
            
            request.session["success_message"] = f"Idée '{title}' modifiée avec succès."
        else:
            request.session["error_message"] = "Erreur lors de la modification de l'idée."
    except Exception as e:
        request.session["error_message"] = f"Erreur lors de la modification de l'idée: {str(e)}"
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage", status_code=status.HTTP_303_SEE_OTHER)

# Route pour supprimer une idée
@router.post("/gestionnaire/subject/{subject_id}/delete_idea/{idea_id}")
async def delete_idea_route(
    subject_id: str, 
    idea_id: str,
    request: Request,
    current_user: User = Depends(get_current_gestionnaire)
):
    """
    Supprime une idée
    """
    # Vérifier que l'utilisateur est gestionnaire du sujet
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    
    # Récupérer l'idée pour les logs avant suppression
    from src.services.idea_service import get_idea, delete_idea
    idea = await get_idea(idea_id)
    
    if not idea or idea.subject_id != subject_id:
        request.session["error_message"] = "Idée non trouvée."
        return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage", status_code=status.HTTP_303_SEE_OTHER)
    
    # Sauvegarder les informations pour le log
    idea_title = idea.title
    idea_content = idea.description or ""
    
    try:
        # Utiliser la fonction delete_idea du service
        success = await delete_idea(idea_id)
        
        if success:
            # Log de l'activité
            await log_activity(
                action="delete_idea",
                subject_id=subject_id,
                user=current_user,
                description=f"Suppression de l'idée '{idea_title}' par le gestionnaire",
                details=f"Contenu supprimé: '{idea_content[:100]}...'",
                request=request
            )
            
            request.session["success_message"] = f"Idée '{idea_title}' supprimée avec succès."
        else:
            request.session["error_message"] = "Erreur lors de la suppression de l'idée."
    except Exception as e:
        request.session["error_message"] = f"Erreur lors de la suppression de l'idée: {str(e)}"
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage", status_code=status.HTTP_303_SEE_OTHER)

# Route pour l'historique d'activité d'un sujet
@router.get("/gestionnaire/subject/{subject_id}/history", response_class=HTMLResponse)
async def subject_history(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """
    Page d'historique d'activité d'un sujet
    """
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    
    # Récupérer l'historique d'activité du sujet
    activities = await get_subject_activities(subject_id)
    
    # Récupérer les statistiques du sujet
    from src.services.idea_service import get_ideas_by_subject
    ideas = await get_ideas_by_subject(subject_id)
    
    # Calculer les statistiques
    total_ideas = len(ideas)
    total_votes = sum(len(idea.votes) for idea in ideas)
    
    # Récupérer les utilisateurs du sujet pour les statistiques
    all_users = await get_users()
    subject_users = [user for user in all_users if str(user.id) in subject.users_ids]
    total_users = len(subject_users)
    
    # Statistiques par période (dernières 24h, 7 jours, 30 jours)
    from datetime import datetime, timedelta
    now = datetime.now()
    
    activities_24h = [a for a in activities if a.timestamp >= now - timedelta(hours=24)]
    activities_7d = [a for a in activities if a.timestamp >= now - timedelta(days=7)]
    activities_30d = [a for a in activities if a.timestamp >= now - timedelta(days=30)]
    
    stats = {
        "total_ideas": total_ideas,
        "total_votes": total_votes,
        "total_users": total_users,
        "activities_24h": len(activities_24h),
        "activities_7d": len(activities_7d),
        "activities_30d": len(activities_30d)
    }
    
    return templates.TemplateResponse("gestionnaire/subject_history.html", {
        "request": request,
        "subject": subject,
        "activities": activities,
        "stats": stats,
        "current_user": current_user,
        "show_sidebar": True
    })
