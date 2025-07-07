import os
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from src.services.database import Database
from src.services.init_service import init_superadmin
from src.services.auth_service import get_current_user_optional
from src.routes import auth, superadmin, gestionnaire, user
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
app.include_router(user.router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, current_user=Depends(get_current_user_optional)):
    metrics = None
    latest_subjects = []
    if current_user:
        # Récupérer les sujets accessibles (user ou gestionnaire)
        user_subjects, user_stats = await get_user_dashboard_stats(current_user)
        # Trier par date de création si dispo, sinon par nom
        latest_subjects = sorted(user_subjects, key=lambda s: getattr(s, 'created_at', None) or s.name, reverse=True)[:3]
        # Calculer les métriques globales
        total_ideas = sum(getattr(s, 'ideas_count', 0) for s in user_subjects)
        total_votes = sum(getattr(s, 'votes_count', 0) for s in user_subjects)
        metrics = {
            'subjects_count': len(user_subjects),
            'ideas_count': total_ideas,
            'votes_count': total_votes,
            'latest_subjects': latest_subjects
        }
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "current_user": current_user,
        "metrics": metrics,
        "show_sidebar": False  # Pas de sidebar sur la page d'accueil
    })

if __name__ == "__main__":
    load_dotenv()