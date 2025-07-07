"""
Utilitaires pour enrichir le contexte des templates avec les informations de l'organisation
"""

from src.services.organization_service import OrganizationService

async def add_organization_context(context: dict) -> dict:
    """
    Ajoute les informations de l'organisation et les paramètres de contexte standard au template
    """
    try:
        organization = await OrganizationService.get_or_create_organization()
        logo_url = await OrganizationService.get_logo_url()
    except Exception:
        # Valeurs par défaut si problème avec la base de données
        organization = None
        logo_url = None
    
    # Ajouter les informations d'organisation
    context_updates = {
        "organization": organization,
        "logo_url": logo_url
    }
    
    # Si show_sidebar n'est pas déjà défini, le définir à True par défaut
    if "show_sidebar" not in context:
        context_updates["show_sidebar"] = True
    
    context.update(context_updates)
    
    return context
