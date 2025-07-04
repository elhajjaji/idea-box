from pydantic import EmailStr, ConfigDict
from typing import Optional, List
from odmantic import Model

class User(Model):
    __collection__ = "user"
    email: EmailStr
    nom: str
    prenom: str
    pwd: str  # Store as hashed string, not SecretStr for MongoDB compatibility
    roles: List[str] = ["user"] # e.g., ["user"], ["superadmin"], ["gestionnaire"]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john.doe@example.com",
                "nom": "Doe",
                "prenom": "John",
                "pwd": "hashedpassword",
                "roles": ["user"]
            }
        }
    )
