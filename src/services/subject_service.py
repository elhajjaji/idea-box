from bson import ObjectId
from src.models.subject import Subject
from src.models.user import User
from src.services.database import Database
from typing import List, Optional

async def get_subject(subject_id: str) -> Optional[Subject]:
    try:
        # Convert string ID to ObjectId and use MongoDB query syntax
        return await Database.engine.find_one(Subject, {"_id": ObjectId(subject_id)})
    except Exception:
        # If ObjectId conversion fails, return None
        return None

async def get_subjects_by_gestionnaire(gestionnaire_id: str) -> List[Subject]:
    return await Database.engine.find(Subject, {"gestionnaires_ids": {"$in": [gestionnaire_id]}})

async def update_subject(subject_id: str, subject_data: dict) -> Optional[Subject]:
    subject = await get_subject(subject_id)
    if subject:
        for key, value in subject_data.items():
            setattr(subject, key, value)
        await Database.engine.save(subject)
        return subject
    return None

async def add_user_to_subject(subject_id: str, user_id: str) -> Optional[Subject]:
    subject = await get_subject(subject_id)
    if subject and user_id not in subject.users_ids:
        subject.users_ids.append(user_id)
        await Database.engine.save(subject)
        return subject
    return None

async def remove_user_from_subject(subject_id: str, user_id: str) -> Optional[Subject]:
    subject = await get_subject(subject_id)
    if subject and user_id in subject.users_ids:
        subject.users_ids.remove(user_id)
        await Database.engine.save(subject)
        return subject
    return None

async def activate_emission(subject_id: str) -> Optional[Subject]:
    subject = await get_subject(subject_id)
    if subject:
        subject.emission_active = True
        subject.vote_active = False # Emission and vote cannot be active at the same time
        await Database.engine.save(subject)
        return subject
    return None

async def deactivate_emission(subject_id: str) -> Optional[Subject]:
    subject = await get_subject(subject_id)
    if subject:
        subject.emission_active = False
        await Database.engine.save(subject)
        return subject
    return None

async def activate_vote(subject_id: str) -> Optional[Subject]:
    subject = await get_subject(subject_id)
    if subject:
        subject.vote_active = True
        subject.emission_active = False # Emission and vote cannot be active at the same time
        await Database.engine.save(subject)
        return subject
    return None

async def close_vote(subject_id: str) -> Optional[Subject]:
    subject = await get_subject(subject_id)
    if subject:
        subject.vote_active = False
        await Database.engine.save(subject)
        return subject
    return None

async def abandon_vote(subject_id: str) -> Optional[Subject]:
    subject = await get_subject(subject_id)
    if subject:
        subject.vote_active = False
        # TODO: Clear votes for ideas in this subject if abandoning vote means resetting
        await Database.engine.save(subject)
        return subject
    return None
