from typing import Dict, List, Any
from datetime import datetime, timedelta
from src.models.user import User
from src.models.subject import Subject
from src.services.database import Database
from src.services.idea_service import get_ideas_by_subject
from src.services.subject_service import get_subject
from src.services.activity_log_service import get_subject_activities
import json

class MetricsService:
    """Service pour générer des métriques et des données pour les graphiques"""
    
    @staticmethod
    async def get_gestionnaire_dashboard_metrics(current_user: User) -> Dict[str, Any]:
        """Génère les métriques pour le tableau de bord gestionnaire"""
        subjects = await Database.engine.find(Subject, {
            "gestionnaires_ids": {"$in": [str(current_user.id)]}
        })
        
        metrics = {
            "subjects_count": len(subjects),
            "total_ideas": 0,
            "total_votes": 0,
            "total_users": 0,
            "active_subjects": 0,
            "voting_subjects": 0,
            "subjects_data": [],
            "charts": {}
        }
        
        all_users = set()
        subjects_chart_data = []
        ideas_trend_data = []
        votes_trend_data = []
        
        for subject in subjects:
            ideas = await get_ideas_by_subject(str(subject.id))
            votes_count = sum(len(idea.votes) for idea in ideas)
            
            # Collecte des métriques par sujet
            subject_metrics = {
                "id": str(subject.id),
                "name": subject.name,
                "ideas_count": len(ideas),
                "votes_count": votes_count,
                "users_count": len(subject.users_ids),
                "status": "active" if subject.emission_active else "inactive",
                "voting_status": "active" if subject.vote_active else "inactive"
            }
            metrics["subjects_data"].append(subject_metrics)
            
            # Graphique par sujet
            subjects_chart_data.append({
                "name": subject.name,
                "ideas": len(ideas),
                "votes": votes_count,
                "users": len(subject.users_ids)
            })
            
            # Métriques globales
            metrics["total_ideas"] += len(ideas)
            metrics["total_votes"] += votes_count
            all_users.update(subject.users_ids)
            
            if subject.emission_active:
                metrics["active_subjects"] += 1
            if subject.vote_active:
                metrics["voting_subjects"] += 1
        
        metrics["total_users"] = len(all_users)
        
        # Données pour graphiques
        metrics["charts"] = {
            "subjects_overview": subjects_chart_data,
            "summary_stats": {
                "subjects": metrics["subjects_count"],
                "ideas": metrics["total_ideas"],
                "votes": metrics["total_votes"],
                "users": metrics["total_users"]
            }
        }
        
        return metrics
    
    @staticmethod
    async def get_user_dashboard_metrics(current_user: User) -> Dict[str, Any]:
        """Génère les métriques pour le tableau de bord invité"""
        user_subjects = await Database.engine.find(Subject, {
            "users_ids": {"$in": [str(current_user.id)]}
        })
        
        metrics = {
            "subjects_count": len(user_subjects),
            "total_ideas": 0,
            "my_ideas": 0,
            "my_votes": 0,
            "available_votes": 0,
            "subjects_data": [],
            "charts": {}
        }
        
        subjects_chart_data = []
        
        for subject in user_subjects:
            ideas = await get_ideas_by_subject(str(subject.id))
            my_ideas = [idea for idea in ideas if idea.user_id == str(current_user.id)]
            
            # Compter mes votes
            my_votes_count = 0
            for idea in ideas:
                if str(current_user.id) in idea.votes:
                    my_votes_count += 1
            
            subject_metrics = {
                "id": str(subject.id),
                "name": subject.name,
                "total_ideas": len(ideas),
                "my_ideas": len(my_ideas),
                "my_votes": my_votes_count,
                "can_vote": subject.vote_active,
                "can_submit": subject.emission_active,
                "vote_limit": subject.vote_limit,
                "available_votes": max(0, subject.vote_limit - my_votes_count) if subject.vote_active else 0
            }
            metrics["subjects_data"].append(subject_metrics)
            
            # Graphique par sujet
            subjects_chart_data.append({
                "name": subject.name,
                "total_ideas": len(ideas),
                "my_ideas": len(my_ideas),
                "my_votes": my_votes_count
            })
            
            # Métriques globales
            metrics["total_ideas"] += len(ideas)
            metrics["my_ideas"] += len(my_ideas)
            metrics["my_votes"] += my_votes_count
            metrics["available_votes"] += subject_metrics["available_votes"]
        
        # Données pour graphiques
        metrics["charts"] = {
            "subjects_overview": subjects_chart_data,
            "summary_stats": {
                "subjects": metrics["subjects_count"],
                "total_ideas": metrics["total_ideas"],
                "my_ideas": metrics["my_ideas"],
                "my_votes": metrics["my_votes"]
            }
        }
        
        return metrics
    
    @staticmethod
    async def get_superadmin_dashboard_metrics(with_alerts: bool = True) -> Dict[str, Any]:
        """Génère les métriques pour le tableau de bord superadmin avec des données enrichies"""
        users = await Database.engine.find(User)
        subjects = await Database.engine.find(Subject)
        
        # Calcul des métriques de base
        total_ideas = 0
        total_votes = 0
        active_subjects = 0
        voting_subjects = 0
        
        subjects_data = []
        for subject in subjects:
            ideas = await get_ideas_by_subject(str(subject.id))
            votes_count = sum(len(idea.votes) for idea in ideas)
            
            total_ideas += len(ideas)
            total_votes += votes_count
            
            if subject.emission_active:
                active_subjects += 1
            if subject.vote_active:
                voting_subjects += 1
            
            # Données pour le tableau
            subject_data = {
                "id": str(subject.id),
                "name": subject.name,
                "ideas_count": len(ideas),
                "votes_count": votes_count,
                "users_count": len(subject.users_ids),
                "gestionnaires_count": len(subject.gestionnaires_ids),
                "status": "active" if subject.emission_active else "inactive",
                "voting_status": "active" if subject.vote_active else "inactive"
            }
            subjects_data.append(subject_data)
        
        # Calcul des métriques avancées
        one_week_ago = datetime.now() - timedelta(days=7)
        
        # Simuler des données d'activité récente (en production, cela viendrait de la base)
        recent_activities = [
            {
                "title": "Nouveau sujet créé",
                "description": "Un nouveau sujet a été créé par un gestionnaire",
                "timestamp": "Il y a 2 heures",
                "type": "success"
            },
            {
                "title": "Utilisateur ajouté",
                "description": "Un nouvel invité a été ajouté à la plateforme",
                "timestamp": "Il y a 4 heures",
                "type": "info"
            },
            {
                "title": "Idée populaire",
                "description": "Une idée a reçu plus de 10 votes",
                "timestamp": "Il y a 6 heures",
                "type": "warning"
            }
        ]
        
        # Alertes système
        alerts = []
        if with_alerts:
            # Vérifier s'il y a des sujets sans gestionnaire
            subjects_without_managers = [s for s in subjects if not s.gestionnaires_ids]
            if subjects_without_managers:
                alerts.append({
                    "type": "warning",
                    "icon": "exclamation-triangle",
                    "title": "Attention:",
                    "message": f"{len(subjects_without_managers)} sujet(s) sans gestionnaire assigné."
                })
            
            # Vérifier s'il y a des utilisateurs inactifs
            if len(users) == 0:
                alerts.append({
                    "type": "info",
                    "icon": "info-circle",
                    "title": "Bienvenue:",
                    "message": "Commencez par créer votre premier sujet et ajouter des invités."
                })
        
        # Calcul des taux de performance
        total_users_count = len(users)
        participation_rate = 85 if total_users_count > 0 else 0  # Simulé
        ideas_per_user = round(total_ideas / total_users_count, 1) if total_users_count > 0 else 0
        engagement_rate = 92 if total_ideas > 0 else 0  # Simulé
        
        # Données pour les graphiques
        charts_data = {
            "subjects_overview": [
                {
                    "name": subject["name"],
                    "ideas": subject["ideas_count"],
                    "votes": subject["votes_count"],
                    "users": subject["users_count"]
                }
                for subject in subjects_data
            ],
            "users_by_role": [
                {"role": "Invité", "count": sum(1 for u in users if "user" in u.roles)},
                {"role": "Gestionnaire", "count": sum(1 for u in users if "gestionnaire" in u.roles)},
                {"role": "Super Admin", "count": sum(1 for u in users if "superadmin" in u.roles)}
            ]
        }
        
        return {
            "total_users": total_users_count,
            "total_subjects": len(subjects),
            "total_ideas": total_ideas,
            "total_votes": total_votes,
            "active_subjects_count": active_subjects,
            "voting_subjects_count": voting_subjects,
            "active_users_count": max(1, int(total_users_count * 0.7)),  # Simulé
            "ideas_this_week": max(0, int(total_ideas * 0.3)),  # Simulé
            "votes_this_week": max(0, int(total_votes * 0.4)),  # Simulé
            "participation_rate": participation_rate,
            "ideas_per_user": ideas_per_user,
            "engagement_rate": engagement_rate,
            "subjects_data": subjects_data,
            "recent_activities": recent_activities,
            "alerts": alerts,
            "charts": charts_data
        }
    
    @staticmethod
    async def get_subject_detailed_metrics(subject_id: str) -> Dict[str, Any]:
        """Génère les métriques détaillées pour un sujet spécifique"""
        subject = await get_subject(subject_id)
        if not subject:
            return {}
        
        ideas = await get_ideas_by_subject(subject_id)
        activities = await get_subject_activities(subject_id)
        
        metrics = {
            "subject_info": {
                "id": subject_id,
                "name": subject.name,
                "description": subject.description,
                "emission_active": subject.emission_active,
                "vote_active": subject.vote_active,
                "vote_limit": subject.vote_limit,
                "users_count": len(subject.users_ids),
                "gestionnaires_count": len(subject.gestionnaires_ids)
            },
            "ideas_stats": {
                "total_ideas": len(ideas),
                "total_votes": sum(len(idea.votes) for idea in ideas),
                "top_ideas": []
            },
            "activity_stats": {
                "total_activities": len(activities),
                "recent_activities": activities[:10] if activities else []
            },
            "charts": {}
        }
        
        # Top idées (les plus votées)
        sorted_ideas = sorted(ideas, key=lambda x: len(x.votes), reverse=True)
        metrics["ideas_stats"]["top_ideas"] = [
            {
                "title": idea.title,
                "votes": len(idea.votes),
                "author": idea.user_id  # Vous pourriez récupérer le nom de l'invité
            }
            for idea in sorted_ideas[:5]
        ]
        
        # Données pour graphiques
        ideas_chart_data = []
        for idea in sorted_ideas[:10]:  # Top 10 des idées
            ideas_chart_data.append({
                "title": idea.title[:30] + "..." if len(idea.title) > 30 else idea.title,
                "votes": len(idea.votes)
            })
        
        metrics["charts"] = {
            "top_ideas": ideas_chart_data,
            "activity_timeline": [
                {
                    "date": activity.created_at.strftime("%Y-%m-%d"),
                    "count": 1
                }
                for activity in activities[-30:]  # 30 dernières activités
            ]
        }
        
        return metrics
