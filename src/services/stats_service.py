from src.models.user import User
from src.models.subject import Subject
from src.services.database import Database
from src.services.idea_service import get_ideas_by_subject

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
