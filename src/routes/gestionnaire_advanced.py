from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Optional

from src.models.user import User
from src.models.subject import Subject
from src.services.auth_service import get_current_user
from src.services.subject_service import get_subject, get_subjects_by_gestionnaire
from src.services.user_service import get_users
from src.services.idea_service import get_ideas_by_subject, update_idea
from src.services.activity_log_service import get_subject_activities, log_activity
from src.services.metrics_service import MetricsService
from src.services.database import Database

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "templates"))

async def get_current_gestionnaire(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, detail="Not authenticated", headers={"Location": "/auth/login"})
    subjects = await get_subjects_by_gestionnaire(str(current_user.id))
    if not subjects:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits de gestionnaire")
    return current_user

# Remplace la dépendance get_current_gestionnaire par une version qui accepte aussi les superadmins
# Correction: rendre la dépendance asynchrone et utiliser await au lieu de asyncio.run
async def get_current_gestionnaire_or_superadmin(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, detail="Not authenticated", headers={"Location": "/auth/login"})
    if "superadmin" in current_user.roles:
        return current_user
    # Gestionnaire classique
    from src.services.subject_service import get_subjects_by_gestionnaire
    subjects = await get_subjects_by_gestionnaire(str(current_user.id))
    if not subjects:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits de gestionnaire")
    return current_user

@router.get("/gestionnaire/subject/{subject_id}/manage", response_class=HTMLResponse)
async def manage_subject(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """Page de gestion complète d'un sujet"""
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits sur ce sujet")
    
    # Récupérer les métriques détaillées du sujet
    metrics = await MetricsService.get_subject_detailed_metrics(subject_id)
    
    # Récupérer les idées du sujet
    ideas = await get_ideas_by_subject(subject_id)
    
    # Récupérer les utilisateurs du sujet
    all_users = await get_users()
    subject_users = [user for user in all_users if str(user.id) in subject.users_ids]
    
    # Récupérer les gestionnaires du sujet
    subject_gestionnaires = [user for user in all_users if str(user.id) in subject.gestionnaires_ids]
    
    return templates.TemplateResponse("gestionnaire/manage_subject.html", {
        "request": request,
        "current_user": current_user,
        "subject": subject,
        "metrics": metrics,
        "ideas": ideas,
        "subject_users": subject_users,
        "subject_gestionnaires": subject_gestionnaires,
        "all_users": all_users,
        "show_sidebar": True
    })

@router.get("/gestionnaire/subject/{subject_id}/users", response_class=HTMLResponse)
async def manage_subject_users(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """Page de gestion des invités d'un sujet"""
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits sur ce sujet")
    
    all_users = await get_users()
    subject_users = [user for user in all_users if str(user.id) in subject.users_ids]
    available_users = [user for user in all_users if str(user.id) not in subject.users_ids]
    
    return templates.TemplateResponse("gestionnaire/manage_subject_users.html", {
        "request": request,
        "current_user": current_user,
        "subject": subject,
        "subject_users": subject_users,
        "available_users": available_users,
        "show_sidebar": True
    })

@router.post("/gestionnaire/subject/{subject_id}/users/add")
async def add_user_to_subject(subject_id: str, user_id: str = Form(...), request: Request = None, current_user: User = Depends(get_current_gestionnaire)):
    """Ajouter un invité à un sujet"""
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits sur ce sujet")
    
    if user_id not in subject.users_ids:
        subject.users_ids.append(user_id)
        await Database.engine.save(subject)
        await log_activity(
            action="user_added",
            subject_id=subject_id,
            user=current_user,
            description=f"Invité {user_id} ajouté au sujet",
            request=request
        )
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/users/remove")
async def remove_user_from_subject(subject_id: str, user_id: str = Form(...), request: Request = None, current_user: User = Depends(get_current_gestionnaire)):
    """Retirer un invité d'un sujet"""
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits sur ce sujet")
    
    if user_id in subject.users_ids:
        subject.users_ids.remove(user_id)
        await Database.engine.save(subject)
        await log_activity(
            action="user_removed",
            subject_id=subject_id,
            user=current_user,
            description=f"Invité {user_id} retiré du sujet",
            request=request
        )
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/users", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/gestionnaire/subject/{subject_id}/history", response_class=HTMLResponse)
async def subject_history(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """Historique et logs d'un sujet"""
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits sur ce sujet")
    
    activities = await get_subject_activities(subject_id)
    
    return templates.TemplateResponse("gestionnaire/subject_history.html", {
        "request": request,
        "current_user": current_user,
        "subject": subject,
        "activities": activities,
        "show_sidebar": True
    })

@router.get("/gestionnaire/ideas/bulk", response_class=HTMLResponse)
async def bulk_ideas_management(request: Request, current_user: User = Depends(get_current_gestionnaire_or_superadmin)):
    """Page de modification en masse des idées"""
    subjects = await get_subjects_by_gestionnaire(str(current_user.id))
    
    # Récupérer tous les utilisateurs pour éviter les requêtes répétées
    from src.services.user_service import get_user
    all_users = await get_users()
    users_dict = {str(user.id): user for user in all_users}
    
    all_ideas = []
    for subject in subjects:
        ideas = await get_ideas_by_subject(str(subject.id))
        for idea in ideas:
            # Récupérer les informations de l'auteur
            author = users_dict.get(idea.user_id)
            author_email = author.email if author else "Email inconnu"
            
            # Add subject info without modifying the model
            idea_dict = {
                "idea": idea,
                "subject_name": subject.name,
                "subject_id": str(subject.id),
                "show_votes_during_vote": subject.show_votes_during_vote,
                "author_email": author_email
            }
            all_ideas.append(idea_dict)
    
    # Préparer le contexte avec les informations de l'organisation
    from src.utils.template_helpers import add_organization_context
    context = {
        "request": request,
        "current_user": current_user,
        "subjects": subjects,
        "all_ideas": all_ideas,
        "show_sidebar": True
    }
    
    # Ajouter les informations de l'organisation
    context = await add_organization_context(context)
    
    return templates.TemplateResponse("gestionnaire/bulk_ideas.html", context)

@router.post("/gestionnaire/ideas/bulk/update")
async def bulk_update_ideas(request: Request, current_user: User = Depends(get_current_gestionnaire_or_superadmin)):
    """Mise à jour en masse des idées"""
    form = await request.form()
    
    updated_count = 0
    for key, value in form.items():
        if key.startswith("idea_") and key.endswith("_title"):
            idea_id = key.replace("idea_", "").replace("_title", "")
            
            # Récupérer l'idée en utilisant le service approprié
            from src.services.idea_service import get_idea
            idea = await get_idea(idea_id)
            if idea:
                # Vérifier que l'utilisateur a les droits sur le sujet de cette idée
                subject = await get_subject(idea.subject_id)
                if subject and str(current_user.id) in subject.gestionnaires_ids:
                    # Préparer les nouvelles valeurs
                    new_title = value
                    new_description = form.get(f"idea_{idea_id}_description", idea.description)
                    
                    # Utiliser la fonction update_idea du service
                    updated_idea = await update_idea(idea_id, new_title, new_description)
                    
                    if updated_idea:
                        await log_activity(
                            action="idea_updated",
                            subject_id=idea.subject_id,
                            user=current_user,
                            description=f"Idée '{new_title}' mise à jour en masse",
                            details=f"Titre: '{new_title}', Description: '{new_description[:100]}...'",
                            request=request
                        )
                        updated_count += 1
    
    return RedirectResponse(url=f"/gestionnaire/ideas/bulk?updated={updated_count}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/toggle_emission")
async def toggle_emission(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """Activer/désactiver l'émission d'idées"""
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits sur ce sujet")
    
    subject.emission_active = not subject.emission_active
    await Database.engine.save(subject)
    
    action = "activated" if subject.emission_active else "deactivated"
    await log_activity(
        action=f"emission_{action}",
        subject_id=subject_id,
        user=current_user,
        description=f"Émission d'idées {action}",
        request=request
    )
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/toggle_vote")
async def toggle_vote(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """Activer/désactiver les sessions de vote"""
    subject = await get_subject(subject_id)
    if not subject or str(current_user.id) not in subject.gestionnaires_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits sur ce sujet")
    
    # Si on active le vote, on désactive l'émission
    if not subject.vote_active:
        subject.vote_active = True
        subject.emission_active = False
        action = "activated"
    else:
        subject.vote_active = False
        action = "deactivated"
    
    await Database.engine.save(subject)
    await log_activity(
        action=f"vote_{action}",
        subject_id=subject_id,
        user=current_user,
        description=f"Session de vote {action}",
        request=request
    )
    
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/gestionnaire/logs", response_class=HTMLResponse)
async def gestionnaire_logs(request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """Page des historiques et logs du gestionnaire"""
    try:
        # Récupérer les sujets du gestionnaire
        subjects = await get_subjects_by_gestionnaire(str(current_user.id))
        
        all_activities = []
        for subject in subjects:
            activities = await get_subject_activities(str(subject.id))
            # Enrichir avec le nom du sujet
            for activity in activities:
                # Convertir l'ActivityLog en dictionnaire et ajouter subject_name
                activity_dict = {
                    "id": str(activity.id),
                    "user_id": activity.user_id,
                    "subject_id": activity.subject_id,
                    "action": activity.action,
                    "details": activity.details,
                    "timestamp": activity.timestamp.isoformat() if activity.timestamp else None,
                    "subject_name": subject.name
                }
                all_activities.append(activity_dict)
        
        # Trier par date décroissante
        all_activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Prendre les 100 dernières activités
        recent_activities = all_activities[:100]
        
        return templates.TemplateResponse("gestionnaire/logs.html", {
            "request": request,
            "current_user": current_user,
            "activities": recent_activities,
            "subjects": subjects,
            "activities_count": len(recent_activities),
            "show_sidebar": True
        })
    except Exception as e:
        print(f"❌ Erreur logs gestionnaire: {e}")
        return templates.TemplateResponse("gestionnaire/logs.html", {
            "request": request,
            "current_user": current_user,
            "activities": [],
            "subjects": [],
            "activities_count": 0,
            "show_sidebar": True
        })

@router.get("/gestionnaire/managers", response_class=HTMLResponse)
async def gestionnaire_managers(request: Request, current_user: User = Depends(get_current_gestionnaire)):
    """Page de gestion des gestionnaires"""
    try:
        # Récupérer les sujets du gestionnaire
        subjects = await get_subjects_by_gestionnaire(str(current_user.id))
        
        # Récupérer tous les utilisateurs
        all_users = await get_users()
        
        # Organiser les gestionnaires par sujet
        subjects_with_managers = []
        for subject in subjects:
            subject_managers = [user for user in all_users if str(user.id) in subject.gestionnaires_ids]
            # Récupérer tous les invités (utilisateurs sans rôle superadmin) qui ne sont pas déjà gestionnaires de ce sujet
            potential_managers = [
                user for user in all_users 
                if "superadmin" not in user.roles and str(user.id) not in subject.gestionnaires_ids
            ]
            
            subjects_with_managers.append({
                "subject": subject,
                "managers": subject_managers,
                "potential_managers": potential_managers
            })
        
        return templates.TemplateResponse("gestionnaire/managers.html", {
            "request": request,
            "current_user": current_user,
            "subjects_with_managers": subjects_with_managers,
            "subjects_count": len(subjects),
            "show_sidebar": True
        })
    except Exception as e:
        print(f"❌ Erreur managers gestionnaire: {e}")
        return templates.TemplateResponse("gestionnaire/managers.html", {
            "request": request,
            "current_user": current_user,
            "subjects_with_managers": [],
            "subjects_count": 0,
            "show_sidebar": True
        })

@router.post("/gestionnaire/managers/add")
async def add_manager_to_subject(
    request: Request,
    subject_id: str = Form(...),
    user_id: str = Form(...),
    current_user: User = Depends(get_current_gestionnaire)
):
    """Ajouter un gestionnaire à un sujet (et promouvoir l'invité si nécessaire)"""
    try:
        print(f"DEBUG - Tentative d'ajout gestionnaire: subject_id={subject_id}, user_id={user_id}")
        
        subject = await get_subject(subject_id)
        if not subject or str(current_user.id) not in subject.gestionnaires_ids:
            print(f"DEBUG - Accès refusé au sujet {subject_id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits sur ce sujet")
        
        # Récupérer l'utilisateur à promouvoir (utiliser le service qui gère ObjectId)
        from src.services.user_service import get_user
        user_to_add = await get_user(user_id)
        if not user_to_add:
            print(f"DEBUG - Utilisateur {user_id} introuvable")
            request.session["error_message"] = "Utilisateur introuvable."
            return RedirectResponse(url="/gestionnaire/managers", status_code=303)
        
        print(f"DEBUG - Utilisateur trouvé: {user_to_add.prenom} {user_to_add.nom}")
        
        # Vérifier que l'utilisateur n'est pas superadmin
        if "superadmin" in user_to_add.roles:
            print(f"DEBUG - Tentative de promotion d'un superadmin")
            request.session["error_message"] = "Impossible de promouvoir un superadmin."
            return RedirectResponse(url="/gestionnaire/managers", status_code=303)
        
        # Promouvoir l'utilisateur au rôle gestionnaire s'il ne l'a pas déjà
        roles_updated = False
        if "gestionnaire" not in user_to_add.roles:
            print(f"DEBUG - Promotion au rôle gestionnaire")
            user_to_add.roles.append("gestionnaire")
            await Database.engine.save(user_to_add)
            roles_updated = True
        
        # Ajouter le gestionnaire au sujet
        if user_id not in subject.gestionnaires_ids:
            print(f"DEBUG - Ajout au sujet {subject.name}")
            subject.gestionnaires_ids.append(user_id)
            await Database.engine.save(subject)
            
            # Log de l'activité
            action_details = f"Gestionnaire {user_to_add.prenom} {user_to_add.nom} ajouté au sujet {subject.name}"
            if roles_updated:
                action_details += " (promu depuis invité)"
            
            await log_activity(
                action="add_manager",
                subject_id=subject_id,
                user=current_user,
                description=action_details,
                details=f"Utilisateur {user_to_add.email} promu gestionnaire",
                request=request
            )
            
            success_msg = f"Gestionnaire {user_to_add.prenom} {user_to_add.nom} ajouté avec succès au sujet {subject.name}."
            if roles_updated:
                success_msg += " L'invité a été promu gestionnaire."
            request.session["success_message"] = success_msg
            print(f"DEBUG - Succès: {success_msg}")
        else:
            print(f"DEBUG - Utilisateur déjà gestionnaire")
            request.session["warning_message"] = "Cet utilisateur est déjà gestionnaire de ce sujet."
        
        return RedirectResponse(url="/gestionnaire/managers", status_code=303)
    except Exception as e:
        print(f"❌ Erreur ajout gestionnaire: {e}")
        import traceback
        traceback.print_exc()
        request.session["error_message"] = f"Erreur lors de l'ajout du gestionnaire: {str(e)}"
        return RedirectResponse(url="/gestionnaire/managers", status_code=303)

@router.post("/gestionnaire/managers/remove")
async def remove_manager_from_subject(
    request: Request,
    subject_id: str = Form(...),
    user_id: str = Form(...),
    current_user: User = Depends(get_current_gestionnaire)
):
    """Retirer un gestionnaire d'un sujet"""
    try:
        subject = await get_subject(subject_id)
        if not subject or str(current_user.id) not in subject.gestionnaires_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits sur ce sujet")
        
        # Vérifier qu'on ne retire pas le dernier gestionnaire
        if len(subject.gestionnaires_ids) <= 1:
            request.session["error_message"] = "Impossible de retirer le dernier gestionnaire du sujet."
            return RedirectResponse(url="/gestionnaire/managers", status_code=303)
        
        # Retirer le gestionnaire du sujet
        if user_id in subject.gestionnaires_ids:
            subject.gestionnaires_ids.remove(user_id)
            await Database.engine.save(subject)
            
            # Récupérer le nom de l'utilisateur pour le log
            from src.services.user_service import get_user
            user_removed = await get_user(user_id)
            username = f"{user_removed.prenom} {user_removed.nom}" if user_removed else "Utilisateur inconnu"
            
            # Log de l'activité
            await log_activity(
                action="remove_manager",
                subject_id=subject_id,
                user=current_user,
                description=f"Gestionnaire {username} retiré du sujet {subject.name}",
                details=f"Gestionnaire supprimé par {current_user.prenom} {current_user.nom}",
                request=request
            )
            
            request.session["success_message"] = f"Gestionnaire {username} retiré avec succès du sujet {subject.name}."
        else:
            request.session["warning_message"] = "Cet utilisateur n'est pas gestionnaire de ce sujet."
        
        return RedirectResponse(url="/gestionnaire/managers", status_code=303)
    except Exception as e:
        print(f"❌ Erreur suppression gestionnaire: {e}")
        request.session["error_message"] = "Erreur lors de la suppression du gestionnaire."
        return RedirectResponse(url="/gestionnaire/managers", status_code=303)

@router.post("/gestionnaire/ideas/bulk/delete")
async def bulk_delete_ideas(request: Request, current_user: User = Depends(get_current_gestionnaire_or_superadmin)):
    """Suppression en masse des idées sélectionnées"""
    form = await request.form()
    idea_ids_raw = form.get("idea_ids")
    import json
    try:
        idea_ids = json.loads(idea_ids_raw) if idea_ids_raw else []
    except Exception:
        idea_ids = []
    
    from src.services.idea_service import get_idea, delete_idea
    from src.services.subject_service import get_subject
    from src.services.activity_log_service import log_activity
    deleted_count = 0
    for idea_id in idea_ids:
        idea = await get_idea(idea_id)
        if not idea:
            continue
        subject = await get_subject(idea.subject_id)
        if not subject or str(current_user.id) not in subject.gestionnaires_ids:
            continue
        idea_title = idea.title
        success = await delete_idea(idea_id)
        if success:
            await log_activity(
                action="delete_idea",
                subject_id=idea.subject_id,
                user=current_user,
                description=f"Suppression en masse de l'idée '{idea_title}'",
                details="Suppression groupée",
                request=request
            )
            deleted_count += 1
    request.session["success_message"] = f"{deleted_count} idée(s) supprimée(s) avec succès."
    return RedirectResponse(url="/gestionnaire/ideas/bulk", status_code=status.HTTP_303_SEE_OTHER)
