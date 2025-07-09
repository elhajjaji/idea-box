from odmantic import Model
from pydantic import ConfigDict


class SubjectState(Model):
    """Modèle pour l'état d'émission d'idées d'un sujet"""
    __collection__ = "subject_states"
    
    subject_id: str
    is_activated: bool
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subject_id": "60d5ecf0f3e4c1a2b3c4d5e9",
                "is_activated": True
            }
        }
    )