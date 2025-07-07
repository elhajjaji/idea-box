"""
Routes pour la gestion des paramètres de l'organisation (Super Admin uniquement)
"""

from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from ..models.user import User
from ..services.auth_service import get_current_user
from ..services.organization_service import OrganizationService
from ..utils.flash_messages import flash, get_flashed_messages

router = APIRouter()
templates = Jinja2Templates(directory="src/templates")

# Fonction de dépendance pour vérifier les droits superadmin
async def get_current_superadmin(request: Request, current_user: User = Depends(get_current_user)):
    """Vérifie que l'utilisateur connecté est un superadmin"""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, detail="Not authenticated", headers={"Location": "/auth/login"})
    if "superadmin" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'avez pas les droits de superadmin")
    return current_user


@router.get("/organization", response_class=HTMLResponse)
async def organization_settings_page(request: Request, current_user: User = Depends(get_current_superadmin)):
    """Page de configuration de l'organisation"""
    try:
        organization = await OrganizationService.get_or_create_organization()
        logo_url = await OrganizationService.get_logo_url()
        
        return templates.TemplateResponse("superadmin/organization.html", {
            "request": request,
            "current_user": current_user,
            "organization": organization,
            "logo_url": logo_url,
            "flash_messages": get_flashed_messages(request),
            "show_sidebar": True
        })
    except Exception as e:
        flash(request, f"Erreur lors du chargement des paramètres: {str(e)}", "error")
        return RedirectResponse(url="/superadmin/dashboard", status_code=303)


@router.post("/organization/update")
async def update_organization(
    request: Request,
    current_user: User = Depends(get_current_superadmin),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    primary_color: str = Form("#007bff"),
    secondary_color: str = Form("#6c757d"),
    accent_color: str = Form("#28a745"),
    website: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None)
):
    """Met à jour les informations de l'organisation"""
    try:
        # Valider les couleurs
        colors = {
            "primary_color": primary_color,
            "secondary_color": secondary_color,
            "accent_color": accent_color
        }
        await OrganizationService.validate_colors(colors)
        
        # Préparer les données
        org_data = {
            "name": name.strip(),
            "description": description.strip() if description else None,
            "primary_color": primary_color,
            "secondary_color": secondary_color,
            "accent_color": accent_color,
            "website": website.strip() if website else None,
            "email": email.strip() if email else None,
            "phone": phone.strip() if phone else None,
            "address": address.strip() if address else None
        }
        
        # Mettre à jour
        await OrganizationService.update_organization(org_data)
        flash(request, "Informations de l'organisation mises à jour avec succès", "success")
        
    except HTTPException as e:
        flash(request, f"Erreur de validation: {e.detail}", "error")
    except Exception as e:
        flash(request, f"Erreur lors de la mise à jour: {str(e)}", "error")
    
    return RedirectResponse(url="/superadmin/organization", status_code=303)


@router.post("/organization/upload-logo")
async def upload_logo(request: Request, current_user: User = Depends(get_current_superadmin)):
    """Upload du logo de l'organisation"""
    try:
        # Récupérer le formulaire
        form = await request.form()
        logo = form.get("logo")
        
        if not logo:
            flash(request, "Aucun fichier sélectionné", "error")
            return RedirectResponse(url="/superadmin/organization", status_code=303)
            
        if not hasattr(logo, 'filename'):
            flash(request, "Le fichier fourni n'est pas valide", "error")
            return RedirectResponse(url="/superadmin/organization", status_code=303)
        
        # Validation du nom de fichier
        if not logo.filename:
            flash(request, "Nom de fichier manquant", "error")
            return RedirectResponse(url="/superadmin/organization", status_code=303)
        
        # Validation de l'extension
        allowed_extensions = ['.png', '.jpg', '.jpeg']
        file_extension = logo.filename.lower().split('.')[-1]
        if '.' + file_extension not in allowed_extensions:
            flash(request, "Type de fichier non autorisé. Seuls les fichiers PNG et JPEG sont acceptés", "error")
            return RedirectResponse(url="/superadmin/organization", status_code=303)
        
        # Validation de la taille du fichier (max 5MB)
        file_content = await logo.read()
        file_size = len(file_content)
        max_size = 5 * 1024 * 1024  # 5MB
        if file_size > max_size:
            flash(request, "Le fichier est trop volumineux (maximum 5MB)", "error")
            return RedirectResponse(url="/superadmin/organization", status_code=303)
        
        # Remettre le curseur au début du fichier
        await logo.seek(0)
        
        # Appeler le service d'upload
        result = await OrganizationService.upload_logo(logo)
        flash(request, "Logo uploadé avec succès", "success")
        
    except HTTPException as e:
        flash(request, f"Erreur d'upload: {e.detail}", "error")
    except Exception as e:
        flash(request, f"Erreur lors de l'upload: {str(e)}", "error")
    
    return RedirectResponse(url="/superadmin/organization", status_code=303)


@router.post("/organization/delete-logo")
async def delete_logo(request: Request, current_user: User = Depends(get_current_superadmin)):
    """Supprime le logo de l'organisation"""
    try:
        success = await OrganizationService.delete_logo()
        if success:
            flash(request, "Logo supprimé avec succès", "success")
        else:
            flash(request, "Aucun logo à supprimer", "info")
            
    except Exception as e:
        flash(request, f"Erreur lors de la suppression: {str(e)}", "error")
    
    return RedirectResponse(url="/superadmin/organization", status_code=303)


@router.get("/organization/preview")
async def preview_organization(request: Request, current_user: User = Depends(get_current_superadmin)):
    """Prévisualisation des paramètres de l'organisation"""
    try:
        organization = await OrganizationService.get_or_create_organization()
        logo_url = await OrganizationService.get_logo_url()
        
        return templates.TemplateResponse("superadmin/organization_preview.html", {
            "request": request,
            "current_user": current_user,
            "organization": organization,
            "logo_url": logo_url,
            "show_sidebar": True
        })
        
    except Exception as e:
        flash(request, f"Erreur lors de la prévisualisation: {str(e)}", "error")
        return RedirectResponse(url="/superadmin/organization", status_code=303)


