from pydantic import ConfigDict
from typing import List, Optional
from datetime import datetime
from odmantic import Model, Field

class Idea(Model):
    __collection__ = "ideas"
    subject_id: str
    user_id: str
    title: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    votes: List[str] = [] # List of user IDs who voted for this idea

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subject_id": "60d5ecf0f3e4c1a2b3c4d5e8",
                "user_id": "60d5ecf0f3e4c1a2b3c4d5e9",
                "title": "Mettre en place un système de covoiturage",
                "description": "Proposer une plateforme interne pour faciliter le covoiturage entre employés."
            }
        }
    )
