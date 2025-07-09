#!/usr/bin/env python3
"""
Script pour nettoyer les votes en excès dans la base de données.
Ce script supprime les votes qui dépassent la limite de votes par sujet.
"""

import asyncio
from src.services.database import Database
from src.models.vote import Vote
from src.models.idea import Idea
from src.models.subject import Subject
from src.services.vote_service import VoteService

async def clean_excess_votes():
    """Nettoie les votes en excès pour tous les utilisateurs"""
    try:
        # Initialiser la base de données
        await Database.initialize()
        
        print("🧹 Nettoyage des votes en excès...")
        
        # Récupérer tous les sujets
        all_subjects = await Database.engine.find(Subject)
        
        cleaned_votes = 0
        total_users_processed = 0
        
        for subject in all_subjects:
            vote_limit = getattr(subject, 'vote_limit', 0)
            if vote_limit <= 0:
                continue
                
            print(f"\n📋 Traitement du sujet: {subject.name} (limite: {vote_limit} votes)")
            
            # Récupérer tous les utilisateurs de ce sujet
            all_user_ids = set(subject.users_ids + subject.gestionnaires_ids)
            
            for user_id in all_user_ids:
                # Compter les votes actuels de l'utilisateur pour ce sujet
                current_votes = await VoteService.get_user_votes_count_for_subject(user_id, str(subject.id))
                
                if current_votes > vote_limit:
                    print(f"⚠️  Utilisateur {user_id}: {current_votes} votes (limite: {vote_limit})")
                    
                    # Récupérer toutes les idées du sujet
                    from src.services.idea_service import get_ideas_by_subject
                    ideas = await get_ideas_by_subject(str(subject.id))
                    
                    # Récupérer tous les votes de l'utilisateur pour ce sujet avec timestamp
                    user_votes_with_dates = []
                    for idea in ideas:
                        votes = await VoteService.get_user_votes_for_idea(str(idea.id), user_id)
                        for vote in votes:
                            user_votes_with_dates.append(vote)
                    
                    # Trier par date (garder les plus anciens)
                    user_votes_with_dates.sort(key=lambda v: v.created_at)
                    
                    # Supprimer les votes en excès (les plus récents)
                    votes_to_remove = current_votes - vote_limit
                    votes_to_delete = user_votes_with_dates[-votes_to_remove:]
                    
                    for vote in votes_to_delete:
                        await Database.engine.delete(vote)
                        cleaned_votes += 1
                        print(f"  ❌ Supprimé vote du {vote.created_at} pour l'idée {vote.idea_id}")
                    
                    # Vérifier que le nettoyage a fonctionné
                    new_count = await VoteService.get_user_votes_count_for_subject(user_id, str(subject.id))
                    print(f"  ✅ Votes après nettoyage: {new_count}/{vote_limit}")
                
                total_users_processed += 1
        
        print(f"\n🎉 Nettoyage terminé!")
        print(f"   👥 Utilisateurs traités: {total_users_processed}")
        print(f"   🗑️  Votes supprimés: {cleaned_votes}")
        
        if cleaned_votes > 0:
            print(f"\n✅ Les compteurs devraient maintenant être corrects.")
        else:
            print(f"\n✅ Aucun vote en excès trouvé.")
            
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(clean_excess_votes())
