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
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "current_user": current_user,
        "show_sidebar": False  # Pas de sidebar sur la page d'accueil
    })

if __name__ == "__main__":
    load_dotenv()