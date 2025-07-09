import os
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from src.services.database import Database
from src.services.init_service import init_superadmin
from src.services.auth_service import get_current_user_optional
from src.routes import auth, superadmin, gestionnaire, user, organization
from src.routes import gestionnaire_advanced
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
from src.services.stats_service import get_user_dashboard_stats
from src.services.idea_service import get_ideas_by_subject
from src.models.subject import Subject


load_dotenv()

app = FastAPI()

# Add Session Middleware
app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "super-secret-key-for-session")
)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "templates"))

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_db_client():
    await Database.connect()
    # Initialiser le SuperAdmin au démarrage
    await init_superadmin()

@app.on_event("shutdown")
async def shutdown_db_client():
    await Database.close()

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(superadmin.router)
app.include_router(gestionnaire.router)
app.include_router(gestionnaire_advanced.router)  # Nouvelles routes gestionnaire
app.include_router(organization.router, prefix="/superadmin")  # Routes organisation
app.include_router(user.router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, current_user=Depends(get_current_user_optional)):
    from src.utils.template_helpers import add_organization_context
    
    # Si l'utilisateur n'est pas connecté, rediriger vers la page de connexion
    if not current_user:
        # Au lieu de rediriger, afficher la page d'accueil avec les infos de l'organisation
        context = {"request": request, "show_sidebar": True}
        context = await add_organization_context(context)
        return templates.TemplateResponse("index.html", context)
    
    # Pour les utilisateurs avec plusieurs rôles, afficher le choix
    if len(current_user.roles) > 1:
        return RedirectResponse(url="/choose-role", status_code=303)
    
    # Redirection automatique pour un seul rôle
    role = current_user.roles[0].lower()
    if role == "superadmin":
        return RedirectResponse(url="/superadmin/dashboard", status_code=303)
    elif role == "gestionnaire":
        return RedirectResponse(url="/gestionnaire/dashboard", status_code=303)
    else:
        return RedirectResponse(url="/user/dashboard", status_code=303)

if __name__ == "__main__":
    load_dotenv()