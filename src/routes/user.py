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
from src.services.idea_service import create_idea, get_ideas_by_subject, add_vote_to_idea, remove_vote_from_idea
from src.services.database import Database

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "templates"))

async def get_current_normal_user(current_user: User = Depends(get_current_user)):
    # All authenticated users are considered 'normal' users unless they have specific roles
    return current_user

@router.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request, current_user: User = Depends(get_current_normal_user)):
    try:
        # Récupérer les sujets de l'utilisateur
        user_subjects = await Database.engine.find(Subject, {
            "$or": [
                {"users_ids": {"$in": [str(current_user.id)]}},
                {"gestionnaires_ids": {"$in": [str(current_user.id)]}}
            ]
        })
        
        # Calculer les statistiques pour chaque sujet
        subjects_stats = {}
        for subject in user_subjects:
            # Récupérer les idées du sujet
            subject_ideas = await get_ideas_by_subject(str(subject.id))
            
            # Calculer les statistiques pour ce sujet
            total_votes = sum(len(idea.votes) for idea in subject_ideas)
            user_ideas = [idea for idea in subject_ideas if idea.user_id == str(current_user.id)]
            
            subjects_stats[str(subject.id)] = {
                'ideas_count': len(subject_ideas),
                'votes_count': total_votes,
                'user_ideas_count': len(user_ideas)
            }
        
        # Statistiques globales utilisateur
        user_stats = {
            'subjects_count': len(user_subjects),
            'user_ideas_count': sum(stats['user_ideas_count'] for stats in subjects_stats.values()),
            'user_votes_count': 0,  # À implémenter selon vos besoins
            'pending_count': 0  # À implémenter selon vos besoins
        }
        
        return templates.TemplateResponse("user/dashboard.html", {
            "request": request,
            "current_user": current_user,
            "user_subjects": user_subjects,
            "subjects_stats": subjects_stats,
            "user_stats": user_stats
        })
    
    except Exception as e:
        print(f"❌ Erreur dashboard utilisateur: {e}")
        return templates.TemplateResponse("user/dashboard.html", {
            "request": request,
            "current_user": current_user,
            "user_subjects": [],
            "subjects_stats": {},
            "user_stats": {
                'subjects_count': 0,
                'user_ideas_count': 0,
                'user_votes_count': 0,
                'pending_count': 0
            }
        })

@router.get("/user/subject/{subject_id}/ideas", response_class=HTMLResponse)
async def subject_ideas(subject_id: str, request: Request, current_user: User = Depends(get_current_normal_user)):
    subject = await get_subject(subject_id)
    if not subject or (str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas attribué à ce sujet.")
    
    ideas = await get_ideas_by_subject(subject_id)
    
    return templates.TemplateResponse("user/subject_ideas.html", {"request": request, "subject": subject, "ideas": ideas, "current_user_id": str(current_user.id)})

@router.post("/user/subject/{subject_id}/ideas/create", response_class=HTMLResponse)
async def create_new_idea(subject_id: str, request: Request, title: str = Form(...), description: Optional[str] = Form(None), current_user: User = Depends(get_current_normal_user)):
    subject = await get_subject(subject_id)
    if not subject or (str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé ou vous n'êtes pas attribué à ce sujet.")
    
    if not subject.emission_active:
        return templates.TemplateResponse("user/subject_ideas.html", {"request": request, "subject": subject, "ideas": await get_ideas_by_subject(subject_id), "current_user_id": str(current_user.id), "error": "L'émission d'idées n'est pas active pour ce sujet."})

    idea = Idea(subject_id=subject_id, user_id=str(current_user.id), title=title, description=description)
    await create_idea(idea)
    return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/user/idea/{idea_id}/vote")
async def vote_for_idea(idea_id: str, request: Request, current_user: User = Depends(get_current_normal_user)):
    idea = await Database.engine.find_one(Idea, Idea.id == idea_id)
    if not idea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idée non trouvée.")
    
    subject = await get_subject(idea.subject_id)
    if not subject or (str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'êtes pas autorisé à voter pour cette idée.")

    if not subject.vote_active:
        return templates.TemplateResponse("user/subject_ideas.html", {"request": request, "subject": subject, "ideas": await get_ideas_by_subject(subject.id), "current_user_id": str(current_user.id), "error": "La session de vote n'est pas active pour ce sujet."})

    # Check vote limit
    user_votes_count = 0
    for existing_idea in await get_ideas_by_subject(subject.id):
        if str(current_user.id) in existing_idea.votes:
            user_votes_count += 1
    
    if user_votes_count >= subject.vote_limit and str(current_user.id) not in idea.votes:
        return templates.TemplateResponse("user/subject_ideas.html", {"request": request, "subject": subject, "ideas": await get_ideas_by_subject(subject.id), "current_user_id": str(current_user.id), "error": f"Vous avez atteint votre limite de {subject.vote_limit} votes pour ce sujet."})

    if str(current_user.id) in idea.votes:
        await remove_vote_from_idea(idea_id, str(current_user.id))
    else:
        await add_vote_to_idea(idea_id, str(current_user.id))
    
    return RedirectResponse(url=f"/user/subject/{subject.id}/ideas", status_code=status.HTTP_303_SEE_OTHER)
