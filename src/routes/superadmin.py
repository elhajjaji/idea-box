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
    users = await get_users()
    subjects = await Database.engine.find(Subject)
    # Create a new list of subjects with string IDs
    subjects_for_template = []
    for subject in subjects:
        subject_dict = subject.dict()
        subject_dict["id"] = str(subject.id)
        subjects_for_template.append(subject_dict)
    user_emails = {str(user.id): user.email for user in users}
    return templates.TemplateResponse("superadmin/dashboard.html", {"request": request, "users": users, "subjects": subjects_for_template, "current_user": current_user, "user_emails": user_emails, "show_sidebar": True})

@router.get("/superadmin/users/add", response_class=HTMLResponse)
async def add_user_form(request: Request, current_user: User = Depends(get_current_superadmin)):
    return templates.TemplateResponse("superadmin/add_user.html", {"request": request, "current_user": current_user, "show_sidebar": True})

@router.post("/superadmin/users/add", response_class=HTMLResponse)
async def add_user(request: Request, email: str = Form(...), nom: str = Form(...), prenom: str = Form(...), password: str = Form(...), current_user: User = Depends(get_current_superadmin)):
    existing_user = await Database.engine.find_one(User, User.email == email)
    if existing_user:
        return templates.TemplateResponse("superadmin/add_user.html", {"request": request, "error": "Cet email est déjà enregistré."})

    hashed_password = get_password_hash(password)
    user = User(email=email, nom=nom, prenom=prenom, pwd=hashed_password)
    await create_user(user)
    return templates.TemplateResponse("superadmin/add_user.html", {"request": request, "message": "Utilisateur ajouté avec succès !"})

@router.get("/superadmin/users/import", response_class=HTMLResponse)
async def import_users_form(request: Request, current_user: User = Depends(get_current_superadmin)):
    return templates.TemplateResponse("superadmin/import_users.html", {"request": request})

@router.post("/superadmin/users/import", response_class=HTMLResponse)
async def import_users(request: Request, file: UploadFile = File(...), current_user: User = Depends(get_current_superadmin)):
    if not file.filename.endswith(".csv"):
        return templates.TemplateResponse("superadmin/import_users.html", {"request": request, "error": "Veuillez télécharger un fichier CSV."})

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

    return templates.TemplateResponse("superadmin/import_users.html", {"request": request, "message": f"{imported_count} utilisateurs importés avec succès.", "errors": errors})

@router.get("/superadmin/subjects/create", response_class=HTMLResponse)
async def create_subject_form(request: Request, current_user: User = Depends(get_current_superadmin)):
    users = await get_users()
    return templates.TemplateResponse("superadmin/create_subject.html", {"request": request, "users": users})

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
            result = await add_role_to_user(str(user.id), "gestionnaire")
            if not result:
                print(f"[ERREUR] Impossible d'ajouter le rôle gestionnaire à l'utilisateur {user.email} (id={user.id})")
        else:
            print(f"[ERREUR] Utilisateur non trouvé pour l'id {user_id}")

    return RedirectResponse(url="/auth/logout", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/superadmin/subjects/{subject_id}/edit", response_class=HTMLResponse)
async def edit_subject_form(subject_id: str, request: Request, current_user: User = Depends(get_current_superadmin)):
    try:
        subject = await Database.engine.find_one(Subject, Subject.id == ObjectId(subject_id))
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sujet non trouvé")
        
        users = await get_users()
        return templates.TemplateResponse("superadmin/edit_subject.html", {"request": request, "subject": subject, "users": users, "current_user": current_user, "show_sidebar": True})
    except Exception as e:
        return templates.TemplateResponse("superadmin/edit_subject.html", {"request": request, "error": f"Erreur: {e}", "current_user": current_user, "show_sidebar": True})

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

        return templates.TemplateResponse("superadmin/edit_subject.html", {
            "request": request,
            "subject": subject,
            "users": users,
            "message": "Sujet modifié avec succès !",
            "current_user": current_user,
            "show_sidebar": True
        })
    except Exception as e:
        users = await get_users()
        return templates.TemplateResponse("superadmin/edit_subject.html", {"request": request, "error": f"Erreur: {e}", "users": users, "current_user": current_user, "show_sidebar": True})

@router.get("/superadmin/users", response_class=HTMLResponse)
async def superadmin_users(request: Request, current_user: User = Depends(get_current_superadmin)):
    users = await get_users()
    return templates.TemplateResponse("superadmin/users.html", {"request": request, "users": users, "current_user": current_user, "show_sidebar": True})

@router.get("/superadmin/subjects", response_class=HTMLResponse)
async def superadmin_subjects(request: Request, current_user: User = Depends(get_current_superadmin)):
    subjects = await Database.engine.find(Subject)
    # Create a new list of subjects with string IDs
    subjects_for_template = []
    for subject in subjects:
        subject_dict = subject.dict()
        subject_dict["id"] = str(subject.id)
        subjects_for_template.append(subject_dict)
    users = await get_users()
    user_emails = {str(user.id): user.email for user in users}
    return templates.TemplateResponse("superadmin/subjects.html", {"request": request, "subjects": subjects_for_template, "current_user": current_user, "user_emails": user_emails, "show_sidebar": True})

@router.get("/superadmin/settings", response_class=HTMLResponse)
async def superadmin_settings(request: Request, current_user: User = Depends(get_current_superadmin)):
    return templates.TemplateResponse("superadmin/settings.html", {"request": request, "current_user": current_user, "show_sidebar": True})
