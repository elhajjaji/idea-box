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
from src.services.idea_service import create_idea, get_ideas_by_subject, add_vote_to_idea, remove_vote_from_idea, get_idea
from src.services.database import Database
from src.services.stats_service import get_user_dashboard_stats
from src.services.activity_log_service import log_activity
from src.services.metrics_service import MetricsService
from src.utils.flash_messages import flash

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "templates"))

async def get_current_normal_user(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    return current_user

async def get_vote_subjects_for_user(user_id: str):
    """Récupère les sujets avec vote actif pour un utilisateur donné (retourne des dicts enrichis)"""
    try:
        all_subjects = await Database.engine.find(Subject)
        vote_subjects = []
        from src.services.idea_service import get_ideas_by_subject
        for subject in all_subjects:
            if subject.vote_active and (user_id in subject.users_ids or user_id in subject.gestionnaires_ids):
                ideas = await get_ideas_by_subject(subject.id)
                vote_subjects.append({
                    "subject": subject,
                    "ideas": ideas,
                    "ideas_count": len(ideas),
                    "votes_count": sum(len(idea.votes) for idea in ideas)
                })
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
            if user_id in idea.votes:
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
            if user_id in idea.votes:
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
        
        user_subjects, user_stats = await get_user_dashboard_stats(current_user)
        
        # Récupérer les sujets avec vote actif
        vote_subjects = await get_vote_subjects_for_user(str(current_user.id))
        
        return templates.TemplateResponse("user/dashboard.html", {
            "request": request,
            "current_user": current_user,
            "user_subjects": user_subjects,
            "user_stats": user_stats,
            "vote_subjects": vote_subjects,
            "metrics": metrics,
            "show_sidebar": True
        })
    
    except Exception as e:
        print(f"❌ Erreur dashboard utilisateur: {e}")
        return templates.TemplateResponse("user/dashboard.html", {
            "request": request,
            "current_user": current_user,
            "user_subjects": [],
            "user_stats": {
                'subjects_count': 0,
                'user_ideas_count': 0,
                'user_votes_count': 0,
                'pending_count': 0
            },
            "vote_subjects": []
        })

@router.get("/user/vote", response_class=HTMLResponse)
async def user_vote_center(request: Request, current_user: User = Depends(get_current_normal_user)):
    """Centre de vote pour l'utilisateur"""
    try:
        # Récupérer les sujets avec vote actif
        vote_subjects = await get_vote_subjects_for_user(str(current_user.id))
        
        # Compter les votes de l'utilisateur
        user_votes_count = await get_user_votes_count(str(current_user.id))
        
        # Compter le nombre total d'idées disponibles
        total_ideas_count = sum(len(subject["ideas"]) for subject in vote_subjects)
        
        # Récupérer les votes par sujet
        user_votes_for_subject = await get_user_votes_for_subjects(str(current_user.id))
        
        # Récupérer les votes récents (optionnel)
        recent_votes = []  # Vous pouvez implémenter cette fonctionnalité plus tard
        
        return templates.TemplateResponse("user/vote.html", {
            "request": request,
            "current_user": current_user,
            "vote_subjects": vote_subjects,
            "user_votes_count": user_votes_count,
            "total_ideas_count": total_ideas_count,
            "user_votes_for_subject": user_votes_for_subject,
            "recent_votes": recent_votes,
            "show_sidebar": True
        })
    
    except Exception as e:
        print(f"❌ Erreur centre de vote: {e}")
        return templates.TemplateResponse("user/vote.html", {
            "request": request,
            "current_user": current_user,
            "vote_subjects": [],
            "user_votes_count": 0,
            "total_ideas_count": 0,
            "user_votes_for_subject": {},
            "recent_votes": [],
            "show_sidebar": True,
            "error": "Erreur lors du chargement du centre de vote"
        })

@router.get("/user/subject/{subject_id}/ideas", response_class=HTMLResponse)
async def subject_ideas(subject_id: str, request: Request, current_user: User = Depends(get_current_normal_user)):
    if isinstance(current_user, RedirectResponse):
        return current_user
    subject = await get_subject(subject_id)
    if not subject or (str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas attribué à ce sujet.")
    ideas = await get_ideas_by_subject(subject_id)
    return templates.TemplateResponse("user/subject_ideas.html", {"request": request, "subject": subject, "ideas": ideas, "current_user": current_user, "show_sidebar": True})

@router.post("/user/subject/{subject_id}/ideas/create", response_class=HTMLResponse)
async def create_new_idea(subject_id: str, request: Request, title: str = Form(...), description: Optional[str] = Form(None), current_user: User = Depends(get_current_normal_user)):
    subject = await get_subject(subject_id)
    if not subject or (str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas attribué à ce sujet.")
    
    if not subject.emission_active:
        return templates.TemplateResponse("user/subject_ideas.html", {"request": request, "subject": subject, "ideas": await get_ideas_by_subject(subject_id), "current_user": current_user, "error": "L'émission d'idées n'est pas active pour ce sujet.", "show_sidebar": True})

    idea = Idea(subject_id=subject_id, user_id=str(current_user.id), title=title, description=description)
    await create_idea(idea)
    return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/user/ideas", response_class=HTMLResponse)
async def user_ideas(request: Request, current_user: User = Depends(get_current_normal_user)):
    if isinstance(current_user, RedirectResponse):
        return current_user
    ideas = await Database.engine.find(Idea, Idea.user_id == str(current_user.id))
    from src.services.subject_service import get_subject
    ideas_with_subject = []
    for idea in ideas:
        subject = await get_subject(idea.subject_id)
        subject_name = subject.name if subject else idea.subject_id
        ideas_with_subject.append({
            "title": idea.title,
            "description": idea.description,
            "votes": idea.votes,
            "created_at": idea.created_at,
            "subject_name": subject_name
        })
    return templates.TemplateResponse("user/my_ideas.html", {"request": request, "ideas": ideas_with_subject, "current_user": current_user, "show_sidebar": True})

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
        
        # Check if user has already voted
        has_voted = str(current_user.id) in idea.votes
        
        if has_voted:
            # Remove vote
            await remove_vote_from_idea(idea_id, str(current_user.id))
            flash(request, "Vote retiré avec succès", "success")
            await log_activity(str(current_user.id), "vote_removed", f"Vote retiré pour l'idée: {idea.title}")
        else:
            # Add vote
            await add_vote_to_idea(idea_id, str(current_user.id))
            flash(request, "Vote ajouté avec succès", "success")
            await log_activity(str(current_user.id), "vote_added", f"Vote ajouté pour l'idée: {idea.title}")
        
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
        success = await remove_vote_from_idea(idea_id, current_user.id)
        
        if success:
            flash(request, "Vote retiré avec succès", "success")
            # Log the activity
            await log_activity(
                user_id=current_user.id,
                action="Remove vote from idea",
                details=f"Idea ID: {idea_id}, Subject: {subject.title}"
            )
        else:
            flash(request, "Erreur lors du retrait du vote", "error")
        
        return RedirectResponse(url=f"/user/subject/{subject.id}/ideas", status_code=status.HTTP_303_SEE_OTHER)
        
    except Exception as e:
        flash(request, f"Erreur: {str(e)}", "error")
        return RedirectResponse(url="/user/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/choose-role", response_class=HTMLResponse)
async def choose_role(request: Request, current_user: User = Depends(get_current_normal_user)):
    if isinstance(current_user, RedirectResponse):
        return current_user
    # Si un seul rôle, redirige automatiquement
    if len(current_user.roles) == 1:
        if "gestionnaire" in [r.lower() for r in current_user.roles]:
            return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url="/user/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    # Sinon, affiche le choix de rôle
    return templates.TemplateResponse("choose_role.html", {"request": request, "roles": current_user.roles})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_redirect(request: Request, current_user: User = Depends(get_current_normal_user)):
    if isinstance(current_user, RedirectResponse):
        return current_user
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
        user_has_voted = str(current_user.id) in idea.votes
        
        # Compter les votes de l'utilisateur
        user_votes_count = await get_user_votes_count(str(current_user.id))
        return templates.TemplateResponse("user/vote.html", {
            "request": request,
            "current_user": current_user,
            "idea": idea,
            "subject": subject,
            "has_voted": user_has_voted,
            "votes_count": len(idea.votes),
            "total_ideas_count": 1,
            "user_votes_count": user_votes_count,
            "show_sidebar": True
        })
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erreur lors de l'affichage de la page de vote: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur serveur.")

@router.post("/user/vote/batch")
async def batch_vote(request: Request, current_user: User = Depends(get_current_user)):
    form = await request.form()
    idea_ids = form.getlist("idea_ids")
    from src.services.idea_service import add_vote_to_idea
    success_count = 0
    for idea_id in idea_ids:
        try:
            result = await add_vote_to_idea(idea_id, str(current_user.id))
            if result:
                success_count += 1
        except Exception as e:
            print(f"Erreur lors du vote groupé pour l'idée {idea_id}: {e}")
    if success_count > 0:
        from src.utils.flash_messages import flash
        flash(request, f"{success_count} vote(s) enregistré(s) avec succès.", "success")
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
                    if str(current_user.id) in idea.votes:
                        my_votes_count += 1
                
                user_subjects.append({
                    "subject": subject,
                    "total_ideas": len(ideas),
                    "my_ideas": len(my_ideas),
                    "my_votes": my_votes_count,
                    "available_votes": max(0, subject.vote_limit - my_votes_count) if subject.vote_active else 0
                })
        
        return templates.TemplateResponse("user/subjects.html", {
            "request": request,
            "current_user": current_user,
            "user_subjects": user_subjects,
            "subjects_count": len(user_subjects),
            "show_sidebar": True
        })
    except Exception as e:
        print(f"❌ Erreur subjects utilisateur: {e}")
        return templates.TemplateResponse("user/subjects.html", {
            "request": request,
            "current_user": current_user,
            "user_subjects": [],
            "subjects_count": 0,
            "show_sidebar": True
        })

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
                    enriched_ideas.append({
                        "idea": idea,
                        "author_name": author.username if author else "Utilisateur inconnu",
                        "is_my_idea": idea.user_id == str(current_user.id),
                        "has_voted": str(current_user.id) in idea.votes,
                        "votes_count": len(idea.votes)
                    })
                
                if enriched_ideas:  # Seulement inclure les sujets avec des idées
                    subjects_with_ideas.append({
                        "subject": subject,
                        "ideas": enriched_ideas,
                        "ideas_count": len(enriched_ideas),
                        "my_ideas_count": len([i for i in enriched_ideas if i["is_my_idea"]]),
                        "my_votes_count": len([i for i in enriched_ideas if i["has_voted"]])
                    })
        
        return templates.TemplateResponse("user/subjects_ideas.html", {
            "request": request,
            "current_user": current_user,
            "subjects_with_ideas": subjects_with_ideas,
            "subjects_count": len(subjects_with_ideas),
            "show_sidebar": True
        })
    except Exception as e:
        print(f"❌ Erreur subjects_ideas utilisateur: {e}")
        return templates.TemplateResponse("user/subjects_ideas.html", {
            "request": request,
            "current_user": current_user,
            "subjects_with_ideas": [],
            "subjects_count": 0,
            "show_sidebar": True
        })

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
        
        return templates.TemplateResponse("user/submit_idea.html", {
            "request": request,
            "current_user": current_user,
            "available_subjects": available_subjects,
            "subjects_count": len(available_subjects),
            "show_sidebar": True
        })
    except Exception as e:
        print(f"❌ Erreur formulaire soumission idée: {e}")
        return templates.TemplateResponse("user/submit_idea.html", {
            "request": request,
            "current_user": current_user,
            "available_subjects": [],
            "subjects_count": 0,
            "show_sidebar": True
        })

@router.post("/user/ideas/submit")
async def submit_idea(
    request: Request,
    subject_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(default=""),
    current_user: User = Depends(get_current_normal_user)
):
    """Soumettre une nouvelle idée"""
    try:
        # Vérifier que le sujet existe et accepte les idées
        subject = await get_subject(subject_id)
        if not subject:
            from src.utils.flash_messages import flash
            flash(request, "Sujet non trouvé.", "error")
            return RedirectResponse(url="/user/ideas/submit", status_code=303)
        
        # Vérifier que l'utilisateur peut soumettre dans ce sujet
        if not (subject.emission_active and 
                (str(current_user.id) in subject.users_ids or str(current_user.id) in subject.gestionnaires_ids)):
            from src.utils.flash_messages import flash
            flash(request, "Vous ne pouvez pas soumettre d'idée dans ce sujet.", "error")
            return RedirectResponse(url="/user/ideas/submit", status_code=303)
        
        # Créer l'idée
        idea = await create_idea(
            subject_id=subject_id,
            user_id=str(current_user.id),
            title=title.strip(),
            description=description.strip()
        )
        
        # Log de l'activité
        await log_activity(
            user_id=str(current_user.id),
            subject_id=subject_id,
            action="create_idea",
            details=f"Idée '{title}' créée par {current_user.username}"
        )
        
        from src.utils.flash_messages import flash
        flash(request, f"Idée '{title}' soumise avec succès!", "success")
        return RedirectResponse(url="/user/ideas", status_code=303)
        
    except Exception as e:
        print(f"❌ Erreur soumission idée: {e}")
        from src.utils.flash_messages import flash
        flash(request, "Erreur lors de la soumission de l'idée.", "error")
        return RedirectResponse(url="/user/ideas/submit", status_code=303)
