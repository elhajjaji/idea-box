from src.models.user import User
from src.models.subject import Subject
from src.services.database import Database
from src.services.idea_service import get_ideas_by_subject
from datetime import datetime, timedelta
from typing import Dict, Any

async def get_user_dashboard_stats(current_user: User):
    """
    Calcule les statistiques pour le tableau de bord de l'utilisateur,
    y compris les sujets assignés et les métriques associées.
    """
    # Récupérer les sujets de l'utilisateur
    user_subjects = await Database.engine.find(Subject, {
        "$or": [
            {"users_ids": {"$in": [str(current_user.id)]}},
            {"gestionnaires_ids": {"$in": [str(current_user.id)]}}
        ]
    })

    # Calculer les statistiques pour chaque sujet
    for subject in user_subjects:
        subject_ideas = await get_ideas_by_subject(str(subject.id))
        subject.ideas_count = len(subject_ideas)
        subject.votes_count = sum(len(idea.votes) for idea in subject_ideas)
        subject.user_ideas_count = len([
            idea for idea in subject_ideas if idea.user_id == str(current_user.id)
        ])

    # Statistiques globales utilisateur
    user_stats = {
        'subjects_count': len(user_subjects),
        'user_ideas_count': sum(getattr(s, 'user_ideas_count', 0) for s in user_subjects),
        'user_votes_count': 0,  # À implémenter
        'pending_count': 0      # À implémenter
    }

    return user_subjects, user_stats

async def get_subject_history_stats(subject_id: str, activities: list) -> Dict[str, Any]:
    """
    Calcule les statistiques pour la page d'historique d'un sujet
    """
    from src.services.idea_service import get_ideas_by_subject
    from src.services.subject_service import get_subject
    
    # Récupérer le sujet et ses idées
    subject = await get_subject(subject_id)
    ideas = await get_ideas_by_subject(subject_id)
    
    # Calculer les statistiques de base
    total_ideas = len(ideas)
    total_votes = sum(len(idea.votes) for idea in ideas)
    total_users = len(subject.users_ids) if subject else 0
    
    # Calculer les activités par période
    now = datetime.utcnow()
    activities_24h = len([a for a in activities if a.timestamp >= now - timedelta(hours=24)])
    activities_7d = len([a for a in activities if a.timestamp >= now - timedelta(days=7)])
    activities_30d = len([a for a in activities if a.timestamp >= now - timedelta(days=30)])
    
    return {
        'total_ideas': total_ideas,
        'total_votes': total_votes,
        'total_users': total_users,
        'activities_24h': activities_24h,
        'activities_7d': activities_7d,
        'activities_30d': activities_30d
    }
