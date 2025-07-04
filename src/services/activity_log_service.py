from typing import List, Optional
from src.models.activity_log import ActivityLog
from src.models.user import User
from src.services.database import Database
from fastapi import Request

async def log_activity(
    action: str,
    subject_id: str,
    user: User,
    description: str,
    details: Optional[str] = None,
    request: Optional[Request] = None
) -> ActivityLog:
    """
    Enregistre une activité dans les logs
    """
    # Récupérer l'adresse IP si la requête est fournie
    ip_address = None
    if request:
        ip_address = request.client.host if request.client else None
    
    activity = ActivityLog(
        action=action,
        subject_id=subject_id,
        user_id=str(user.id),
        user_email=user.email,
        user_name=f"{user.prenom} {user.nom}",
        description=description,
        details=details,
        ip_address=ip_address
    )
    
    await Database.engine.save(activity)
    return activity

async def get_subject_activities(subject_id: str, limit: int = 50) -> List[ActivityLog]:
    """
    Récupère l'historique des activités pour un sujet donné
    """
    activities = await Database.engine.find(
        ActivityLog,
        ActivityLog.subject_id == subject_id,
        sort=ActivityLog.timestamp.desc(),  # Plus récent en premier
        limit=limit
    )
    return activities

async def get_user_activities(user_id: str, limit: int = 50) -> List[ActivityLog]:
    """
    Récupère l'historique des activités pour un utilisateur donné
    """
    activities = await Database.engine.find(
        ActivityLog,
        ActivityLog.user_id == user_id,
        sort=ActivityLog.timestamp.desc(),
        limit=limit
    )
    return activities

async def get_recent_activities(limit: int = 100) -> List[ActivityLog]:
    """
    Récupère les activités récentes globales
    """
    activities = await Database.engine.find(
        ActivityLog,
        sort=ActivityLog.timestamp.desc(),
        limit=limit
    )
    return activities