#!/usr/bin/env python3
"""
Script pour nettoyer les votes en trop qui dépassent la limite par sujet
"""

import asyncio
from src.services.database import Database
from src.models.subject import Subject
from src.models.idea import Idea
from src.models.vote import Vote
from src.services.vote_service import VoteService

async def clean_excess_votes():
    """Nettoie les votes qui dépassent la limite par sujet"""
    print("🧹 Nettoyage des votes en trop...")
    
    # Initialiser la base de données
    await Database.initialize()
    
    # Récupérer tous les sujets
    subjects = await Database.engine.find(Subject)
    
    cleaned_count = 0
    
    for subject in subjects:
        vote_limit = getattr(subject, 'vote_limit', 0)
        if vote_limit <= 0:
            print(f"⏭️  Sujet '{subject.name}': pas de limite de votes")
            continue
        
        print(f"🔍 Vérification du sujet '{subject.name}' (limite: {vote_limit})")
        
        # Récupérer toutes les idées de ce sujet
        ideas = await Database.engine.find(Idea, {"subject_id": str(subject.id)})
        
        # Pour chaque utilisateur du sujet, vérifier ses votes
        all_users = set(subject.users_ids + subject.gestionnaires_ids)
        
        for user_id in all_users:
            # Récupérer tous les votes de cet utilisateur pour ce sujet
            user_votes = []
            for idea in ideas:
                votes = await VoteService.get_user_votes_for_idea(str(idea.id), user_id)
                for vote in votes:
                    user_votes.append((vote, idea))
            
            if len(user_votes) > vote_limit:
                excess_count = len(user_votes) - vote_limit
                print(f"⚠️  Utilisateur {user_id}: {len(user_votes)} votes (limite: {vote_limit}) - {excess_count} en trop")
                
                # Trier les votes par date (garder les plus anciens)
                user_votes.sort(key=lambda x: x[0].created_at)
                
                # Supprimer les votes en trop (les plus récents)
                for i in range(vote_limit, len(user_votes)):
                    vote_to_remove, idea = user_votes[i]
                    print(f"🗑️  Suppression du vote pour l'idée '{idea.title}' (date: {vote_to_remove.created_at})")
                    await Database.engine.delete(vote_to_remove)
                    cleaned_count += 1
            else:
                print(f"✅ Utilisateur {user_id}: {len(user_votes)} votes (OK)")
    
    print(f"🎉 Nettoyage terminé ! {cleaned_count} vote(s) supprimé(s)")

async def verify_votes():
    """Vérifie l'état des votes après nettoyage"""
    print("\n🔍 Vérification après nettoyage...")
    
    subjects = await Database.engine.find(Subject)
    
    for subject in subjects:
        vote_limit = getattr(subject, 'vote_limit', 0)
        if vote_limit <= 0:
            continue
        
        print(f"\n📊 Sujet '{subject.name}' (limite: {vote_limit})")
        
        # Récupérer toutes les idées de ce sujet
        ideas = await Database.engine.find(Idea, {"subject_id": str(subject.id)})
        
        # Pour chaque utilisateur du sujet, compter ses votes
        all_users = set(subject.users_ids + subject.gestionnaires_ids)
        
        for user_id in all_users:
            user_votes_count = await VoteService.get_user_votes_count_for_subject(user_id, str(subject.id))
            if user_votes_count > 0:
                status = "✅" if user_votes_count <= vote_limit else "❌"
                print(f"   {status} Utilisateur {user_id}: {user_votes_count}/{vote_limit} votes")

async def main():
    try:
        await clean_excess_votes()
        await verify_votes()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
