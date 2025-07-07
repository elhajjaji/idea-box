"""
Service pour la gestion des informations de l'organisation
"""

import os
import shutil
from typing import Optional
from datetime import datetime
from fastapi import UploadFile, HTTPException

from ..models.organization import Organization
from .database import Database


class OrganizationService:
    """Service pour gérer les informations de l'organisation"""
    
    # Répertoire pour stocker les fichiers uploadés
    UPLOAD_DIR = "static/uploads"
    ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".gif"}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    
    @classmethod
    async def get_organization(cls) -> Optional[Organization]:
        """Récupère les informations de l'organisation active"""
        return await Database.engine.find_one(
            Organization,
            {"is_active": True}
        )
    
    @classmethod
    async def get_or_create_organization(cls) -> Organization:
        """Récupère ou crée les informations par défaut de l'organisation"""
        org = await cls.get_organization()
        if not org:
            org = Organization(
                name="Idea Box",
                description="Plateforme collaborative de gestion d'idées",
                primary_color="#007bff",
                secondary_color="#6c757d",
                accent_color="#28a745",
                is_active=True,
                created_at=datetime.now().isoformat()
            )
            await Database.engine.save(org)
        return org
    
    @classmethod
    async def update_organization(cls, org_data: dict) -> Organization:
        """Met à jour les informations de l'organisation"""
        org = await cls.get_or_create_organization()
        
        # Mettre à jour les champs fournis
        for key, value in org_data.items():
            if hasattr(org, key):
                setattr(org, key, value)
        
        org.updated_at = datetime.now().isoformat()
        await Database.engine.save(org)
        return org
    
    @classmethod
    async def upload_logo(cls, file: UploadFile) -> dict:
        """Upload et sauvegarde du logo de l'organisation"""
        
        print(f"DEBUG: Début upload_logo, filename: {file.filename}")
        
        # Vérifications
        if not file.filename:
            print("DEBUG: Erreur - aucun fichier fourni")
            raise HTTPException(status_code=400, detail="Aucun fichier fourni")
        
        # Vérifier l'extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        print(f"DEBUG: Extension détectée: {file_ext}")
        if file_ext not in cls.ALLOWED_EXTENSIONS:
            print(f"DEBUG: Extension non autorisée: {file_ext}")
            raise HTTPException(
                status_code=400,
                detail=f"Extension non autorisée. Extensions acceptées: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )
        
        # Vérifier la taille
        print("DEBUG: Lecture du contenu du fichier...")
        content = await file.read()
        print(f"DEBUG: Taille du fichier: {len(content)} bytes")
        if len(content) > cls.MAX_FILE_SIZE:
            print(f"DEBUG: Fichier trop volumineux: {len(content)} > {cls.MAX_FILE_SIZE}")
            raise HTTPException(
                status_code=400,
                detail=f"Fichier trop volumineux. Taille maximale: {cls.MAX_FILE_SIZE // (1024*1024)} MB"
            )
        
        # Créer le répertoire s'il n'existe pas
        print(f"DEBUG: Création du répertoire {cls.UPLOAD_DIR}")
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        print(f"DEBUG: Répertoire créé, existe: {os.path.exists(cls.UPLOAD_DIR)}")
        
        # Générer un nom de fichier unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logo_{timestamp}{file_ext}"
        file_path = os.path.join(cls.UPLOAD_DIR, filename)
        print(f"DEBUG: Chemin complet du fichier: {file_path}")
        print(f"DEBUG: Répertoire de travail actuel: {os.getcwd()}")
        
        try:
            # Sauvegarder le fichier
            print(f"DEBUG: Écriture de {len(content)} bytes dans {file_path}")
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            print(f"DEBUG: Fichier écrit, existe maintenant: {os.path.exists(file_path)}")
            
            # Vérifier les permissions du fichier
            if os.path.exists(file_path):
                stat_info = os.stat(file_path)
                print(f"DEBUG: Taille du fichier écrit: {stat_info.st_size} bytes")
            
            # Mettre à jour l'organisation
            org = await cls.get_or_create_organization()
            
            # Supprimer l'ancien logo s'il existe
            if org.logo_path and os.path.exists(org.logo_path):
                try:
                    os.remove(org.logo_path)
                except OSError:
                    pass  # Ignorer si impossible de supprimer
            
            # Mettre à jour avec le nouveau logo
            org.logo_filename = filename
            org.logo_path = file_path
            org.updated_at = datetime.now().isoformat()
            await Database.engine.save(org)
            
            return {
                "filename": filename,
                "path": file_path,
                "size": len(content),
                "url": f"/{file_path}"
            }
            
        except Exception as e:
            # Nettoyer en cas d'erreur
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Erreur lors de l'upload: {str(e)}")
    
    @classmethod
    async def delete_logo(cls) -> bool:
        """Supprime le logo de l'organisation"""
        org = await cls.get_organization()
        if not org or not org.logo_path:
            return False
        
        # Supprimer le fichier
        if os.path.exists(org.logo_path):
            try:
                os.remove(org.logo_path)
            except OSError:
                pass
        
        # Mettre à jour l'organisation
        org.logo_filename = None
        org.logo_path = None
        org.updated_at = datetime.now().isoformat()
        await Database.engine.save(org)
        
        return True
    
    @classmethod
    async def get_logo_url(cls) -> Optional[str]:
        """Récupère l'URL du logo de l'organisation"""
        org = await cls.get_organization()
        if org and org.logo_path and os.path.exists(org.logo_path):
            # Le logo_path est "static/uploads/logo_xxx.png"
            # L'URL doit être "/static/uploads/logo_xxx.png"
            if org.logo_path.startswith('static/'):
                return f"/{org.logo_path}"
            else:
                # Au cas où le chemin ne commence pas par static/
                return f"/static/uploads/{org.logo_filename}"
        return None
    
    @classmethod
    async def validate_colors(cls, colors: dict) -> dict:
        """Valide les couleurs fournies"""
        validated = {}
        
        for key, value in colors.items():
            if key in ['primary_color', 'secondary_color', 'accent_color']:
                if not value.startswith('#') or len(value) != 7:
                    raise HTTPException(
                        status_code=400,
                        detail=f"La couleur {key} doit être au format hexadécimal (#RRGGBB)"
                    )
                try:
                    int(value[1:], 16)
                    validated[key] = value
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Format de couleur hexadécimal invalide pour {key}"
                    )
        
        return validated
