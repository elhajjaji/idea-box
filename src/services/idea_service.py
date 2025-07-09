from src.models.idea import Idea
from src.models.subject import Subject
from src.services.database import Database
from typing import List, Optional
from odmantic import ObjectId

async def create_idea(idea: Idea) -> Idea:
    await Database.engine.save(idea)
    return idea

async def get_idea(idea_id: str) -> Optional[Idea]:
    try:
        print(f"DEBUG - get_idea called with idea_id: {idea_id}")
        print(f"DEBUG - idea_id type: {type(idea_id)}")
        
        # Convert string ID to ObjectId for proper querying
        object_id = ObjectId(idea_id)
        print(f"DEBUG - Converted to ObjectId: {object_id}")
        
        # Try to find the idea
        idea = await Database.engine.find_one(Idea, Idea.id == object_id)
        print(f"DEBUG - Query result: {idea}")
        
        if idea:
            print(f"DEBUG - Found idea: {idea.title}, subject_id: {idea.subject_id}")
        else:
            print(f"DEBUG - No idea found with ObjectId: {object_id}")
            
            # Try to find all ideas to see what's in the database
            all_ideas = await Database.engine.find(Idea)
            print(f"DEBUG - Total ideas in database: {len(all_ideas)}")
            for i, db_idea in enumerate(all_ideas):
                print(f"DEBUG - Idea {i}: id={db_idea.id}, title={db_idea.title}, subject_id={db_idea.subject_id}")
                
        return idea
        
    except Exception as e:
        print(f"DEBUG - Error in get_idea: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def get_ideas_by_subject(subject_id: str) -> List[Idea]:
    return await Database.engine.find(Idea, Idea.subject_id == subject_id)

async def update_idea(idea_id: str, title: str, description: str) -> Optional[Idea]:
    """
    Met à jour une idée avec un nouveau titre et une nouvelle description
    """
    print(f"DEBUG - update_idea called with:")
    print(f"  idea_id: {idea_id}")
    print(f"  title: '{title}'")
    print(f"  description: '{description[:100]}...' (length: {len(description)})")
    
    idea = await get_idea(idea_id)
    print(f"DEBUG - Found idea: {idea.title if idea else 'None'}")
    
    if idea:
        print(f"DEBUG - Before update: title='{idea.title}', description='{idea.description[:100] if idea.description else 'None'}...'")
        
        idea.title = title
        idea.description = description
        
        print(f"DEBUG - After assignment: title='{idea.title}', description='{idea.description[:100]}...'")
        
        try:
            await Database.engine.save(idea)
            print(f"DEBUG - Successfully saved idea to database")
            
            # Vérifier que la sauvegarde a bien fonctionné
            saved_idea = await get_idea(idea_id)
            print(f"DEBUG - Verification - saved idea: title='{saved_idea.title}', description='{saved_idea.description[:100] if saved_idea.description else 'None'}...'")
            
            return saved_idea
        except Exception as e:
            print(f"DEBUG - Error saving idea: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    else:
        print(f"DEBUG - No idea found with id: {idea_id}")
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

# Note: Les fonctions de vote ont été déplacées vers VoteService
# Utilisez VoteService.add_vote() et VoteService.remove_vote() à la place
