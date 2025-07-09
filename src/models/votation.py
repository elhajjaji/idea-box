from typing import List, Optional
from datetime import datetime
from odmantic import Model
from pydantic import ConfigDict


class Votation(Model):
    """Modèle pour les sessions de vote"""
    __collection__ = "votations"
    
    subject_id: str
    votation_name: str
    ideas_list: List[str]
    vote_limit: int
    is_activated: bool = False
    allow_multiple_active: bool = False
    created_at: datetime
    activated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subject_id": "60d5ecf0f3e4c1a2b3c4d5e9",
                "votation_name": "Vote final - Décembre 2024",
                "ideas_list": ["60d5ecf0f3e4c1a2b3c4d5ec", "60d5ecf0f3e4c1a2b3c4d5ed"],
                "vote_limit": 3,
                "is_activated": False,
                "allow_multiple_active": False,
                "created_at": "2025-07-09T10:00:00Z",
                "activated_at": None,
                "closed_at": None
            }
        }
    )