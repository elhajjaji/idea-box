import os
from src.models.user import User
from src.services.database import Database
from src.services.auth_service import get_password_hash
import asyncio
from dotenv import load_dotenv

async def init_superadmin():
    """
    Initialise le compte SuperAdmin depuis la configuration .env
    """
    load_dotenv()
    
    # Récupérer les informations du SuperAdmin depuis les variables d'environnement
    email = os.getenv("SUPERADMIN_EMAIL")
    nom = os.getenv("SUPERADMIN_NOM")
    prenom = os.getenv("SUPERADMIN_PRENOM")
    password = os.getenv("SUPERADMIN_PASSWORD")
    
    if not all([email, nom, prenom, password]):
        print("❌ Configuration SuperAdmin incomplète dans le fichier .env")
        return False
    
    try:
        # Vérifier si le SuperAdmin existe déjà
        existing_superadmin = await Database.engine.find_one(User, User.email == email)
        
        if existing_superadmin:
            # Vérifier si l'utilisateur a déjà le rôle superadmin
            if "superadmin" not in existing_superadmin.roles:
                existing_superadmin.roles.append("superadmin")
                await Database.engine.save(existing_superadmin)
                print(f"✅ Rôle SuperAdmin ajouté à l'utilisateur existant: {email}")
            else:
                print(f"ℹ️  SuperAdmin déjà configuré: {email}")
            return True
        
        # Créer le compte SuperAdmin
        hashed_password = get_password_hash(password)
        superadmin = User(
            email=email,
            nom=nom,
            prenom=prenom,
            pwd=hashed_password,
            roles=["superadmin"]
        )
        
        await Database.engine.save(superadmin)
        print(f"✅ Compte SuperAdmin créé avec succès: {email}")
        print(f"   Nom: {nom} {prenom}")
        print(f"   Email: {email}")
        print(f"   ⚠️  Mot de passe: {password}")
        print(f"   🔒 Changez le mot de passe après la première connexion!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la création du SuperAdmin: {str(e)}")
        return False

if __name__ == "__main__":
    # Script pour initialiser le SuperAdmin manuellement
    async def main():
        await Database.connect()
        await init_superadmin()
        await Database.close()
    
    asyncio.run(main())