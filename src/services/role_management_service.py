from src.models.user import User
from src.models.subject import Subject
from src.services.database import Database
from typing import List
from bson import ObjectId

class RoleManagementService:
    """Service pour la gestion automatique des rôles basée sur les assignations aux sujets"""
    
    @staticmethod
    async def update_user_roles_from_subjects(user_id) -> List[str]:
        """
        Met à jour automatiquement les rôles d'un utilisateur selon ses assignations aux sujets
        Retourne la liste des nouveaux rôles
        """
        try:
            # Convertir en ObjectId si c'est un string
            if isinstance(user_id, str):
                try:
                    user_object_id = ObjectId(user_id)
                except:
                    print(f"❌ ID utilisateur invalide: {user_id}")
                    return []
            else:
                user_object_id = user_id
            
            # Récupérer l'utilisateur
            user = await Database.engine.find_one(User, User.id == user_object_id)
            if not user:
                print(f"❌ Utilisateur {user_id} non trouvé")
                return []
            
            # Récupérer tous les sujets
            all_subjects = await Database.engine.find(Subject)
            
            # Analyser les assignations
            is_user = False  # Invité sur au moins un sujet
            is_gestionnaire = False  # Gestionnaire sur au moins un sujet
            is_superadmin = "superadmin" in (user.roles or [])  # Garder le statut superadmin s'il existe
            
            print(f"🔍 Analyse pour {user.email} (ID: {user_id})")
            
            user_id_str = str(user.id)  # Convertir l'ObjectId en string pour les comparaisons
            
            for subject in all_subjects:
                # Vérifier si l'utilisateur est invité (users_ids)
                if user_id_str in subject.users_ids:
                    is_user = True
                    print(f"   📝 Invité sur: {subject.name}")
                
                # Vérifier si l'utilisateur est gestionnaire (gestionnaires_ids)
                if user_id_str in subject.gestionnaires_ids:
                    is_gestionnaire = True
                    print(f"   🔧 Gestionnaire de: {subject.name}")
            
            # Construire la nouvelle liste de rôles
            new_roles = []
            
            if is_superadmin:
                new_roles.append("superadmin")
                print(f"   👑 Conserve superadmin")
            
            if is_gestionnaire:
                new_roles.append("gestionnaire")
                print(f"   🔧 Ajoute gestionnaire")
            
            if is_user:
                new_roles.append("user")
                print(f"   📝 Ajoute user")
            
            print(f"   ✅ Nouveaux rôles calculés: {new_roles}")
            
            # Mettre à jour l'utilisateur
            user.roles = new_roles
            await Database.engine.save(user)
            
            print(f"✅ Rôles mis à jour pour {user.email}: {new_roles}")
            return new_roles
            
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour des rôles pour {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    async def update_all_users_roles():
        """Met à jour les rôles de tous les utilisateurs selon leurs assignations"""
        try:
            all_users = await Database.engine.find(User)
            updated_count = 0
            
            for user in all_users:
                if user.email != "admin@admin.com":  # Ne pas toucher au compte admin principal
                    old_roles = user.roles.copy() if user.roles else []
                    new_roles = await RoleManagementService.update_user_roles_from_subjects(str(user.id))
                    
                    if set(old_roles) != set(new_roles):
                        updated_count += 1
                        print(f"📝 {user.email}: {old_roles} → {new_roles}")
            
            print(f"✅ Mise à jour terminée: {updated_count} utilisateurs modifiés")
            return updated_count
            
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour globale des rôles: {e}")
            return 0
    
    @staticmethod
    async def add_user_to_subject_as_invitee(user_id: str, subject_id: str):
        """Ajoute un utilisateur comme invité sur un sujet et met à jour ses rôles"""
        try:
            subject = await Database.engine.find_one(Subject, Subject.id == subject_id)
            if not subject:
                return False
            
            # Ajouter à la liste des invités s'il n'y est pas déjà
            if user_id not in subject.users_ids:
                subject.users_ids.append(user_id)
                await Database.engine.save(subject)
            
            # Mettre à jour les rôles automatiquement
            await RoleManagementService.update_user_roles_from_subjects(user_id)
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout comme invité: {e}")
            return False
    
    @staticmethod
    async def add_user_to_subject_as_manager(user_id: str, subject_id: str):
        """Ajoute un utilisateur comme gestionnaire sur un sujet et met à jour ses rôles"""
        try:
            subject = await Database.engine.find_one(Subject, Subject.id == subject_id)
            if not subject:
                return False
            
            # Ajouter à la liste des gestionnaires s'il n'y est pas déjà
            if user_id not in subject.gestionnaires_ids:
                subject.gestionnaires_ids.append(user_id)
                await Database.engine.save(subject)
            
            # Mettre à jour les rôles automatiquement
            await RoleManagementService.update_user_roles_from_subjects(user_id)
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'ajout comme gestionnaire: {e}")
            return False
    
    @staticmethod
    async def remove_user_from_subject(user_id: str, subject_id: str, as_manager: bool = False):
        """Retire un utilisateur d'un sujet et met à jour ses rôles"""
        try:
            subject = await Database.engine.find_one(Subject, Subject.id == subject_id)
            if not subject:
                return False
            
            # Retirer de la liste appropriée
            if as_manager and user_id in subject.gestionnaires_ids:
                subject.gestionnaires_ids.remove(user_id)
            elif not as_manager and user_id in subject.users_ids:
                subject.users_ids.remove(user_id)
            
            await Database.engine.save(subject)
            
            # Mettre à jour les rôles automatiquement
            await RoleManagementService.update_user_roles_from_subjects(user_id)
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du retrait du sujet: {e}")
            return False