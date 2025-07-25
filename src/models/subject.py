from pydantic import ConfigDict
from typing import List, Optional, TYPE_CHECKING
from odmantic import Model, Field

if TYPE_CHECKING:
    from src.models.idea import Idea

class Subject(Model):
    __collection__ = "subjects"
    name: str
    description: Optional[str] = None
    superadmin_id: str # ID of the superadmin who created this subject
    gestionnaires_ids: List[str] = [] # List of user IDs who are managers for this subject
    users_ids: List[str] = [] # List of user IDs assigned to this subject
    emission_active: bool = False
    
    # Attributs pour le système de vote
    vote_active: bool = False
    vote_limit: int = 5  # Nombre maximum de votes par utilisateur
    show_votes_during_vote: bool = False  # Afficher les votes en temps réel pendant la session
    
    # Attributs pour les statistiques (non stockés en DB)
    ideas_count: Optional[int] = 0
    votes_count: Optional[int] = 0
    user_ideas_count: Optional[int] = 0
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Amélioration du processus de recrutement",
                "description": "Idées pour optimiser notre processus de recrutement interne.",
                "superadmin_id": "60d5ecf0f3e4c1a2b3c4d5e6",
                "gestionnaires_ids": ["60d5ecf0f3e4c1a2b3c4d5e7"],
                "users_ids": [],
                "emission_active": False,
                "vote_active": False,
                "vote_limit": 5,
                "show_votes_during_vote": False
            }
        }
    )
