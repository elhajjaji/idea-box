from src.models.user import User
from src.services.database import Database
from typing import List, Optional

async def create_user(user: User) -> User:
    await Database.engine.save(user)
    return user

async def get_user(user_id: str) -> Optional[User]:
    return await Database.engine.find_one(User, User.id == user_id)

async def get_users() -> List[User]:
    return await Database.engine.find(User)

async def update_user(user_id: str, user_data: dict) -> Optional[User]:
    user = await get_user(user_id)
    if user:
        for key, value in user_data.items():
            setattr(user, key, value)
        await Database.engine.save(user)
        return user
    return None

async def delete_user(user_id: str) -> bool:
    user = await get_user(user_id)
    if user:
        await Database.engine.delete(user)
        return True
    return False

async def add_role_to_user(user_id: str, role: str) -> Optional[User]:
    user = await get_user(user_id)
    if user and role not in user.roles:
        user.roles.append(role)
        await Database.engine.save(user)
        return user
    return None

async def remove_role_from_user(user_id: str, role: str) -> Optional[User]:
    user = await get_user(user_id)
    if user and role in user.roles:
        user.roles.remove(role)
        await Database.engine.save(user)
        return user
    return None
