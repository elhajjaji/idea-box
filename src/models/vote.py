from datetime import datetime
from odmantic import Model
from pydantic import ConfigDict


class Vote(Model):
    """Modèle pour les votes individuels"""
    __collection__ = "votes"
    
    votation_id: str
    idea_id: str
    user_id: str
    created_at: datetime
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "votation_id": "60d5ecf0f3e4c1a2b3c4d5f0",
                "idea_id": "60d5ecf0f3e4c1a2b3c4d5ec",
                "user_id": "60d5ecf0f3e4c1a2b3c4d5e8",
                "created_at": "2025-07-09T14:30:00Z"
            }
        }
    )