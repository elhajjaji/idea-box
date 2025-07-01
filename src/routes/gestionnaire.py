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

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "templates"))

async def get_current_gestionnaire(request: Request, current_user: User = Depends(get_current_user)):
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
        "available_users": available_users,
        "available_users_dict": available_users_dict
    })

@router.post("/gestionnaire/subject/{subject_id}/add_user")
async def add_user_to_subject_route(subject_id: str, request: Request, user_id: str = Form(...), current_user: User = Depends(get_current_gestionnaire)):
    subject = await add_user_to_subject(subject_id, user_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible d'ajouter l'utilisateur au sujet.")
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/remove_user")
async def remove_user_from_subject_route(subject_id: str, request: Request, user_id: str = Form(...), current_user: User = Depends(get_current_gestionnaire)):
    subject = await remove_user_from_subject(subject_id, user_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de retirer l'utilisateur du sujet.")
    return RedirectResponse(url=f"/gestionnaire/subject/{subject_id}/manage_users", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/activate_emission")
async def activate_emission_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await activate_emission(subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible d'activer l'émission d'idées.")
    return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/deactivate_emission")
async def deactivate_emission_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await deactivate_emission(subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de désactiver l'émission d'idées.")
    return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/activate_vote")
async def activate_vote_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await activate_vote(subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible d'activer la session de vote.")
    return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/close_vote")
async def close_vote_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await close_vote(subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de clôturer la session de vote.")
    return RedirectResponse(url="/gestionnaire/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/gestionnaire/subject/{subject_id}/abandon_vote")
async def abandon_vote_route(subject_id: str, request: Request, current_user: User = Depends(get_current_gestionnaire)):
    subject = await abandon_vote(subject_id)
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible d'abandonner la session de vote.")
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
