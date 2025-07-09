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
from src.services.metrics_service import MetricsService
from src.services.vote_service import VoteService

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
    # Récupérer les métriques pour le gestionnaire
    metrics = await MetricsService.get_gestionnaire_dashboard_metrics(current_user)
    
    subjects = await get_subjects_by_gestionnaire(str(current_user.id))
    from src.services.idea_service import get_ideas_by_subject
    # Ajout du nombre d'idées et de votants pour chaque sujet
    for subject in subjects:
        ideas = await get_ideas_by_subject(str(subject.id))
        subject.ideas_count = len(ideas)
        # Utiliser VoteService pour compter les votes
        subject.votes_count = await VoteService.get_votes_count_for_subject(str(subject.id))
        
    active_subject_id = request.session.get("active_subject_id")
    active_subject = None
    if active_subject_id:
        active_subject = await get_subject(active_subject_id)

    # Préparer le contexte avec les informations de l'organisation
    from src.utils.template_helpers import add_organization_context
    context = {
        "request": request, 
        "subjects": subjects, 
        "active_subject": active_subject, 
        "current_user": current_user, 
        "metrics": metrics,
        "show_sidebar": True
    }
    
    # Ajouter les informations de l'organisation
    context = await add_organization_context(context)

    return templates.TemplateResponse("gestionnaire/dashboard.html", context)

@router.get("/gestionnaire/subjects", response_class=HTMLResponse)
async def gestionnaire_subjects(request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subjects = await get_subjects_by_gestionnaire(str(current_user.id))
    
    # Récupérer le nombre d'idées pour chaque sujet
    from src.services.idea_service import get_ideas_by_subject
    subjects_with_ideas = []
    for subject in subjects:
        ideas = await get_ideas_by_subject(str(subject.id))
        subjects_with_ideas.append({
            "subject": subject,
            "ideas_count": len(ideas)
        })
    
    # Préparer le contexte avec les informations de l'organisation
    from src.utils.template_helpers import add_organization_context
    context = {
        "request": request, 
        "subjects": subjects_with_ideas, 
        "current_user": current_user, 
        "show_sidebar": True
    }
    
    # Ajouter les informations de l'organisation
    context = await add_organization_context(context)
    
    return templates.TemplateResponse("gestionnaire/subjects.html", context)

@router.get("/gestionnaire/users", response_class=HTMLResponse)
async def gestionnaire_users(request: Request, current_user: User = Depends(get_current_gestionnaire)):
    # Récupérer tous les sujets gérés par le gestionnaire
    subjects = await get_subjects_by_gestionnaire(str(current_user.id))
    
    # Récupérer tous les invités assignés aux sujets du gestionnaire
    all_users = await get_users()
    managed_users = []
    
    for subject in subjects:
        for user in all_users:
            if str(user.id) in subject.users_ids and user not in managed_users:
                managed_users.append(user)
    
    # Préparer le contexte avec les informations de l'organisation
    from src.utils.template_helpers import add_organization_context
    context = {
        "request": request, 
        "users": managed_users,
        "subjects": subjects,
        "current_user": current_user, 
        "show_sidebar": True
    }
    
    # Ajouter les informations de l'organisation
    context = await add_organization_context(context)
    
    return templates.TemplateResponse("gestionnaire/users.html", context)

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
    
    # Récupérer les invités qui peuvent devenir gestionnaires (tous les invités existants sauf ceux déjà gestionnaires de ce sujet)
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

    # Préparer le contexte avec les informations de l'organisation
    from src.utils.template_helpers import add_organization_context
    context = {
        "request": request, 
        "subject": subject, 
        "subject_users": subject_users, 
        "subject_managers": subject_managers,
        "available_users": available_users,
        "potential_managers": potential_managers,
        "available_users_dict": available_users_dict,
        "current_user": current_user,
        "show_sidebar": True
    }
    
    # Ajouter les informations de l'organisation
    context = await add_organization_context(context)
    
    return templates.TemplateResponse("gestionnaire/manage_users.html", context)

@router.post("/gestionnaire/subject/{subject_id}/add_user")
async def add_user_to_subject_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire), user_id: str = Form(...)):
    subject = await add_user_to_subject(subject_id, user_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible d'ajouter l'invité au sujet.")
    # Ajout du rôle gestionnaire si l'invité est dans gestionnaires_ids
    if str(user_id) in subject.gestionnaires_ids:
        await add_role_to_user(user_id, "gestionnaire")
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/add_users")
async def add_users_to_subject_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire), user_ids: str = Form(...)):
    """
    Ajoute plusieurs invités au sujet en une seule fois
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
                # Ajout du rôle gestionnaire si l'invité est dans gestionnaires_ids
                if str(user_id) in subject.gestionnaires_ids:
                    await add_role_to_user(user_id, "gestionnaire")
                success_count += 1
            else:
                failed_count += 1
        except Exception:
            failed_count += 1
    
    if success_count > 0:
        request.session["success_message"] = f"{success_count} invité(s) ajouté(s) au sujet avec succès."
    if failed_count > 0:
        request.session["error_message"] = f"Échec pour {failed_count} invité(s)."
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/remove_user")
async def remove_user_from_subject_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire), user_id: str = Form(...)):
    subject = await remove_user_from_subject(subject_id, user_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de retirer l'invité du sujet.")
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/remove_users")
async def remove_users_from_subject_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire), user_ids: str = Form(...)):
    """
    Retire plusieurs invités du sujet en une seule fois
    """
    import json
    try:
        user_ids_list = json.loads(user_ids)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Format des IDs invités invalide.")
    
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
        request.session["success_message"] = f"{success_count} invité(s) retiré(s) du sujet avec succès."
    if failed_count > 0:
        request.session["error_message"] = f"Échec pour {failed_count} invité(s)."
    
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
    current_user: User = Depends(get_current_gestionnaire),
    email: str = Form(...),
    prenom: str = Form(...),
    nom: str = Form(...),
    password: str = Form(...)
):
    # Vérifier que l'invité est gestionnaire du sujet
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    
    try:
        # Créer l'objet invité avec mot de passe hashé
        from src.services.auth_service import get_password_hash
        hashed_password = get_password_hash(password)
        
        new_user = User(
            email=email,
            pwd=hashed_password,  # Utiliser 'pwd' au lieu de 'password'
            prenom=prenom,
            nom=nom,
            roles=["user"]
        )
        
        # Sauvegarder l'invité
        created_user = await create_user(new_user)
        if created_user:
            # Ajouter l'invité au sujet
            await add_user_to_subject(subject_id, str(created_user.id))
            # Ajout du rôle gestionnaire si l'invité est dans gestionnaires_ids
            subject = await get_subject(subject_id)
            if str(created_user.id) in subject.gestionnaires_ids:
                await add_role_to_user(str(created_user.id), "gestionnaire")
            request.session["success_message"] = f"Invité {email} créé et ajouté au sujet avec succès."
        else:
            request.session["error_message"] = "Erreur lors de la création de l'invité."
    except Exception as e:
        request.session["error_message"] = f"Erreur lors de la création de l'invité: {str(e)}"
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/import_users")
async def import_users_route(
    subject_id: str,
    request: Request,
    current_user: User = Depends(get_current_gestionnaire),
    file: UploadFile = File(...)
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
async def batch_activate_emission(request: Request, current_user: User = Depends(get_current_gestionnaire), subject_ids: List[str] = Form(...)):
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
async def batch_deactivate_emission(request: Request, current_user: User = Depends(get_current_gestionnaire), subject_ids: List[str] = Form(...)):
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
async def batch_activate_vote(request: Request, current_user: User = Depends(get_current_gestionnaire), subject_ids: List[str] = Form(...)):
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
    
    # Récupérer les utilisateurs du sujet
    all_users = await get_users()
    subject_users = [user for user in all_users if str(user.id) in subject.users_ids]
    
    # Convertir les idées en dictionnaires enrichis
    enriched_ideas = []
    for idea in ideas:
        # Récupérer l'auteur de l'idée
        author = await get_user(idea.user_id)
        author_name = f"{author.prenom} {author.nom}" if author else "Utilisateur inconnu"
        
        # S'assurer que description n'est jamais None
        description_content = idea.description if idea.description is not None else ""
        
        # Utiliser VoteService pour compter les votes
        votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
        voter_ids = await VoteService.get_voter_ids_for_idea(str(idea.id))
        
        # Créer un dictionnaire avec toutes les informations
        idea_dict = {
            "id": str(idea.id),
            "title": idea.title,
            "description": description_content,
            "author_name": author_name,
            "author_id": idea.user_id,
            "votes_count": votes_count,
            "votes": voter_ids,  # Liste des IDs des votants pour compatibilité
            # "created_at": idea.created_at,  # On ne le met pas pour éviter l'erreur JSON
            "subject_id": idea.subject_id
        }
        
        enriched_ideas.append(idea_dict)
    # TRIER par nombre de votes décroissant
    enriched_ideas.sort(key=lambda i: i["votes_count"], reverse=True)
    return templates.TemplateResponse("gestionnaire/manage_subject.html", {
        "request": request,
        "subject": subject,
        "ideas": enriched_ideas,
        "subject_users": subject_users,
        "current_user": current_user,
        "show_sidebar": True
    })

# Route pour modifier une idée
@router.post("/gestionnaire/subject/{subject_id}/edit_idea/{idea_id}")
async def edit_idea(
    subject_id: str, 
    idea_id: str,
    request: Request,
    current_user: User = Depends(get_current_gestionnaire),
    title: str = Form(...),
    content: str = Form(...)
):
    """
    Modifie une idée existante
    """
    print(f"DEBUG - edit_idea called with:")
    print(f"  subject_id: {subject_id}")
    print(f"  idea_id: {idea_id}")
    print(f"  title: {title}")
    print(f"  content: {content}")
    print(f"  current_user: {current_user.email if current_user else 'None'}")
    
    # Vérifier que l'utilisateur est gestionnaire du sujet
    subject = await get_subject(subject_id)
    print(f"DEBUG - subject found: {subject.name if subject else 'None'}")
    
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        print(f"DEBUG - Access denied. Subject gestionnaires: {subject.gestionnaires_ids if subject else 'None'}, User ID: {current_user.id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    
    # Récupérer l'idée pour avoir l'ancien contenu pour le log
    from src.services.idea_service import get_idea, update_idea
    idea = await get_idea(idea_id)
    print(f"DEBUG - idea found: {idea.title if idea else 'None'}")
    
    if not idea or idea.subject_id != subject_id:
        print(f"DEBUG - Idea not found or wrong subject. Idea subject_id: {idea.subject_id if idea else 'None'}, Expected: {subject_id}")
        request.session["error_message"] = "Idée non trouvée."
        return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage", status_code=status.HTTP_303_SEE_OTHER)
    
    # Sauvegarder l'ancien contenu pour le log
    old_title = idea.title
    old_content = idea.description if idea.description else ""
    print(f"DEBUG - Old values: title='{old_title}', content='{old_content[:50]}...'")
    
    try:
        print(f"DEBUG - Calling update_idea with: id={idea_id}, title='{title}', description='{content[:50]}...'")
        # Mettre à jour l'idée (content du formulaire devient description en base)
        updated_idea = await update_idea(idea_id, title, content)
        print(f"DEBUG - update_idea result: {updated_idea.title if updated_idea else 'None'}")
        
        if updated_idea:
            # Log de l'activité
            await log_activity(
                action="edit_idea",
                subject_id=subject_id,
                user=current_user,
                description=f"Modification de l'idée '{old_title}' par le gestionnaire",
                details=f"Ancien titre: '{old_title}' -> Nouveau titre: '{title}'\nAncien contenu: '{old_content[:100]}...' -> Nouveau contenu: '{content[:100]}...'",
                request=request
            )
            print(f"DEBUG - Activity logged successfully")
            
            request.session["success_message"] = f"L'idée '{title}' a été modifiée avec succès."
            print(f"DEBUG - Success message set")
        else:
            print(f"DEBUG - update_idea returned None")
            request.session["error_message"] = "Erreur lors de la modification de l'idée."
    
    except Exception as e:
        print(f"DEBUG - Exception in edit_idea: {str(e)}")
        import traceback
        traceback.print_exc()
        request.session["error_message"] = f"Erreur lors de la modification: {str(e)}"
    
    print(f"DEBUG - Redirecting to /gestionnaire/subject/{subject_id}/manage")
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
    
    # Récupérer l'idée pour avoir les informations pour le log
    from src.services.idea_service import get_idea, delete_idea
    idea = await get_idea(idea_id)
    
    if not idea or idea.subject_id != subject_id:
        request.session["error_message"] = "Idée non trouvée."
        return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage", status_code=status.HTTP_303_SEE_OTHER)
    
    # Sauvegarder les informations pour le log avant suppression
    idea_title = idea.title
    votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
    
    try:
        # Supprimer l'idée
        success = await delete_idea(idea_id)
        
        if success:
            # Log de l'activité
            await log_activity(
                action="delete_idea",
                subject_id=subject_id,
                user=current_user,
                description=f"Suppression de l'idée '{idea_title}' par le gestionnaire",
                details=f"Idée supprimée avec {votes_count} vote(s)",
                request=request
            )
            
            request.session["success_message"] = f"L'idée '{idea_title}' a été supprimée avec succès."
        else:
            request.session["error_message"] = "Erreur lors de la suppression de l'idée."
    
    except Exception as e:
        request.session["error_message"] = f"Erreur lors de la suppression: {str(e)}"
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage", status_code=status.HTTP_303_SEE_OTHER)

# Route pour l'historique/activités d'un sujet
@router.get("/gestionnaire/subject/{subject_id}/history", response_class=HTMLResponse)
async def subject_history(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """
    Affiche l'historique des activités d'un sujet
    """
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    
    # Récupérer les activités du sujet
    activities = await get_subject_activities(subject_id)
    
    # Calculer les statistiques requises par le template
    from src.services.idea_service import get_ideas_by_subject
    from datetime import datetime, timedelta
    
    # Récupérer les idées du sujet
    ideas = await get_ideas_by_subject(subject_id)
    
    # Calculer le nombre total d'idées
    total_ideas = len(ideas)
    
    # Calculer le nombre total de votes en utilisant VoteService
    total_votes = 0
    for idea in ideas:
        votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
        total_votes += votes_count
    
    # Calculer le nombre d'utilisateurs assignés
    total_users = len(subject.users_ids)
    
    # Calculer les statistiques d'activité par période
    now = datetime.now()
    activities_24h = len([a for a in activities if (now - a.timestamp).days < 1])
    activities_7d = len([a for a in activities if (now - a.timestamp).days < 7])
    activities_30d = len([a for a in activities if (now - a.timestamp).days < 30])
    
    # Créer l'objet stats
    stats = {
        "total_ideas": total_ideas,
        "total_votes": total_votes,
        "total_users": total_users,
        "activities_24h": activities_24h,
        "activities_7d": activities_7d,
        "activities_30d": activities_30d
    }
    
    return templates.TemplateResponse("gestionnaire/subject_history.html", {
        "request": request,
        "subject": subject,
        "activities": activities,
        "stats": stats,
        "current_user": current_user,
        "show_sidebar": True
    })

@router.get("/gestionnaire/subject/manage", response_class=HTMLResponse)
async def manage_subjects_overview(request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """Page de gestion rapide des sujets"""
    try:
        subjects = await get_subjects_by_gestionnaire(str(current_user.id))
        
        # Enrichir les sujets avec des métriques
        from src.services.idea_service import get_ideas_by_subject
        enriched_subjects = []
        
        for subject in subjects:
            ideas = await get_ideas_by_subject(str(subject.id))
            all_users = await get_users()
            subject_users = [user for user in all_users if str(user.id) in subject.users_ids]
            
            # Calculer le nombre total de votes pour ce sujet
            total_votes = 0
            for idea in ideas:
                votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
                total_votes += votes_count
            
            enriched_subjects.append({
                "subject": subject,
                "ideas_count": len(ideas),
                "users_count": len(subject_users),
                "votes_count": total_votes,
                "status": "Émission" if subject.emission_active else "Vote" if subject.vote_active else "Fermé"
            })
        
        # Préparer le contexte avec les informations de l'organisation
        from src.utils.template_helpers import add_organization_context
        context = {
            "request": request,
            "current_user": current_user,
            "subjects": enriched_subjects,
            "subjects_count": len(subjects),
            "show_sidebar": True
        }
        context = await add_organization_context(context)
        return templates.TemplateResponse("gestionnaire/manage_subjects_overview.html", context)
    except Exception as e:
        print(f"❌ Erreur gestion rapide sujets: {e}")
        return templates.TemplateResponse("gestionnaire/manage_subjects_overview.html", {
            "request": request,
            "current_user": current_user,
            "subjects": [],
            "subjects_count": 0,
            "show_sidebar": True
        })

@router.get("/gestionnaire/users/manage", response_class=HTMLResponse)
async def manage_users_overview(request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """Page de gestion globale des invités"""
    try:
        subjects = await get_subjects_by_gestionnaire(str(current_user.id))
        all_users = await get_users()
        
        # Organiser les utilisateurs par sujet
        subjects_with_users = []
        for subject in subjects:
            subject_users = [user for user in all_users if str(user.id) in subject.users_ids]
            available_users = [user for user in all_users if str(user.id) not in subject.users_ids and "user" in user.roles]
            
            subjects_with_users.append({
                "subject": subject,
                "users": subject_users,
                "available_users": available_users
            })
        
        return templates.TemplateResponse("gestionnaire/manage_users_overview.html", {
            "request": request,
            "current_user": current_user,
            "subjects_with_users": subjects_with_users,
            "subjects_count": len(subjects),
            "show_sidebar": True
        })
    except Exception as e:
        print(f"❌ Erreur gestion globale invités: {e}")
        return templates.TemplateResponse("gestionnaire/manage_users_overview.html", {
            "request": request,
            "current_user": current_user,
            "subjects_with_users": [],
            "subjects_count": 0,
            "show_sidebar": True
        })

@router.post("/gestionnaire/subject/{subject_id}/edit")
async def edit_subject(
    subject_id: str,
    request: Request,
    current_user: User = Depends(get_current_gestionnaire),
    name: str = Form(...),
    description: str = Form(...),
    vote_limit: int = Form(...),
    show_votes_during_vote: Optional[str] = Form(None)
):
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=404, detail="Sujet non trouvé ou vous n'êtes pas gestionnaire de ce sujet.")
    # Mettre à jour les champs
    subject.name = name.strip()
    subject.description = description.strip()
    subject.vote_limit = vote_limit
    subject.show_votes_during_vote = bool(show_votes_during_vote)
    # Sauvegarder les modifications
    await Database.engine.save(subject)
    # Message de succès
    request.session["success_message"] = "Sujet mis à jour avec succès."
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage", status_code=303)
