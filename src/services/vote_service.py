from typing import List
from src.models.vote import Vote
from src.services.database import Database

class VoteService:
    """Service pour gérer les votes avec le nouveau modèle Vote"""
    
    @staticmethod
    async def get_votes_for_idea(idea_id: str) -> List[Vote]:
        """Récupère tous les votes pour une idée"""
        return await Database.engine.find(Vote, {"idea_id": idea_id})
    
    @staticmethod
    async def get_votes_count_for_idea(idea_id: str) -> int:
        """Compte le nombre de votes pour une idée"""
        votes = await VoteService.get_votes_for_idea(idea_id)
        return len(votes)
    
    @staticmethod
    async def get_votes_count_for_subject(subject_id: str) -> int:
        """Compte le nombre total de votes pour toutes les idées d'un sujet"""
        from src.services.idea_service import get_ideas_by_subject
        ideas = await get_ideas_by_subject(subject_id)
        total_votes = 0
        for idea in ideas:
            votes_count = await VoteService.get_votes_count_for_idea(str(idea.id))
            total_votes += votes_count
        return total_votes
    
    @staticmethod
    async def get_user_votes_for_idea(idea_id: str, user_id: str) -> List[Vote]:
        """Récupère les votes d'un utilisateur pour une idée"""
        return await Database.engine.find(Vote, {"idea_id": idea_id, "user_id": user_id})
    
    @staticmethod
    async def has_user_voted_for_idea(idea_id: str, user_id: str) -> bool:
        """Vérifie si un utilisateur a voté pour une idée"""
        votes = await VoteService.get_user_votes_for_idea(idea_id, user_id)
        return len(votes) > 0
    
    @staticmethod
    async def get_voter_ids_for_idea(idea_id: str) -> List[str]:
        """Récupère la liste des IDs des utilisateurs qui ont voté pour une idée"""
        votes = await VoteService.get_votes_for_idea(idea_id)
        return [vote.user_id for vote in votes]
    
    @staticmethod
    async def add_vote(idea_id: str, user_id: str, votation_id: str = None) -> Vote:
        """Ajoute un vote pour une idée"""
        from datetime import datetime
        
        # Vérifier si l'utilisateur a déjà voté
        if await VoteService.has_user_voted_for_idea(idea_id, user_id):
            raise ValueError("L'utilisateur a déjà voté pour cette idée")
        
        vote = Vote(
            idea_id=idea_id,
            user_id=user_id,
            votation_id=votation_id or "",
            created_at=datetime.now()
        )
        return await Database.engine.save(vote)
    
    @staticmethod
    async def remove_vote(idea_id: str, user_id: str) -> bool:
        """Supprime le vote d'un utilisateur pour une idée"""
        votes = await VoteService.get_user_votes_for_idea(idea_id, user_id)
        if votes:
            for vote in votes:
                await Database.engine.delete(vote)
            return True
        return False