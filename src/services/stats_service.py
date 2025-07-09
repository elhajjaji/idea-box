from src.models.user import User
from src.models.subject import Subject
from src.services.database import Database
from src.services.idea_service import get_ideas_by_subject
from src.services.vote_service import VoteService

async def get_user_dashboard_stats(current_user: User, request=None):
    """
    Calcule les statistiques pour le tableau de bord de l'utilisateur,
    y compris les sujets assignés et les métriques associées.
    """
    # Récupérer tous les sujets de l'utilisateur
    all_user_subjects = await Database.engine.find(Subject, {
        "$or": [
            {"users_ids": {"$in": [str(current_user.id)]}},
            {"gestionnaires_ids": {"$in": [str(current_user.id)]}}
        ]
    })
    
    # Filtrer selon les préférences si elles existent
    user_subjects = all_user_subjects
    user_preferences_dict = {}  # Pour stocker les préférences sans modifier les objets Subject
    
    if request:
        user_preferences = request.session.get("subject_preferences", {})
        selected_subjects = user_preferences.get(str(current_user.id), [])
        
        print(f"DEBUG - Préférences utilisateur {current_user.id}: {selected_subjects}")
        print(f"DEBUG - Nombre total de sujets: {len(all_user_subjects)}")
        
        # Si l'utilisateur a des préférences définies, les appliquer
        if selected_subjects:
            user_subjects = [
                subject for subject in all_user_subjects 
                if str(subject.id) in selected_subjects
            ]
            print(f"DEBUG - Nombre de sujets après filtrage: {len(user_subjects)}")
        else:
            print("DEBUG - Aucune préférence définie, affichage de tous les sujets")
        
        # Créer un dictionnaire de préférences pour utilisation dans le template
        for subject in all_user_subjects:
            user_preferences_dict[str(subject.id)] = str(subject.id) in selected_subjects if selected_subjects else True

    # Calculer les statistiques pour chaque sujet
    for subject in user_subjects:
        subject_ideas = await get_ideas_by_subject(str(subject.id))
        subject.ideas_count = len(subject_ideas)
        
        # Calculer le nombre total de votes pour toutes les idées du sujet
        subject.votes_count = 0
        for idea in subject_ideas:
            votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
            subject.votes_count += votes_count
            
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

    return all_user_subjects, user_subjects, user_stats, user_preferences_dict
