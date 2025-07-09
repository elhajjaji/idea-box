#!/usr/bin/env python3
"""
Script de synchronisation des rôles utilisateurs
Corrige automatiquement les rôles selon les assignations aux sujets
"""

import asyncio
import sys
import os

# Ajouter le répertoire racine au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.database import Database
from src.services.role_management_service import RoleManagementService
from src.models.user import User
from src.models.subject import Subject

async def analyze_pierre_martin():
    """Analyse spécifique pour Pierre Martin"""
    print("🔍 Analyse de Pierre Martin...")
    
    # Trouver Pierre Martin
    pierre = await Database.engine.find_one(User, User.email == "pierre.martin@techcorp-innovation.fr")
    if not pierre:
        print("❌ Pierre Martin non trouvé!")
        return
    
    print(f"👤 Utilisateur trouvé: {pierre.prenom} {pierre.nom} ({pierre.email})")
    print(f"🏷️  Rôles actuels: {pierre.roles}")
    
    # Analyser ses assignations
    all_subjects = await Database.engine.find(Subject)
    managed_subjects = []
    invited_subjects = []
    
    for subject in all_subjects:
        if str(pierre.id) in subject.gestionnaires_ids:
            managed_subjects.append(subject.name)
        if str(pierre.id) in subject.users_ids:
            invited_subjects.append(subject.name)
    
    print(f"🔧 Gère les sujets: {managed_subjects}")
    print(f"📝 Invité sur les sujets: {invited_subjects}")
    
    # Calculer les rôles attendus
    expected_roles = []
    if "superadmin" in (pierre.roles or []):
        expected_roles.append("superadmin")
    if managed_subjects:
        expected_roles.append("gestionnaire")
    if invited_subjects:
        expected_roles.append("user")
    
    print(f"✅ Rôles attendus: {expected_roles}")
    
    # Corriger si nécessaire
    if set(pierre.roles or []) != set(expected_roles):
        print("🔄 Correction des rôles nécessaire...")
        new_roles = await RoleManagementService.update_user_roles_from_subjects(str(pierre.id))
        print(f"✅ Rôles corrigés: {new_roles}")
    else:
        print("✅ Rôles déjà corrects!")

async def main():
    """Script principal de synchronisation"""
    print("🔄 Début de la synchronisation des rôles utilisateurs...")
    print("-" * 60)
    
    try:
        # Initialiser la base de données
        await Database.connect()
        print("✅ Connexion à la base de données établie")
        
        # Analyser Pierre Martin spécifiquement
        await analyze_pierre_martin()
        
        print("\n" + "=" * 60)
        print("📊 État général de tous les utilisateurs :")
        
        # Afficher l'état actuel
        all_users = await Database.engine.find(User)
        for user in all_users:
            if user.email != "admin@admin.com":  # Utiliser email au lieu de username
                # Analyser ses assignations
                all_subjects = await Database.engine.find(Subject)
                managed_count = sum(1 for s in all_subjects if str(user.id) in s.gestionnaires_ids)
                invited_count = sum(1 for s in all_subjects if str(user.id) in s.users_ids)
                
                print(f"   {user.prenom} {user.nom} ({user.email}):")
                print(f"      - Rôles: {user.roles}")
                print(f"      - Gère {managed_count} sujet(s), invité sur {invited_count} sujet(s)")
        
        # Synchroniser tous les rôles
        print("\n🔄 Synchronisation globale en cours...")
        updated_count = await RoleManagementService.update_all_users_roles()
        
        print("\n✅ Synchronisation terminée !")
        print(f"📈 {updated_count} utilisateurs mis à jour")
        
        # Vérifier Pierre Martin après correction
        print("\n🔍 Vérification finale de Pierre Martin...")
        await analyze_pierre_martin()
        
        print("\n" + "=" * 60)
        print("🎉 Synchronisation des rôles terminée avec succès !")
        print("💡 Les utilisateurs ont maintenant les rôles corrects selon leurs assignations aux sujets.")
        
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Fermer la connexion à la base de données
        await Database.close()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)