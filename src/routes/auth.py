from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from typing import Optional
from src.models.user import User
from src.services.auth_service import (create_access_token, get_password_hash, verify_password, get_user_by_email, get_current_user, SECRET_KEY, ALGORITHM)
from src.services.database import Database
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "templates"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register", response_class=HTMLResponse)
async def register_user(request: Request, email: str = Form(...), nom: str = Form(...), prenom: str = Form(...), password: str = Form(...)):
    existing_user = await get_user_by_email(email)
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Cet email est déjà enregistré."})

    hashed_password = get_password_hash(password)
    user = User(email=email, nom=nom, prenom=prenom, pwd=hashed_password)
    await Database.engine.save(user)
    return templates.TemplateResponse("register.html", {"request": request, "message": "Inscription réussie ! Vous pouvez maintenant vous connecter."})

@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.pwd):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email, "roles": user.roles})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_class=HTMLResponse)
async def login_user(request: Request, username: str = Form(...), password: str = Form(...)):
    user = await get_user_by_email(username)
    if not user or not verify_password(password, user.pwd):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Identifiants incorrects"})
    
    # Créer un token d'accès
    access_token = create_access_token(data={"sub": user.email, "roles": user.roles})
    
    # Rediriger vers le tableau de bord approprié selon le rôle
    if "superadmin" in user.roles:
        response = RedirectResponse(url="/superadmin/dashboard", status_code=303)
    elif "gestionnaire" in user.roles:
        response = RedirectResponse(url="/gestionnaire/dashboard", status_code=303)
    else:
        response = RedirectResponse(url="/user/dashboard", status_code=303)
    
    # Stocker le token dans la session
    response.set_cookie("access_token", access_token, httponly=True, secure=False, samesite="lax")
    return response

@router.get("/logout")
async def logout_user():
    """Route de déconnexion - supprime le cookie d'authentification"""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, current_user: User = Depends(get_current_user)):
    """Page de profil utilisateur"""
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "current_user": current_user,
        "show_sidebar": True
    })
