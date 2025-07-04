from pydantic import ConfigDict
from typing import Optional
from datetime import datetime
from odmantic import Model, Field

class ActivityLog(Model):
    __collection__ = "activity_logs"
    
    # Informations de base
    action: str  # "activate_emission", "deactivate_emission", "activate_vote", "close_vote", etc.
    subject_id: str  # ID du sujet concerné
    user_id: str  # ID de l'utilisateur qui fait l'action (gestionnaire ou superadmin)
    user_email: str  # Email de l'utilisateur pour faciliter l'affichage
    user_name: str  # Nom complet de l'utilisateur
    
    # Détails de l'action
    description: str  # Description lisible de l'action
    details: Optional[str] = None  # Détails supplémentaires si nécessaire
    
    # Métadonnées
    timestamp: datetime = Field(default_factory=datetime.now)
    ip_address: Optional[str] = None  # Adresse IP de l'utilisateur
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action": "activate_emission",
                "subject_id": "60d5ecf0f3e4c1a2b3c4d5e8",
                "user_id": "60d5ecf0f3e4c1a2b3c4d5e9",
                "user_email": "gestionnaire@example.com",
                "user_name": "Jean Dupont",
                "description": "Activation de l'émission d'idées pour le sujet 'Amélioration des processus'",
                "details": "État précédent: Inactive",
                "timestamp": "2025-07-04T12:30:00Z",
                "ip_address": "192.168.1.1"
            }
        }
    )