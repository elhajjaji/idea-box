"""
Modèle pour les informations de l'organisation
"""

from typing import Optional
from odmantic import Model, Field
from pydantic import validator


class Organization(Model):
    """Modèle représentant les informations de l'organisation"""
    
    # Informations de base
    name: str = Field(..., min_length=1, max_length=100, description="Nom de l'organisation")
    description: Optional[str] = Field(None, max_length=500, description="Description ou slogan de l'organisation")
    
    # Logo et branding
    logo_filename: Optional[str] = Field(None, description="Nom du fichier logo")
    logo_path: Optional[str] = Field(None, description="Chemin vers le fichier logo")
    
    # Couleurs de la charte graphique
    primary_color: str = Field("#007bff", description="Couleur principale (hex)")
    secondary_color: str = Field("#6c757d", description="Couleur secondaire (hex)")
    accent_color: str = Field("#28a745", description="Couleur d'accent (hex)")
    
    # Informations de contact (optionnelles)
    website: Optional[str] = Field(None, max_length=200, description="Site web de l'organisation")
    email: Optional[str] = Field(None, max_length=100, description="Email de contact")
    phone: Optional[str] = Field(None, max_length=20, description="Téléphone de contact")
    address: Optional[str] = Field(None, max_length=300, description="Adresse de l'organisation")
    
    # Métadonnées
    is_active: bool = Field(True, description="Configuration active")
    created_at: Optional[str] = Field(None, description="Date de création")
    updated_at: Optional[str] = Field(None, description="Date de dernière mise à jour")
    
    @validator('primary_color', 'secondary_color', 'accent_color')
    def validate_hex_color(cls, v):
        """Valide que la couleur est au format hexadécimal"""
        if not v.startswith('#') or len(v) != 7:
            raise ValueError('La couleur doit être au format hexadécimal (#RRGGBB)')
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError('Format de couleur hexadécimal invalide')
        return v
    
    @validator('website')
    def validate_website(cls, v):
        """Valide l'URL du site web"""
        if v and not (v.startswith('http://') or v.startswith('https://')):
            return f'https://{v}'
        return v
