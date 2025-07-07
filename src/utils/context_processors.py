from fastapi import Request, Depends
from src.services.organization_service import OrganizationService
from src.services.auth_service import get_current_user_optional
from src.models.user import User

async def get_global_context(request: Request, user: User = Depends(get_current_user_optional)):
    """
    Injecte des variables globales dans le contexte des templates Jinja2.
    """
    try:
        organization = await OrganizationService.get_or_create_organization()
        logo_url = await OrganizationService.get_logo_url()
    except Exception as e:
        # En cas d'erreur (ex: DB pas prête), fournir des valeurs par défaut
        print(f"AVERTISSEMENT: Impossible de charger le contexte de l'organisation: {e}")
        # Créer un objet organisation par défaut
        class DefaultOrganization:
            def __init__(self):
                self.name = 'Idea Box'
                self.description = 'Plateforme de gestion d\'idées'
                self.primary_color = '#4e73df'
                self.secondary_color = '#5a5c69'
                self.accent_color = '#1cc88a'
                self.website = None
                self.email = None
                self.phone = None
                self.address = None
        
        organization = DefaultOrganization()
        logo_url = None

    return {
        "request": request,
        "organization": organization,
        "logo_url": logo_url,
        "current_user": user,
    }
