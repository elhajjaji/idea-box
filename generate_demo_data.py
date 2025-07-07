#!/usr/bin/env python3
"""
Script de génération de données de démonstration pour Idea Box
Génère des utilisateurs, sujets, idées et logs d'activité pour tester l'application
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List
import sys
import os

# Ajouter le répertoire src au path pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.models.user import User
from src.models.subject import Subject
from src.models.idea import Idea
from src.models.activity_log import ActivityLog
from src.services.database import Database
from src.services.auth_service import get_password_hash


class DemoDataGenerator:
    """Générateur de données de démonstration"""
    
    def __init__(self):
        self.users = []
        self.subjects = []
        self.ideas = []
        self.activities = []
        
        # Données de base pour la génération
        self.prenoms = [
            "Alice", "Bob", "Charlie", "Diana", "Ethan", "Fiona", "Gabriel", "Hannah",
            "Ivan", "Julia", "Kevin", "Laura", "Marcus", "Nina", "Oscar", "Paula",
            "Quentin", "Rachel", "Samuel", "Tania", "Ulrich", "Valerie", "William", "Xenia",
            "Yves", "Zoe", "Antoine", "Beatrice", "Cedric", "Delphine", "Emilie", "Fabien"
        ]
        
        self.noms = [
            "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand",
            "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "David",
            "Bertrand", "Roux", "Vincent", "Fournier", "Morel", "Girard", "Andre", "Lefevre",
            "Mercier", "Dupont", "Lambert", "Bonnet", "Francois", "Martinez", "Legrand", "Garnier"
        ]
        
        self.sujets_demo = [
            {
                "name": "Amélioration de l'environnement de travail",
                "description": "Propositions pour rendre notre espace de travail plus agréable, productif et accueillant pour tous les employés."
            },
            {
                "name": "Innovation technologique",
                "description": "Idées pour moderniser notre infrastructure technique et adopter de nouvelles technologies innovantes."
            },
            {
                "name": "Processus de recrutement",
                "description": "Suggestions pour optimiser notre processus de recrutement et améliorer l'expérience des candidats."
            },
            {
                "name": "Formation et développement professionnel",
                "description": "Propositions de formations, ateliers et programmes de développement des compétences."
            },
            {
                "name": "Communication interne",
                "description": "Idées pour améliorer la communication entre les équipes et la diffusion d'informations."
            },
            {
                "name": "Responsabilité sociale et environnementale",
                "description": "Initiatives pour réduire notre impact environnemental et renforcer notre engagement social."
            },
            {
                "name": "Amélioration des processus métier",
                "description": "Optimisations et simplifications des processus internes pour gagner en efficacité."
            },
            {
                "name": "Événements et activités d'équipe",
                "description": "Organisation d'événements, team buildings et activités pour renforcer la cohésion d'équipe."
            }
        ]
        
        self.idees_exemples = {
            "Amélioration de l'environnement de travail": [
                {
                    "title": "Espace de détente avec canapés",
                    "description": "Créer un espace détente confortable avec canapés, plantes et éclairage tamisé pour les pauses."
                },
                {
                    "title": "Salle de sieste",
                    "description": "Aménager une petite salle pour permettre aux employés de faire une sieste réparatrice."
                },
                {
                    "title": "Espaces de travail modulables",
                    "description": "Installer des cloisons mobiles pour adapter l'espace selon les besoins (travail individuel/équipe)."
                },
                {
                    "title": "Amélioration de l'éclairage",
                    "description": "Remplacer l'éclairage fluorescent par des LED avec variateur pour un confort visuel optimal."
                },
                {
                    "title": "Distributeur de fruits gratuits",
                    "description": "Mettre à disposition des fruits frais gratuitement pour encourager une alimentation saine."
                }
            ],
            "Innovation technologique": [
                {
                    "title": "Migration vers le cloud",
                    "description": "Migrer notre infrastructure vers le cloud pour améliorer la scalabilité et réduire les coûts."
                },
                {
                    "title": "Automatisation des tests",
                    "description": "Mettre en place une pipeline CI/CD complète avec tests automatisés pour améliorer la qualité."
                },
                {
                    "title": "Intelligence artificielle pour le support",
                    "description": "Implémenter un chatbot IA pour le support client de niveau 1 et FAQ automatique."
                },
                {
                    "title": "Tableau de bord temps réel",
                    "description": "Créer des dashboards en temps réel pour suivre les KPIs métier et techniques."
                },
                {
                    "title": "Application mobile interne",
                    "description": "Développer une app mobile pour accéder aux outils internes en mobilité."
                }
            ],
            "Processus de recrutement": [
                {
                    "title": "Entretiens vidéo asynchrones",
                    "description": "Permettre aux candidats de répondre aux questions en vidéo à leur rythme."
                },
                {
                    "title": "Tests techniques en ligne",
                    "description": "Créer une plateforme de tests techniques adaptés à chaque poste."
                },
                {
                    "title": "Programme de cooptation renforcé",
                    "description": "Améliorer le système de cooptation avec des primes attractives et un suivi personnalisé."
                },
                {
                    "title": "Journées portes ouvertes virtuelles",
                    "description": "Organiser des événements en ligne pour faire découvrir l'entreprise aux candidats potentiels."
                }
            ],
            "Formation et développement professionnel": [
                {
                    "title": "Plateforme de e-learning interne",
                    "description": "Créer une plateforme de formation en ligne avec des parcours personnalisés."
                },
                {
                    "title": "Mentorat inter-équipes",
                    "description": "Mettre en place un programme de mentorat entre collaborateurs de différentes équipes."
                },
                {
                    "title": "Conférences techniques mensuelles",
                    "description": "Organiser des présentations internes sur les nouvelles technologies et méthodologies."
                },
                {
                    "title": "Budget formation individuel",
                    "description": "Allouer un budget annuel de formation que chaque employé peut utiliser librement."
                }
            ],
            "Communication interne": [
                {
                    "title": "Newsletter hebdomadaire interactive",
                    "description": "Créer une newsletter avec sondages, actualités et contributions des équipes."
                },
                {
                    "title": "Mur d'expression anonyme",
                    "description": "Installer un système pour permettre l'expression anonyme d'idées et préoccupations."
                },
                {
                    "title": "Réunions café mensuelles",
                    "description": "Organiser des rencontres informelles entre management et équipes autour d'un café."
                },
                {
                    "title": "Application de chat interne",
                    "description": "Déployer une solution de messagerie instantanée pour faciliter les échanges rapides."
                }
            ],
            "Responsabilité sociale et environnementale": [
                {
                    "title": "Programme de covoiturage",
                    "description": "Créer une plateforme pour organiser le covoiturage entre collègues."
                },
                {
                    "title": "Tri sélectif renforcé",
                    "description": "Améliorer le système de tri avec plus de catégories et une meilleure signalétique."
                },
                {
                    "title": "Partenariat avec associations locales",
                    "description": "Développer des partenariats pour des actions bénévoles et du mécénat de compétences."
                },
                {
                    "title": "Réduction du papier",
                    "description": "Digitaliser tous les processus pour tendre vers le zéro papier."
                }
            ]
        }
    
    async def init_database(self):
        """Initialise la connexion à la base de données"""
        await Database.connect()
        print("✅ Connexion à la base de données établie")
    
    async def clear_existing_data(self):
        """Supprime toutes les données existantes (ATTENTION: destructif !)"""
        try:
            await Database.engine.get_collection(User).delete_many({})
            await Database.engine.get_collection(Subject).delete_many({})
            await Database.engine.get_collection(Idea).delete_many({})
            await Database.engine.get_collection(ActivityLog).delete_many({})
            print("🗑️ Données existantes supprimées")
        except Exception as e:
            print(f"⚠️ Erreur lors de la suppression des données: {e}")
    
    async def generate_users(self, nb_users: int = 25):
        """Génère des utilisateurs avec différents rôles"""
        print(f"👥 Génération de {nb_users} utilisateurs...")
        
        # Super admin
        superadmin = User(
            email="admin@example.com",
            nom="Admin",
            prenom="Super",
            pwd=get_password_hash("admin123"),
            roles=["user", "superadmin"]
        )
        await Database.engine.save(superadmin)
        self.users.append(superadmin)
        
        # Gestionnaires (15% des utilisateurs)
        nb_gestionnaires = max(3, nb_users // 7)
        for i in range(nb_gestionnaires):
            prenom = random.choice(self.prenoms)
            nom = random.choice(self.noms)
            email = f"{prenom.lower()}.{nom.lower()}@example.com"
            
            gestionnaire = User(
                email=email,
                nom=nom,
                prenom=prenom,
                pwd=get_password_hash("demo123"),
                roles=["user", "gestionnaire"]
            )
            await Database.engine.save(gestionnaire)
            self.users.append(gestionnaire)
        
        # Utilisateurs standard
        nb_invites = nb_users - len(self.users)
        used_combinations = set()
        
        for i in range(nb_invites):
            # Éviter les doublons nom/prénom
            while True:
                prenom = random.choice(self.prenoms)
                nom = random.choice(self.noms)
                if (prenom, nom) not in used_combinations:
                    used_combinations.add((prenom, nom))
                    break
            
            email = f"{prenom.lower()}.{nom.lower()}@example.com"
            
            invite = User(
                email=email,
                nom=nom,
                prenom=prenom,
                pwd=get_password_hash("demo123"),
                roles=["user"]
            )
            await Database.engine.save(invite)
            self.users.append(invite)
        
        print(f"✅ {len(self.users)} utilisateurs créés (1 superadmin, {nb_gestionnaires} gestionnaires, {nb_invites} invités)")
    
    async def generate_subjects(self):
        """Génère des sujets avec gestionnaires et invités assignés"""
        print("📋 Génération des sujets...")
        
        superadmin = next(u for u in self.users if "superadmin" in u.roles)
        gestionnaires = [u for u in self.users if "gestionnaire" in u.roles]
        invites = [u for u in self.users if u.roles == ["user"]]
        
        for sujet_data in self.sujets_demo:
            # Assigner 1-2 gestionnaires par sujet
            subject_gestionnaires = random.sample(gestionnaires, random.randint(1, min(2, len(gestionnaires))))
            
            # Assigner 60-80% des invités au sujet
            nb_invites_assigne = random.randint(int(len(invites) * 0.6), int(len(invites) * 0.8))
            subject_invites = random.sample(invites, nb_invites_assigne)
            
            # États aléatoires mais cohérents
            emission_active = random.choice([True, False, False])  # 1/3 de chance
            vote_active = False if emission_active else random.choice([True, False])  # Mutuellement exclusif
            
            subject = Subject(
                name=sujet_data["name"],
                description=sujet_data["description"],
                superadmin_id=str(superadmin.id),
                gestionnaires_ids=[str(g.id) for g in subject_gestionnaires],
                users_ids=[str(u.id) for u in subject_invites],
                emission_active=emission_active,
                vote_active=vote_active,
                vote_limit=random.randint(1, 5)
            )
            
            await Database.engine.save(subject)
            self.subjects.append(subject)
        
        print(f"✅ {len(self.subjects)} sujets créés")
    
    async def generate_ideas(self):
        """Génère des idées pour chaque sujet"""
        print("💡 Génération des idées...")
        
        total_ideas = 0
        
        for subject in self.subjects:
            # Récupérer les invités assignés au sujet
            subject_users = [u for u in self.users if str(u.id) in subject.users_ids]
            
            if not subject_users:
                continue
            
            # Générer 3-8 idées par sujet
            nb_ideas = random.randint(3, 8)
            subject_ideas_data = self.idees_exemples.get(subject.name, [])
            
            for i in range(nb_ideas):
                author = random.choice(subject_users)
                
                # Utiliser les idées prédéfinies ou en générer
                if i < len(subject_ideas_data):
                    idea_data = subject_ideas_data[i]
                    title = idea_data["title"]
                    description = idea_data["description"]
                else:
                    title = f"Idée #{i+1} pour {subject.name[:30]}..."
                    description = f"Description détaillée de l'idée #{i+1} proposée par {author.prenom} {author.nom}."
                
                # Date de création aléatoire dans les 30 derniers jours
                created_at = datetime.now() - timedelta(
                    days=random.randint(1, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                idea = Idea(
                    subject_id=str(subject.id),
                    user_id=str(author.id),
                    title=title,
                    description=description,
                    created_at=created_at,
                    votes=[]
                )
                
                await Database.engine.save(idea)
                self.ideas.append(idea)
                total_ideas += 1
        
        print(f"✅ {total_ideas} idées créées")
    
    async def generate_votes(self):
        """Génère des votes aléatoires sur les idées"""
        print("🗳️ Génération des votes...")
        
        total_votes = 0
        
        for idea in self.ideas:
            # Récupérer le sujet et ses invités
            subject = next(s for s in self.subjects if str(s.id) == idea.subject_id)
            subject_users = [u for u in self.users if str(u.id) in subject.users_ids]
            
            # L'auteur ne peut pas voter pour sa propre idée
            eligible_voters = [u for u in subject_users if str(u.id) != idea.user_id]
            
            if not eligible_voters:
                continue
            
            # 20-70% des invités votent pour chaque idée
            vote_ratio = random.uniform(0.2, 0.7)
            nb_voters = int(len(eligible_voters) * vote_ratio)
            
            if nb_voters > 0:
                voters = random.sample(eligible_voters, nb_voters)
                idea.votes = [str(v.id) for v in voters]
                await Database.engine.save(idea)
                total_votes += len(voters)
        
        print(f"✅ {total_votes} votes générés")
    
    async def generate_activity_logs(self):
        """Génère des logs d'activité"""
        print("📝 Génération des logs d'activité...")
        
        actions_possibles = [
            "activate_emission", "deactivate_emission", "activate_vote", 
            "close_vote", "abandon_vote", "edit_idea", "add_manager"
        ]
        
        total_logs = 0
        
        for subject in self.subjects:
            gestionnaires = [u for u in self.users if str(u.id) in subject.gestionnaires_ids]
            
            # Générer 5-15 activités par sujet
            nb_activities = random.randint(5, 15)
            
            for _ in range(nb_activities):
                actor = random.choice(gestionnaires) if gestionnaires else self.users[0]
                action = random.choice(actions_possibles)
                
                # Date aléatoire dans les 60 derniers jours
                timestamp = datetime.now() - timedelta(
                    days=random.randint(1, 60),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                # Description selon l'action
                descriptions = {
                    "activate_emission": f"Activation de l'émission d'idées pour le sujet '{subject.name}'",
                    "deactivate_emission": f"Désactivation de l'émission d'idées pour le sujet '{subject.name}'",
                    "activate_vote": f"Activation de la session de vote pour le sujet '{subject.name}'",
                    "close_vote": f"Clôture de la session de vote pour le sujet '{subject.name}'",
                    "abandon_vote": f"Abandon de la session de vote pour le sujet '{subject.name}'",
                    "edit_idea": f"Modification d'une idée par le gestionnaire",
                    "add_manager": f"Ajout d'un gestionnaire au sujet '{subject.name}'"
                }
                
                activity = ActivityLog(
                    action=action,
                    subject_id=str(subject.id),
                    user_id=str(actor.id),
                    user_email=actor.email,
                    user_name=f"{actor.prenom} {actor.nom}",
                    description=descriptions.get(action, f"Action {action}"),
                    details=f"Action effectuée par {actor.prenom} {actor.nom}",
                    timestamp=timestamp,
                    ip_address=f"192.168.1.{random.randint(10, 200)}"
                )
                
                await Database.engine.save(activity)
                total_logs += 1
        
        print(f"✅ {total_logs} logs d'activité générés")
    
    async def generate_demo_data(self, nb_users: int = 25, clear_existing: bool = True):
        """Génère toutes les données de démonstration"""
        print("🚀 Génération des données de démonstration pour Idea Box")
        print("=" * 60)
        
        await self.init_database()
        
        if clear_existing:
            confirm = input("⚠️ Voulez-vous supprimer toutes les données existantes ? (oui/non): ")
            if confirm.lower() in ['oui', 'o', 'yes', 'y']:
                await self.clear_existing_data()
            else:
                print("❌ Génération annulée")
                return
        
        try:
            await self.generate_users(nb_users)
            await self.generate_subjects()
            await self.generate_ideas()
            await self.generate_votes()
            await self.generate_activity_logs()
            
            print("\n" + "=" * 60)
            print("🎉 Génération terminée avec succès !")
            print("\n📊 Résumé des données générées :")
            print(f"   👥 Utilisateurs: {len(self.users)}")
            print(f"   📋 Sujets: {len(self.subjects)}")
            print(f"   💡 Idées: {len(self.ideas)}")
            print(f"   📝 Logs: {total_logs if 'total_logs' in locals() else '?'}")
            print("\n🔑 Comptes de connexion :")
            print("   Super Admin - admin@example.com / admin123")
            print("   Gestionnaires et Invités - [email] / demo123")
            print("\n🌐 Accédez à l'application : http://localhost:8000")
            
        except Exception as e:
            print(f"❌ Erreur lors de la génération : {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Point d'entrée principal"""
    generator = DemoDataGenerator()
    
    # Paramètres par défaut
    nb_users = 25
    
    # Gestion des arguments de ligne de commande
    if len(sys.argv) > 1:
        try:
            nb_users = int(sys.argv[1])
        except ValueError:
            print("❌ Le nombre d'utilisateurs doit être un entier")
            return
    
    await generator.generate_demo_data(nb_users=nb_users)


if __name__ == "__main__":
    asyncio.run(main())
