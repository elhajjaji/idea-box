from src.models.idea import Idea
from src.models.subject import Subject
from src.services.database import Database
from typing import List, Optional

async def create_idea(idea: Idea) -> Idea:
    await Database.engine.save(idea)
    return idea

async def get_idea(idea_id: str) -> Optional[Idea]:
    return await Database.engine.find_one(Idea, Idea.id == idea_id)

async def get_ideas_by_subject(subject_id: str) -> List[Idea]:
    return await Database.engine.find(Idea, Idea.subject_id == subject_id)

async def update_idea(idea_id: str, title: str, description: str) -> Optional[Idea]:
    """
    Met à jour une idée avec un nouveau titre et une nouvelle description
    """
    idea = await get_idea(idea_id)
    if idea:
        idea.title = title
        idea.description = description
        await Database.engine.save(idea)
        return idea
    return None

async def delete_idea(idea_id: str) -> bool:
    """
    Supprime une idée
    """
    idea = await get_idea(idea_id)
    if idea:
        await Database.engine.delete(idea)
        return True
    return False

async def add_vote_to_idea(idea_id: str, user_id: str) -> Optional[Idea]:
    idea = await get_idea(idea_id)
    if idea and user_id not in idea.votes:
        idea.votes.append(user_id)
        await Database.engine.save(idea)
        return idea
    return None

async def remove_vote_from_idea(idea_id: str, user_id: str) -> Optional[Idea]:
    idea = await get_idea(idea_id)
    if idea and user_id in idea.votes:
        idea.votes.remove(user_id)
        await Database.engine.save(idea)
        return idea
    return None
