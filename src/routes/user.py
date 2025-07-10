from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Optional

from src.models.user import User
from src.models.idea import Idea
from src.models.subject import Subject
from src.services.auth_service import get_current_user
from src.services.subject_service import get_subject
from src.services.idea_service import create_idea, get_ideas_by_subject, get_idea
from src.services.vote_service import VoteService
from src.services.database import Database
from src.services.stats_service import get_user_dashboard_stats
from src.services.activity_log_service import log_activity
from src.services.metrics_service import MetricsService
from src.utils.flash_messages import flash

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "templates"))

def get_active_role(request: Request, user: User) -> str:
    """Récupère le rôle actif de l'utilisateur depuis la session"""
    if len(user.roles) == 1:
        return user.roles[0]
    
    # Pour les utilisateurs multi-rôles, vérifier la session
    active_role = request.session.get("active_role")
    if active_role and active_role in user.roles:
        return active_role
    
    # Rôle par défaut (prioriser superadmin > gestionnaire > user)
    if "superadmin" in user.roles:
        return "superadmin"
    elif "gestionnaire" in user.roles:
        return "gestionnaire"
    else:
        return "user"

def set_active_role(request: Request, role: str):
    """Définit le rôle actif dans la session"""
    request.session["active_role"] = role

async def get_current_normal_user(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER, 
            detail="Not authenticated", 
            headers={"Location": "/auth/login"}
        )
    return current_user

async def get_vote_subjects_for_user(user_id: str, request=None):
    """Récupère les sujets avec vote actif pour un utilisateur donné (retourne des dicts enrichis)"""
    try:
        all_subjects = await Database.engine.find(Subject)
        vote_subjects = []
        
        # Récupérer les préférences utilisateur si la request est fournie
        selected_subject_ids = None
        if request:
            user_preferences = request.session.get("subject_preferences", {})
            selected_subject_ids = user_preferences.get(user_id, [])
            print(f"DEBUG - Préférences vote pour utilisateur {user_id}: {selected_subject_ids}")
        
        from src.services.idea_service import get_ideas_by_subject
        for subject in all_subjects:
            if hasattr(subject, 'vote_active') and subject.vote_active and (user_id in subject.users_ids or user_id in subject.gestionnaires_ids):
                # Si l'utilisateur a des préférences définies, vérifier si ce sujet est sélectionné
                if selected_subject_ids and str(subject.id) not in selected_subject_ids:
                    print(f"DEBUG - Sujet {subject.name} ignoré car pas dans les préférences")
                    continue
                
                # Vérifier si l'utilisateur peut encore voter pour ce sujet
                user_votes_count = await VoteService.get_user_votes_count_for_subject(user_id, subject.id)
                vote_limit = getattr(subject, 'vote_limit', 0)
                
                # Ne retourner le sujet que si l'utilisateur peut encore voter
                if vote_limit > 0 and user_votes_count < vote_limit:
                    ideas = await get_ideas_by_subject(subject.id)
                    total_votes = 0
                    
                    # Enrichir chaque idée avec les informations de votes
                    enriched_ideas = []
                    for idea in ideas:
                        votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
                        total_votes += votes_count
                        
                        # Récupérer les IDs des votants pour cette idée
                        voter_ids = await VoteService.get_voter_ids_for_idea(str(idea.id))
                        
                        # Créer un objet dict avec toutes les propriétés de l'idée + votes
                        idea_dict = {
                            "id": idea.id,
                            "subject_id": idea.subject_id,
                            "user_id": idea.user_id,
                            "title": idea.title,
                            "description": idea.description,
                            "created_at": idea.created_at,
                            "votes": voter_ids,  # Liste des IDs des votants (compatibilité template)
                            "votes_count": votes_count
                        }
                        enriched_ideas.append(idea_dict)
                    
                    print(f"DEBUG - Sujet de vote ajouté: {subject.name} avec {len(enriched_ideas)} idées")
                    vote_subjects.append({
                        "subject": subject,
                        "ideas": enriched_ideas,
                        "ideas_count": len(enriched_ideas),
                        "votes_count": total_votes
                    })
        
        print(f"DEBUG - Nombre total de sujets de vote retournés: {len(vote_subjects)}")
        return vote_subjects
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des sujets de vote: {e}")
        return []

async def get_user_votes_count(user_id: str):
    """Compte le nombre total de votes de l'utilisateur"""
    try:
        all_ideas = await Database.engine.find(Idea)
        votes_count = 0
        for idea in all_ideas:
            if await VoteService.has_user_voted_for_idea(str(idea.id), user_id):
                votes_count += 1
        return votes_count
    except Exception as e:
        print(f"❌ Erreur lors du comptage des votes: {e}")
        return 0

async def get_user_votes_for_subjects(user_id: str):
    """Récupère le nombre de votes par sujet pour un utilisateur"""
    try:
        all_ideas = await Database.engine.find(Idea)
        votes_per_subject = {}
        
        for idea in all_ideas:
            if await VoteService.has_user_voted_for_idea(str(idea.id), user_id):
                subject_id = idea.subject_id
                votes_per_subject[subject_id] = votes_per_subject.get(subject_id, 0) + 1
        
        return votes_per_subject
    except Exception as e:
        print(f"❌ Erreur lors du comptage des votes par sujet: {e}")
        return {}

@router.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request, current_user: User = Depends(get_current_normal_user)):
    try:
        # Récupérer les métriques pour l'utilisateur
        metrics = await MetricsService.get_user_dashboard_metrics(current_user)
        
        all_user_subjects, user_subjects, user_stats, user_preferences = await get_user_dashboard_stats(current_user, request)
        
        print(f"DEBUG Dashboard - Tous les sujets: {len(all_user_subjects)}")
        print(f"DEBUG Dashboard - Sujets filtrés: {len(user_subjects)}")
        for subject in user_subjects:
            print(f"DEBUG - Sujet affiché: {subject.name} (ID: {subject.id})")
        
        # Récupérer les sujets avec vote actif (en tenant compte des préférences)
        vote_subjects = await get_vote_subjects_for_user(str(current_user.id), request)
        
        # Récupérer les votes par sujet pour calculer les votes restants correctement
        user_votes_for_subject = await get_user_votes_for_subjects(str(current_user.id))
        
        # Préparer le contexte avec les informations de l'organisation
        from src.utils.template_helpers import add_organization_context
        context = {
            "request": request,
            "current_user": current_user,
            "all_user_subjects": all_user_subjects,  # Tous les sujets pour la sélection
            "user_subjects": user_subjects,  # Sujets filtrés selon les préférences
            "user_preferences": user_preferences,  # Dictionnaire des préférences pour le template
            "user_stats": user_stats,
            "vote_subjects": vote_subjects,
            "user_votes_for_subject": user_votes_for_subject,
            "metrics": metrics,
            "show_sidebar": True
        }
        
        # Ajouter les informations de l'organisation
        context = await add_organization_context(context)
        
        return templates.TemplateResponse("user/dashboard.html", context)
    
    except Exception as e:
        print(f"❌ Erreur dashboard utilisateur: {e}")
        # Préparer le contexte avec les informations de l'organisation
        from src.utils.template_helpers import add_organization_context
        context = {
            "request": request,
            "current_user": current_user,
            "user_subjects": [],
            "user_stats": {
                'subjects_count': 0,
                'user_ideas_count': 0,
                'user_votes_count': 0,
                'pending_count': 0
            },
            "vote_subjects": [],
            "user_votes_for_subject": {},
            "metrics": {
                'subjects_count': 0,
                'my_ideas': 0,
                'my_votes': 0,
                'available_votes': 0,
                'subjects_data': [],
                'charts': {
                    'subjects_overview': [],
                    'summary_stats': {
                        'my_ideas': 0,
                        'my_votes': 0,
                        'total_ideas': 0
                    }
                }
            },
            "show_sidebar": True
        }
        
        # Ajouter les informations de l'organisation
        context = await add_organization_context(context)
        
        return templates.TemplateResponse("user/dashboard.html", context)

@router.get("/user/vote", response_class=HTMLResponse)
async def user_vote_center(request: Request, current_user: User = Depends(get_current_normal_user)):
    """Centre de vote pour l'utilisateur"""
    try:
        # Récupérer les sujets avec vote actif (en tenant compte des préférences)
        vote_subjects = await get_vote_subjects_for_user(str(current_user.id), request)
        
        # Compter les votes de l'utilisateur
        user_votes_count = await get_user_votes_count(str(current_user.id))
        
        # Compter le nombre total d'idées disponibles
        total_ideas_count = sum(len(subject["ideas"]) for subject in vote_subjects)
        
        # Récupérer les votes par sujet
        user_votes_for_subject = await get_user_votes_for_subjects(str(current_user.id))
        
        # Récupérer les votes récents (optionnel)
        recent_votes = []  # Vous pouvez implémenter cette fonctionnalité plus tard
        
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "vote_subjects": vote_subjects,
            "user_votes_count": user_votes_count,
            "total_ideas_count": total_ideas_count,
            "user_votes_for_subject": user_votes_for_subject,
            "recent_votes": recent_votes
        })
        return templates.TemplateResponse("user/vote.html", context)
    
    except Exception as e:
        print(f"❌ Erreur centre de vote: {e}")
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "vote_subjects": [],
            "user_votes_count": 0,
            "total_ideas_count": 0,
            "user_votes_for_subject": {},
            "recent_votes": [],
            "error": "Erreur lors du chargement du centre de vote"
        })
        return templates.TemplateResponse("user/vote.html", context)

@router.get("/user/subject/{subject_id}/ideas", response_class=HTMLResponse)
async def subject_ideas(subject_id: str, request: Request, current_user: User = Depends(get_current_normal_user)):
    subject = await get_subject(subject_id)
    if not subject or (str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas attribué à ce sujet.")
    ideas = await get_ideas_by_subject(subject_id)
    
    # DEBUG: Vérifier l'état des votes dans la base de données
    print(f"DEBUG - Nombre d'idées trouvées: {len(ideas)}")
    for idea in ideas:
        votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
        print(f"DEBUG - Idée '{idea.title}': votes = {votes_count}")
    
    # Calculer les métriques de votes
    total_votes = 0
    my_votes_count = 0
    print(f"DEBUG - Calcul des votes pour l'utilisateur {current_user.id} dans le sujet {subject_id}")
    for idea in ideas:
        votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
        total_votes += votes_count
        has_voted = await VoteService.has_user_voted_for_idea(str(idea.id), str(current_user.id))
        if has_voted:
            my_votes_count += 1
            print(f"DEBUG - L'utilisateur a voté pour l'idée '{idea.title}' (ID: {idea.id})")
        else:
            print(f"DEBUG - L'utilisateur n'a PAS voté pour l'idée '{idea.title}' (ID: {idea.id})")
    
    vote_limit = getattr(subject, 'vote_limit', 0)
    vote_active = getattr(subject, 'vote_active', False)
    votes_remaining = max(0, vote_limit - my_votes_count) if vote_active else 0
    
    print(f"DEBUG - Résultat final: my_votes_count={my_votes_count}, vote_limit={vote_limit}, votes_remaining={votes_remaining}")
    
    # Calculer les statistiques par idée
    ideas_stats = []
    for idea in ideas:
        vote_count = await VoteService.get_votes_count_for_idea(str(idea.id))
        has_voted = await VoteService.has_user_voted_for_idea(str(idea.id), str(current_user.id))
        ideas_stats.append({
            "idea": idea,
            "vote_count": vote_count,
            "has_voted": has_voted,
            "vote_percentage": round((vote_count / len(subject.users_ids + subject.gestionnaires_ids)) * 100, 1) if (subject.users_ids + subject.gestionnaires_ids) else 0
        })
    
    # Métriques de participation
    total_participants = len(set(subject.users_ids + subject.gestionnaires_ids))
    # Calculer le nombre de participants qui ont voté
    all_voters = set()
    for idea in ideas:
        voter_ids = await VoteService.get_voter_ids_for_idea(str(idea.id))
        all_voters.update(voter_ids)
    participants_who_voted = len(all_voters)
    participation_rate = round((participants_who_voted / total_participants) * 100, 1) if total_participants > 0 else 0
    
    # Top des idées (triées par nombre de votes)
    ideas_with_votes = []
    for idea in ideas:
        votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
        ideas_with_votes.append((idea, votes_count))
    
    top_ideas = sorted(ideas_with_votes, key=lambda x: x[1], reverse=True)
    
    # Enrichir les top_ideas avec l'information si l'utilisateur a voté
    top_ideas_enriched = []
    for idea, votes_count in top_ideas:
        has_voted = await VoteService.has_user_voted_for_idea(str(idea.id), str(current_user.id))
        print(f"DEBUG - Idée '{idea.title}': {votes_count} votes")
        top_ideas_enriched.append({
            "id": str(idea.id),
            "title": idea.title,
            "description": idea.description,
            "votes_count": votes_count,
            "user_has_voted": has_voted
        })
    
    most_voted_idea = top_ideas[0][0] if top_ideas else None
    
    metrics = {
        "total_ideas": len(ideas),
        "total_votes": total_votes,
        "my_votes_count": my_votes_count,
        "votes_remaining": votes_remaining,
        "vote_limit": vote_limit,
        "total_participants": total_participants,
        "participants_who_voted": participants_who_voted,
        "participation_rate": participation_rate,
        "most_voted_idea": most_voted_idea,
        "average_votes_per_idea": round(total_votes / len(ideas), 2) if ideas else 0
    }
    
    from src.utils.template_helpers import add_organization_context
    context = await add_organization_context({
        "request": request, 
        "subject": subject, 
        "ideas": ideas_stats, 
        "current_user": current_user,
        "metrics": metrics,
        "top_ideas": top_ideas_enriched
    })
    return templates.TemplateResponse("user/subject_ideas.html", context)

@router.post("/user/subject/{subject_id}/ideas/create", response_class=HTMLResponse)
async def create_new_idea(subject_id: str, request: Request, title: str = Form(...), description: Optional[str] = Form(None), current_user: User = Depends(get_current_normal_user)):
    subject = await get_subject(subject_id)
    if not subject or (str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas attribué à ce sujet.")
    
    if not subject.emission_active:
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request, 
            "subject": subject, 
            "ideas": await get_ideas_by_subject(subject_id), 
            "current_user": current_user, 
            "error": "L'émission d'idées n'est pas active pour ce sujet."
        })
        return templates.TemplateResponse("user/subject_ideas.html", context)

    idea = Idea(subject_id=subject_id, user_id=str(current_user.id), title=title, description=description)
    await create_idea(idea)
    return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/user/ideas", response_class=HTMLResponse)
async def user_ideas(request: Request, current_user: User = Depends(get_current_normal_user)):
    ideas = await Database.engine.find(Idea, Idea.user_id == str(current_user.id))
    from src.services.subject_service import get_subject
    ideas_with_subject = []
    for idea in ideas:
        subject = await get_subject(idea.subject_id)
        subject_name = subject.name if subject else idea.subject_id
        votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
        voter_ids = await VoteService.get_voter_ids_for_idea(str(idea.id))
        ideas_with_subject.append({
            "title": idea.title,
            "description": idea.description,
            "votes": voter_ids,  # Liste des IDs des votants pour compatibilité
            "votes_count": votes_count,
            "created_at": idea.created_at,
            "subject_name": subject_name
        })
    
    from src.utils.template_helpers import add_organization_context
    context = await add_organization_context({
        "request": request, 
        "ideas": ideas_with_subject, 
        "current_user": current_user
    })
    return templates.TemplateResponse("user/my_ideas.html", context)

@router.post("/user/idea/{idea_id}/vote")
async def vote_idea(
    idea_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    if "user" not in current_user.roles:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        # Get the idea
        idea = await get_idea(idea_id)
        if not idea:
            flash(request, "Idée non trouvée", "error")
            return RedirectResponse(url="/user/vote", status_code=303)
        
        # Get the subject to check if voting is active
        subject = await get_subject(idea.subject_id)
        if not subject:
            flash(request, "Sujet non trouvé", "error")
            return RedirectResponse(url="/user/vote", status_code=303)
        
        # Check if voting session is active
        if not getattr(subject, 'vote_active', False):
            flash(request, "La session de vote n'est pas active pour ce sujet", "error")
            return RedirectResponse(url=f"/user/subject/{subject.id}/ideas", status_code=303)
        
        # Check if user has access to this subject
        if str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids:
            flash(request, "Vous n'avez pas accès à ce sujet", "error")
            return RedirectResponse(url="/user/vote", status_code=303)
        
        # Check if user has already voted
        has_voted = await VoteService.has_user_voted_for_idea(idea_id, str(current_user.id))
        
        if has_voted:
            # Remove vote
            await VoteService.remove_vote(idea_id, str(current_user.id))
            flash(request, "Vote retiré avec succès", "success")
            await log_activity(
                action="vote_removed",
                subject_id=idea.subject_id,
                user=current_user,
                description=f"Vote retiré pour l'idée: {idea.title}",
                request=request
            )
        else:
            # Add vote
            await VoteService.add_vote(idea_id, str(current_user.id))
            flash(request, "Vote ajouté avec succès", "success")
            await log_activity(
                action="vote_added",
                subject_id=idea.subject_id,
                user=current_user,
                description=f"Vote ajouté pour l'idée: {idea.title}",
                request=request
            )
        
        return RedirectResponse(url="/user/vote", status_code=303)
        
    except Exception as e:
        flash(request, f"Erreur lors du vote: {str(e)}", "error")
        return RedirectResponse(url="/user/vote", status_code=303)

@router.post("/user/idea/{idea_id}/remove_vote")
async def remove_vote(
    idea_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Remove vote from an idea"""
    try:
        # Get the idea to check if it exists and get subject info
        idea = await get_idea(idea_id)
        if not idea:
            flash(request, "Idée non trouvée", "error")
            return RedirectResponse(url="/user/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        
        # Get subject info
        subject = await get_subject(idea.subject_id)
        if not subject:
            flash(request, "Sujet non trouvé", "error")
            return RedirectResponse(url="/user/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        
        # Remove the vote
        success = await VoteService.remove_vote(idea_id, current_user.id)
        
        if success:
            flash(request, "Vote retiré avec succès", "success")
            # Log the activity
            await log_activity(
                action="remove_vote_from_idea",
                subject_id=idea.subject_id,
                user=current_user,
                description=f"Vote retiré pour l'idée: {idea.title}",
                details=f"Idea ID: {idea_id}, Subject: {subject.title}",
                request=request
            )
        else:
            flash(request, "Erreur lors du retrait du vote", "error")
        
        return RedirectResponse(url=f"/user/subject/{subject.id}/ideas", status_code=status.HTTP_303_SEE_OTHER)
        
    except Exception as e:
        flash(request, f"Erreur: {str(e)}", "error")
        return RedirectResponse(url="/user/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/choose-role", response_class=HTMLResponse)
async def choose_role(request: Request, current_user: User = Depends(get_current_normal_user)):
    # Si un seul rôle, redirige automatiquement
    if len(current_user.roles) == 1:
        role = current_user.roles[0].lower()
        if role == "superadmin":
            return RedirectResponse(url="/superadmin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        elif role == "gestionnaire":
            return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url="/user/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    
    # Pour les utilisateurs avec plusieurs rôles, afficher le choix
    # Prioriser certains rôles pour une meilleure UX
    primary_roles = []
    if "superadmin" in current_user.roles:
        primary_roles.append({"name": "superadmin", "display": "Super Administrateur", "url": "/superadmin/dashboard", "icon": "bi-shield-fill-check", "color": "danger"})
    if "gestionnaire" in current_user.roles:
        primary_roles.append({"name": "gestionnaire", "display": "Gestionnaire", "url": "/gestionnaire/dashboard", "icon": "bi-kanban", "color": "warning"})
    if "user" in current_user.roles:
        primary_roles.append({"name": "user", "display": "Invité", "url": "/user/dashboard", "icon": "bi-person", "color": "primary"})
    
    from src.utils.template_helpers import add_organization_context
    context = await add_organization_context({
        "request": request, 
        "roles": current_user.roles,
        "primary_roles": primary_roles,
        "current_user": current_user
    })
    return templates.TemplateResponse("choose_role.html", context)

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_redirect(request: Request, current_user: User = Depends(get_current_normal_user)):
    # Redirige selon le nombre de rôles
    if len(current_user.roles) == 1:
        if "gestionnaire" in [r.lower() for r in current_user.roles]:
            return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url="/user/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/choose-role", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/user/idea/{idea_id}/vote", response_class=HTMLResponse)
async def show_vote_page(idea_id: str, request: Request, current_user: User = Depends(get_current_normal_user)):
    """Affiche la page de vote pour une idée"""
    try:
        # Utiliser le service get_idea qui gère correctement la conversion ObjectId
        idea = await get_idea(idea_id)
        if not idea:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idée non trouvée.")
        
        # Récupérer le sujet associé
        subject = await get_subject(idea.subject_id)
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé.")
        
        # Vérifier que l'utilisateur a accès à ce sujet
        if str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas accès à cette idée.")
        
        # Vérifier si l'utilisateur a déjà voté
        user_has_voted = await VoteService.has_user_voted_for_idea(idea_id, str(current_user.id))
        
        # Compter les votes pour cette idée
        votes_count = await VoteService.get_votes_count_for_idea(idea_id)
        
        # Compter les votes de l'utilisateur
        user_votes_count = await get_user_votes_count(str(current_user.id))
        
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "idea": idea,
            "subject": subject,
            "has_voted": user_has_voted,
            "votes_count": votes_count,
            "total_ideas_count": 1,
            "user_votes_count": user_votes_count
        })
        return templates.TemplateResponse("user/vote.html", context)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur lors de l'affichage de la page de vote: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur serveur.")

@router.post("/user/vote/batch")
async def batch_vote(request: Request, current_user: User = Depends(get_current_user)):
    try:
        form = await request.form()
        idea_ids = form.getlist("idea_ids")
        
        if not idea_ids:
            flash(request, "Aucune idée sélectionnée", "error")
            return RedirectResponse(url="/user/vote", status_code=303)
        
        success_count = 0
        votes_by_subject = {}  # Pour compter les votes par sujet
        
        # Vérifier chaque idée et son sujet avant de voter
        for idea_id in idea_ids:
            try:
                # Get the idea
                idea = await get_idea(idea_id)
                if not idea:
                    continue
                
                # Get the subject to check if voting is active
                subject = await get_subject(idea.subject_id)
                if not subject:
                    continue
                
                # Check if voting session is active
                if not getattr(subject, 'vote_active', False):
                    flash(request, f"La session de vote n'est pas active pour le sujet '{subject.name}'", "error")
                    continue
                
                # Check if user has access to this subject
                if str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids:
                    continue
                
                # Vérifier la limite de votes pour ce sujet
                subject_id = idea.subject_id
                if subject_id not in votes_by_subject:
                    # Récupérer les votes actuels de l'utilisateur pour ce sujet
                    current_votes = await VoteService.get_user_votes_count_for_subject(str(current_user.id), subject_id)
                    votes_by_subject[subject_id] = {
                        'current': current_votes,
                        'limit': getattr(subject, 'vote_limit', 0),
                        'new_votes': 0,
                        'subject_name': subject.name
                    }
                
                # Vérifier si on peut encore voter pour ce sujet
                subject_votes = votes_by_subject[subject_id]
                total_votes_after = subject_votes['current'] + subject_votes['new_votes'] + 1
                
                if total_votes_after > subject_votes['limit']:
                    flash(request, f"Limite de votes atteinte pour le sujet '{subject_votes['subject_name']}' ({subject_votes['limit']} votes maximum)", "warning")
                    continue
                
                # Add vote if all checks pass
                await VoteService.add_vote(idea_id, str(current_user.id))
                success_count += 1
                votes_by_subject[subject_id]['new_votes'] += 1
                
            except ValueError as ve:
                # Erreur de limite ou déjà voté
                flash(request, str(ve), "warning")
                continue
            except Exception as e:
                print(f"Erreur lors du vote groupé pour l'idée {idea_id}: {e}")
        
        if success_count > 0:
            flash(request, f"{success_count} vote(s) enregistré(s) avec succès.", "success")
        elif len(idea_ids) > 0:
            flash(request, "Aucun vote n'a pu être enregistré. Vérifiez les limites de votes et que les sessions sont actives.", "warning")
        
        return RedirectResponse(url="/user/vote", status_code=303)
    except Exception as e:
        print(f"❌ Erreur lors du vote en lot: {e}")
        flash(request, "Erreur lors du vote en lot", "error")
        return RedirectResponse(url="/user/vote", status_code=303)
        return RedirectResponse(url="/user/vote", status_code=303)

@router.get("/user/subjects", response_class=HTMLResponse)
async def user_subjects(request: Request, current_user: User = Depends(get_current_normal_user)):
    """Page pour afficher tous les sujets de l'utilisateur"""
    try:
        # Récupérer les sujets assignés à l'utilisateur
        all_subjects = await Database.engine.find(Subject)
        user_subjects = []
        
        for subject in all_subjects:
            if str(current_user.id) in subject.users_ids or str(current_user.id) in subject.gestionnaires_ids:
                # Récupérer les idées du sujet
                ideas = await get_ideas_by_subject(str(subject.id))
                my_ideas = [idea for idea in ideas if idea.user_id == str(current_user.id)]
                
                # Compter les votes de l'utilisateur pour ce sujet
                my_votes_count = 0
                for idea in ideas:
                    if await VoteService.has_user_voted_for_idea(str(idea.id), str(current_user.id)):
                        my_votes_count += 1
                
                vote_limit = getattr(subject, 'vote_limit', 0)
                vote_active = getattr(subject, 'vote_active', False)
                
                user_subjects.append({
                    "subject": subject,
                    "total_ideas": len(ideas),
                    "my_ideas": len(my_ideas),
                    "my_votes": my_votes_count,
                    "available_votes": max(0, vote_limit - my_votes_count) if vote_active else 0
                })
        
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "user_subjects": user_subjects,
            "subjects_count": len(user_subjects)
        })
        return templates.TemplateResponse("user/subjects.html", context)
    except Exception as e:
        print(f"❌ Erreur subjects utilisateur: {e}")
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "user_subjects": [],
            "subjects_count": 0
        })
        return templates.TemplateResponse("user/subjects.html", context)

@router.get("/user/subjects/ideas", response_class=HTMLResponse)
async def user_subjects_ideas(request: Request, current_user: User = Depends(get_current_normal_user)):
    """Page pour afficher toutes les idées par sujet"""
    try:
        # Récupérer les sujets assignés à l'utilisateur
        all_subjects = await Database.engine.find(Subject)
        subjects_with_ideas = []
        
        for subject in all_subjects:
            if str(current_user.id) in subject.users_ids or str(current_user.id) in subject.gestionnaires_ids:
                # Récupérer les idées du sujet
                ideas = await get_ideas_by_subject(str(subject.id))
                
                # Enrichir les idées avec des informations supplémentaires
                enriched_ideas = []
                for idea in ideas:
                    # Récupérer l'auteur de l'idée
                    author = await Database.engine.find_one(User, User.id == idea.user_id)
                    has_voted = await VoteService.has_user_voted_for_idea(str(idea.id), str(current_user.id))
                    votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
                    
                    enriched_ideas.append({
                        "idea": idea,
                        "author_name": author.username if author else "Utilisateur inconnu",
                        "is_my_idea": idea.user_id == str(current_user.id),
                        "has_voted": has_voted,
                        "votes_count": votes_count
                    })
                
                if enriched_ideas:  # Seulement inclure les sujets avec des idées
                    subjects_with_ideas.append({
                        "subject": subject,
                        "ideas": enriched_ideas,
                        "ideas_count": len(enriched_ideas),
                        "my_ideas_count": len([i for i in enriched_ideas if i["is_my_idea"]]),
                        "my_votes_count": len([i for i in enriched_ideas if i["has_voted"]])
                    })
        
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "subjects_with_ideas": subjects_with_ideas,
            "subjects_count": len(subjects_with_ideas)
        })
        return templates.TemplateResponse("user/subjects_ideas.html", context)
    except Exception as e:
        print(f"❌ Erreur subjects_ideas utilisateur: {e}")
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "subjects_with_ideas": [],
            "subjects_count": 0
        })
        return templates.TemplateResponse("user/subjects_ideas.html", context)

@router.get("/user/ideas/submit", response_class=HTMLResponse)
async def submit_idea_form(request: Request, current_user: User = Depends(get_current_normal_user)):
    """Formulaire pour soumettre une nouvelle idée"""
    try:
        # Récupérer les sujets avec émission active où l'utilisateur peut soumettre
        all_subjects = await Database.engine.find(Subject)
        available_subjects = []
        
        for subject in all_subjects:
            if (subject.emission_active and 
                (str(current_user.id) in subject.users_ids or str(current_user.id) in subject.gestionnaires_ids)):
                available_subjects.append(subject)
        
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "available_subjects": available_subjects,
            "subjects_count": len(available_subjects)
        })
        return templates.TemplateResponse("user/submit_idea.html", context)
    except Exception as e:
        print(f"❌ Erreur formulaire soumission idée: {e}")
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "available_subjects": [],
            "subjects_count": 0
        })
        return templates.TemplateResponse("user/submit_idea.html", context)

@router.get("/user/subject/{subject_id}/submit", response_class=HTMLResponse)
async def submit_idea_for_subject(subject_id: str, request: Request, current_user: User = Depends(get_current_normal_user)):
    """Formulaire pour soumettre une nouvelle idée pour un sujet spécifique"""
    try:
        # Vérifier que le sujet existe et que l'utilisateur peut y soumettre des idées
        subject = await get_subject(subject_id)
        if not subject:
            flash(request, "Sujet non trouvé.", "error")
            return RedirectResponse(url="/user/subjects", status_code=303)
        
        # Vérifier l'accès utilisateur
        if str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids:
            flash(request, "Vous n'avez pas accès à ce sujet.", "error")
            return RedirectResponse(url="/user/subjects", status_code=303)
        
        # Vérifier que l'émission est active
        if not subject.emission_active:
            flash(request, "L'émission d'idées n'est pas active pour ce sujet.", "warning")
            return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=303)
        
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "subject": subject,
            "show_sidebar": True
        })
        return templates.TemplateResponse("user/create_idea.html", context)
        
    except Exception as e:
        print(f"❌ Erreur formulaire soumission idée pour sujet: {e}")
        flash(request, "Erreur lors du chargement du formulaire.", "error")
        return RedirectResponse(url="/user/subjects", status_code=303)

@router.post("/user/subject/{subject_id}/submit")
async def submit_idea_for_subject_post(
    subject_id: str,
    request: Request,
    title: str = Form(...),
    description: str = Form(default=""),
    current_user: User = Depends(get_current_normal_user)
):
    """Traitement de la soumission d'une idée pour un sujet spécifique"""
    try:
        # Vérifier que le sujet existe et accepte les idées
        subject = await get_subject(subject_id)
        if not subject:
            flash(request, "Sujet non trouvé.", "error")
            return RedirectResponse(url="/user/subjects", status_code=303)
        
        # Vérifier l'accès utilisateur
        if str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids:
            flash(request, "Vous n'avez pas accès à ce sujet.", "error")
            return RedirectResponse(url="/user/subjects", status_code=303)
        
        # Vérifier que l'émission est active
        if not subject.emission_active:
            flash(request, "L'émission d'idées n'est pas active pour ce sujet.", "error")
            return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=303)
        
        # Créer l'idée
        idea = Idea(
            subject_id=subject_id,
            user_id=str(current_user.id),
            title=title.strip(),
            description=description.strip() if description else None
        )
        
        # Sauvegarder l'idée
        created_idea = await create_idea(idea)
        
        flash(request, f"Idée '{title}' soumise avec succès!", "success")
        return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=303)
        
    except Exception as e:
        print(f"❌ Erreur soumission idée pour sujet: {e}")
        flash(request, "Erreur lors de la soumission de l'idée.", "error")
        return RedirectResponse(url=f"/user/subject/{subject_id}/submit", status_code=303)

from fastapi.responses import HTMLResponse
from src.services.subject_service import get_subject

@router.get("/user/ideas/create", response_class=HTMLResponse)
async def create_idea_form(request: Request, subject_id: str, current_user: User = Depends(get_current_normal_user)):
    subject = await get_subject(subject_id)
    if not subject or (str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids):
        raise HTTPException(status_code=404, detail="Sujet non trouvé ou accès refusé.")
    return templates.TemplateResponse("user/create_idea.html", {
        "request": request,
        "subject": subject,
        "current_user": current_user,
        "show_sidebar": True
    })

@router.post("/user/subject/{subject_id}/ideas/vote_batch")
async def vote_batch_ideas(subject_id: str, request: Request, current_user: User = Depends(get_current_normal_user)):
    try:
        # Get the subject to check if voting is active
        subject = await get_subject(subject_id)
        if not subject:
            flash(request, "Sujet non trouvé", "error")
            return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=303)
        
        # Check if voting session is active
        if not getattr(subject, 'vote_active', False):
            flash(request, "La session de vote n'est pas active pour ce sujet", "error")
            return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=303)
        
        # Check if user has access to this subject
        if str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids:
            flash(request, "Vous n'avez pas accès à ce sujet", "error")
            return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=303)
        
        form = await request.form()
        idea_ids = form.getlist("idea_ids")
        votes_added = 0
        for idea_id in idea_ids:
            try:
                await VoteService.add_vote(idea_id, str(current_user.id))
                votes_added += 1
            except Exception as e:
                print(f"Erreur lors du vote groupé pour l'idée {idea_id}: {e}")
        
        if votes_added > 0:
            from src.utils.flash_messages import flash
            flash(request, f"{votes_added} vote(s) enregistré(s) avec succès.", "success")
        return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=303)
    except Exception as e:
        print(f"❌ Erreur lors du vote en lot: {e}")
        flash(request, "Erreur lors du vote en lot", "error")
        return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=303)

@router.post("/user/unvote/{idea_id}")
async def unvote_idea(
    idea_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Route pour retirer un vote d'une idée"""
    try:
        # Get the idea
        idea = await get_idea(idea_id)
        if not idea:
            flash(request, "Idée non trouvée", "error")
            return RedirectResponse(url="/user/vote", status_code=303)
        
        # Get the subject to check if voting is active
        subject = await get_subject(idea.subject_id)
        if not subject:
            flash(request, "Sujet non trouvé", "error")
            return RedirectResponse(url="/user/vote", status_code=303)
        
        # Check if user has access to this subject
        if str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids:
            flash(request, "Vous n'avez pas accès à ce sujet", "error")
            return RedirectResponse(url="/user/vote", status_code=303)
        
        # Remove the vote
        success = await VoteService.remove_vote(idea_id, str(current_user.id))
        
        if success:
            flash(request, "Vote retiré avec succès", "success")
            await log_activity(
                action="remove_vote_from_idea",
                subject_id=idea.subject_id,
                user=current_user,
                description=f"Vote retiré pour l'idée: {idea.title}",
                details=f"Idea ID: {idea_id}, Subject: {subject.title}",
                request=request
            )
        else:
            flash(request, "Vous n'aviez pas voté pour cette idée", "warning")
        
        return RedirectResponse(url="/user/vote", status_code=303)
        
    except Exception as e:
        print(f"❌ Erreur lors du retrait du vote: {e}")
        flash(request, f"Erreur lors du retrait du vote: {str(e)}", "error")
        return RedirectResponse(url="/user/vote", status_code=303)

@router.post("/user/update-subject-preferences")
async def update_subject_preferences(
    request: Request,
    current_user: User = Depends(get_current_normal_user)
):
    """Met à jour les préférences de sujets de l'invité"""
    try:
        form = await request.form()
        selected_subjects = form.getlist("selected_subjects")
        
        # Récupérer tous les sujets auxquels l'utilisateur a accès
        all_subjects = await Database.engine.find(Subject)
        user_subjects = []
        
        for subject in all_subjects:
            if str(current_user.id) in subject.users_ids or str(current_user.id) in subject.gestionnaires_ids:
                user_subjects.append(subject)
        
        # Mettre à jour les préférences dans la session
        user_preferences = request.session.get("subject_preferences", {})
        user_preferences[str(current_user.id)] = selected_subjects
        request.session["subject_preferences"] = user_preferences
        
        # Log de l'activité  
        await log_activity(
            action="update_subject_preferences",
            subject_id="",  # Pas de sujet spécifique
            user=current_user,
            description=f"Préférences de sujets mises à jour",
            details=f"Préférences mises à jour: {len(selected_subjects)} sujets sélectionnés",
            request=request
        )
        
        flash(request, f"Vos préférences ont été mises à jour ! {len(selected_subjects)} sujet(s) sélectionné(s).", "success")
        return RedirectResponse(url="/user/dashboard", status_code=303)
        
    except Exception as e:
        print(f"❌ Erreur mise à jour préférences: {e}")
        flash(request, "Erreur lors de la mise à jour de vos préférences.", "error")
        return RedirectResponse(url="/user/dashboard", status_code=303)

@router.get("/user/subject-selection", response_class=HTMLResponse)
async def subject_selection_page(request: Request, current_user: User = Depends(get_current_normal_user)):
    """Page dédiée à la sélection des sujets d'intérêt"""
    try:
        # Récupérer tous les sujets disponibles pour l'utilisateur
        all_subjects = await Database.engine.find(Subject)
        available_subjects = []
        
        for subject in all_subjects:
            if str(current_user.id) in subject.users_ids or str(current_user.id) in subject.gestionnaires_ids:
                # Récupérer les statistiques pour ce sujet
                ideas = await get_ideas_by_subject(str(subject.id))
                my_ideas = [idea for idea in ideas if idea.user_id == str(current_user.id)]
                
                # Compter les votes de l'utilisateur pour ce sujet
                my_votes_count = 0
                for idea in ideas:
                    if await VoteService.has_user_voted_for_idea(str(idea.id), str(current_user.id)):
                        my_votes_count += 1
                
                # Vérifier les préférences de l'utilisateur
                user_preferences = request.session.get("subject_preferences", {})
                user_subject_prefs = user_preferences.get(str(current_user.id), [])
                is_selected = str(subject.id) in user_subject_prefs if user_subject_prefs else True
                
                available_subjects.append({
                    "subject": subject,
                    "ideas_count": len(ideas),
                    "my_ideas_count": len(my_ideas),
                    "my_votes_count": my_votes_count,
                    "is_selected": is_selected,
                    "can_submit": subject.emission_active,
                    "can_vote": subject.vote_active,
                    "vote_limit": getattr(subject, 'vote_limit', 0),
                    "available_votes": max(0, getattr(subject, 'vote_limit', 0) - my_votes_count) if subject.vote_active else 0
                })
        
        from src.utils.template_helpers import add_organization_context
        context = await add_organization_context({
            "request": request,
            "current_user": current_user,
            "available_subjects": available_subjects,
            "total_subjects": len(available_subjects),
            "selected_count": len([s for s in available_subjects if s["is_selected"]]),
            "show_sidebar": True
        })
        return templates.TemplateResponse("user/subject_selection.html", context)
        
    except Exception as e:
        print(f"❌ Erreur page sélection sujets: {e}")
        flash(request, "Erreur lors du chargement de la page de sélection.", "error")
        return RedirectResponse(url="/user/dashboard", status_code=303)

@router.post("/user/ideas/submit")
async def submit_idea_post(
    request: Request,
    subject_id: str = Form(...),
    title: str = Form(...),
    description: str = Form("") ,
    current_user: User = Depends(get_current_normal_user)
):
    """Traitement du formulaire de soumission d'idée générique"""
    try:
        subject = await get_subject(subject_id)
        if not subject:
            flash(request, "Sujet non trouvé.", "error")
            return RedirectResponse(url="/user/ideas/submit", status_code=303)
        if str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids:
            flash(request, "Vous n'avez pas accès à ce sujet.", "error")
            return RedirectResponse(url="/user/ideas/submit", status_code=303)
        if not subject.emission_active:
            flash(request, "L'émission d'idées n'est pas active pour ce sujet.", "error")
            return RedirectResponse(url="/user/ideas/submit", status_code=303)
        idea = Idea(
            subject_id=subject_id,
            user_id=str(current_user.id),
            title=title.strip(),
            description=description.strip() if description else None
        )
        await create_idea(idea)
        flash(request, f"Idée '{title}' soumise avec succès!", "success")
        return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=303)
    except Exception as e:
        print(f"❌ Erreur soumission idée générique: {e}")
        flash(request, "Erreur lors de la soumission de l'idée.", "error")
        return RedirectResponse(url="/user/ideas/submit", status_code=303)
