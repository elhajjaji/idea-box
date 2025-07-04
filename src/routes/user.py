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
from src.services.stats_service import get_user_dashboard_stats

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "templates"))

async def get_current_normal_user(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    return current_user

@router.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request, current_user: User = Depends(get_current_normal_user)):
    try:
        user_subjects, user_stats = await get_user_dashboard_stats(current_user)
        
        return templates.TemplateResponse("user/dashboard.html", {
            "request": request,
            "current_user": current_user,
            "user_subjects": user_subjects,
            "user_stats": user_stats,
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
            }
        })

@router.get("/user/subject/{subject_id}/ideas", response_class=HTMLResponse)
async def subject_ideas(subject_id: str, request: Request, current_user: User = Depends(get_current_normal_user)):
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
        return templates.TemplateResponse("user/subject_ideas.html", {"request": request, "subject": subject, "ideas": await get_ideas_by_subject(subject_id), "current_user": current_user, "error": "L'émission d'idées n'est pas active pour ce sujet."})

    idea = Idea(subject_id=subject_id, user_id=str(current_user.id), title=title, description=description)
    await create_idea(idea)
    return RedirectResponse(url=f"/user/subject/{subject_id}/ideas", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/user/ideas", response_class=HTMLResponse)
async def user_ideas(request: Request, current_user: User = Depends(get_current_normal_user)):
    if isinstance(current_user, RedirectResponse):
        return current_user
    ideas = await Database.engine.find(Idea, Idea.user_id == str(current_user.id))
    return templates.TemplateResponse("user/my_ideas.html", {"request": request, "ideas": ideas, "current_user": current_user, "show_sidebar": True})

@router.post("/user/idea/{idea_id}/vote")
async def vote_for_idea(idea_id: str, request: Request, current_user: User = Depends(get_current_normal_user)):
    idea = await Database.engine.find_one(Idea, Idea.id == idea_id)
    if not idea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idée non trouvée.")
    
    subject = await get_subject(idea.subject_id)
    if not subject or (str(current_user.id) not in subject.users_ids and str(current_user.id) not in subject.gestionnaires_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'êtes pas autorisé à voter pour cette idée.")

    if not subject.vote_active:
        return templates.TemplateResponse("user/subject_ideas.html", {"request": request, "subject": subject, "ideas": await get_ideas_by_subject(subject.id), "current_user": current_user, "error": "La session de vote n'est pas active pour ce sujet."})

    # Check vote limit
    user_votes_count = 0
    for existing_idea in await get_ideas_by_subject(subject.id):
        if str(current_user.id) in existing_idea.votes:
            user_votes_count += 1
    
    if user_votes_count >= subject.vote_limit and str(current_user.id) not in idea.votes:
        return templates.TemplateResponse("user/subject_ideas.html", {"request": request, "subject": subject, "ideas": await get_ideas_by_subject(subject.id), "current_user": current_user, "error": f"Vous avez atteint votre limite de {subject.vote_limit} votes pour ce sujet."})

    if str(current_user.id) in idea.votes:
        await remove_vote_from_idea(idea_id, str(current_user.id))
    else:
        await add_vote_to_idea(idea_id, str(current_user.id))
    
    return RedirectResponse(url=f"/user/subject/{subject.id}/ideas", status_code=status.HTTP_303_SEE_OTHER)

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
