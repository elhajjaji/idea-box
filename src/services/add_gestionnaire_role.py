http://localhost:8000/superadmin/dashboardimport asyncio
from src.services.database import Database
from src.models.user import User

async def add_gestionnaire_role(email):
    await Database.connect()
    user = await Database.engine.find_one(User, User.email == email)
    if user and "gestionnaire" not in user.roles:
        user.roles.append("gestionnaire")
        await Database.engine.save(user)
        print(f"✅ Rôle 'gestionnaire' ajouté à {email}")
    else:
        print(f"ℹ️  Utilisateur non trouvé ou déjà gestionnaire : {email}")
    await Database.close()

if __name__ == "__main__":
    asyncio.run(add_gestionnaire_role("com.test1@gmail.com"))
