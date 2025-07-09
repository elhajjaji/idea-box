#!/usr/bin/env python3
"""
Génération de données de démonstration pour l'application Boîte à Idées
Version avec nouveau modèle de votation (SubjectState, Votation, Vote)
"""

import asyncio
from datetime import datetime, timedelta
from src.services.database import Database
from src.models.user import User
from src.models.subject import Subject
from src.models.subject_state import SubjectState
from src.models.idea import Idea
from src.models.votation import Votation
from src.models.vote import Vote
from src.models.activity_log import ActivityLog
from src.models.organization import Organization
from src.services.auth_service import get_password_hash


async def create_demo_data():
    """Créer des données de démonstration complètes"""
    
    print("🚀 Génération des données de démonstration...")
    
    # 0. Initialiser la connexion à la base de données
    print("🔌 Connexion à la base de données...")
    await Database.connect()
    
    # 1. Supprimer toutes les données existantes
    print("🗑️ Suppression des données existantes...")
    await Database.engine.get_collection(User).delete_many({})
    await Database.engine.get_collection(Subject).delete_many({})
    await Database.engine.get_collection(SubjectState).delete_many({})
    await Database.engine.get_collection(Idea).delete_many({})
    await Database.engine.get_collection(Votation).delete_many({})
    await Database.engine.get_collection(Vote).delete_many({})
    await Database.engine.get_collection(ActivityLog).delete_many({})
    await Database.engine.get_collection(Organization).delete_many({})
    
    # 2. Créer l'organisation
    print("🏢 Création de l'organisation...")
    organization = Organization(
        name="TechCorp Innovation",
        description="Leader dans le développement de solutions technologiques innovantes",
        website="https://techcorp-innovation.fr",
        email="contact@techcorp-innovation.fr",
        phone="+33 1 23 45 67 89",
        address="123 Avenue de l'Innovation, 75001 Paris",
        primary_color="#3B82F6",
        secondary_color="#EF4444",
        accent_color="#10B981",
        logo_filename="logo_techcorp.png"
    )
    await Database.engine.save(organization)
    
    # 3. Créer les utilisateurs
    print("👥 Création des utilisateurs...")
    
    # Super Admin
    superadmin = User(
        email="admin@techcorp-innovation.fr",
        nom="Dubois",
        prenom="Marie",
        pwd=get_password_hash("admin123"),
        roles=["superadmin"]
    )
    await Database.engine.save(superadmin)
    
    # Gestionnaires
    gestionnaire1 = User(
        email="pierre.martin@techcorp-innovation.fr",
        nom="Martin",
        prenom="Pierre",
        pwd=get_password_hash("gest123"),
        roles=["gestionnaire"]
    )
    
    gestionnaire2 = User(
        email="sophie.laurent@techcorp-innovation.fr",
        nom="Laurent",
        prenom="Sophie",
        pwd=get_password_hash("gest123"),
        roles=["gestionnaire"]
    )
    
    await Database.engine.save(gestionnaire1)
    await Database.engine.save(gestionnaire2)
    
    # Utilisateurs invités
    users_data = [
        ("jean.dupont@techcorp-innovation.fr", "Dupont", "Jean"),
        ("alice.bernard@techcorp-innovation.fr", "Bernard", "Alice"),
        ("thomas.petit@techcorp-innovation.fr", "Petit", "Thomas"),
        ("julie.moreau@techcorp-innovation.fr", "Moreau", "Julie"),
        ("david.garcia@techcorp-innovation.fr", "Garcia", "David"),
        ("emma.roux@techcorp-innovation.fr", "Roux", "Emma"),
        ("lucas.blanc@techcorp-innovation.fr", "Blanc", "Lucas"),
        ("chloe.simon@techcorp-innovation.fr", "Simon", "Chloé")
    ]
    
    users = []
    for email, nom, prenom in users_data:
        user = User(
            email=email,
            nom=nom,
            prenom=prenom,
            pwd=get_password_hash("user123"),
            roles=["user"]
        )
        await Database.engine.save(user)
        users.append(user)
    
    # 4. Créer les sujets
    print("📋 Création des sujets...")
    
    # Sujet 1 - Télétravail (géré par gestionnaire1)
    subject1 = Subject(
        name="Amélioration du télétravail",
        description="Comment optimiser l'organisation du télétravail dans notre entreprise ?",
        superadmin_id=str(superadmin.id),
        gestionnaires_ids=[str(gestionnaire1.id)],
        users_ids=[str(u.id) for u in users[:4]],  # 4 premiers utilisateurs
        emission_active=True
    )
    await Database.engine.save(subject1)
    
    # État d'émission pour sujet1
    subject1_state = SubjectState(
        subject_id=str(subject1.id),
        is_activated=True
    )
    await Database.engine.save(subject1_state)
    
    # Sujet 2 - Innovation (géré par gestionnaire2)
    subject2 = Subject(
        name="Innovations technologiques",
        description="Quelles technologies émergentes devons-nous adopter en 2025 ?",
        superadmin_id=str(superadmin.id),
        gestionnaires_ids=[str(gestionnaire2.id)],
        users_ids=[str(u.id) for u in users[2:6]],  # utilisateurs 3-6
        emission_active=False
    )
    await Database.engine.save(subject2)
    
    # État d'émission pour sujet2 (désactivé)
    subject2_state = SubjectState(
        subject_id=str(subject2.id),
        is_activated=False
    )
    await Database.engine.save(subject2_state)
    
    # Sujet 3 - Bien-être (géré par les deux gestionnaires)
    subject3 = Subject(
        name="Bien-être au travail",
        description="Initiatives pour améliorer la qualité de vie au bureau",
        superadmin_id=str(superadmin.id),
        gestionnaires_ids=[str(gestionnaire1.id), str(gestionnaire2.id)],
        users_ids=[str(u.id) for u in users[4:]],  # 4 derniers utilisateurs
        emission_active=False
    )
    await Database.engine.save(subject3)
    
    # État d'émission pour sujet3
    subject3_state = SubjectState(
        subject_id=str(subject3.id),
        is_activated=False
    )
    await Database.engine.save(subject3_state)
    
    # 5. Créer les idées
    print("💡 Création des idées...")
    
    # Idées pour le sujet télétravail
    ideas_subject1 = [
        ("Espaces de coworking partagés", "Créer des espaces de coworking dans différents quartiers pour les employés", users[0]),
        ("Outils de collaboration améliorés", "Investir dans de meilleurs outils de visioconférence et collaboration", users[1]),
        ("Formation au télétravail", "Programme de formation pour optimiser la productivité en télétravail", users[2]),
        ("Flex office hybride", "Système de réservation de bureaux pour travail hybride", users[3])
    ]
    
    ideas1 = []
    for title, description, user in ideas_subject1:
        idea = Idea(
            subject_id=str(subject1.id),
            user_id=str(user.id),
            title=title,
            description=description,
            created_at=datetime.now() - timedelta(days=7, hours=hash(title) % 24)
        )
        await Database.engine.save(idea)
        ideas1.append(idea)
    
    # Idées pour le sujet innovation
    ideas_subject2 = [
        ("Intelligence Artificielle", "Intégrer l'IA dans nos processus de développement", users[2]),
        ("Blockchain", "Explorer les applications blockchain pour nos services", users[3]),
        ("IoT et capteurs", "Déployer des capteurs IoT pour optimiser les espaces de travail", users[4]),
        ("Réalité augmentée", "Utiliser la RA pour la formation et la maintenance", users[5]),
        ("Cloud natif", "Migration vers une architecture cloud-native", users[2])
    ]
    
    ideas2 = []
    for title, description, user in ideas_subject2:
        idea = Idea(
            subject_id=str(subject2.id),
            user_id=str(user.id),
            title=title,
            description=description,
            created_at=datetime.now() - timedelta(days=5, hours=hash(title) % 24)
        )
        await Database.engine.save(idea)
        ideas2.append(idea)
    
    # Idées pour le sujet bien-être
    ideas_subject3 = [
        ("Salle de sport", "Aménager une salle de sport dans l'entreprise", users[4]),
        ("Cours de yoga", "Organiser des cours de yoga pendant la pause déjeuner", users[5]),
        ("Jardins partagés", "Créer des espaces verts et jardins partagés", users[6]),
        ("Téléconsultation médicale", "Service de téléconsultation avec des médecins", users[7])
    ]
    
    ideas3 = []
    for title, description, user in ideas_subject3:
        idea = Idea(
            subject_id=str(subject3.id),
            user_id=str(user.id),
            title=title,
            description=description,
            created_at=datetime.now() - timedelta(days=3, hours=hash(title) % 24)
        )
        await Database.engine.save(idea)
        ideas3.append(idea)
    
    # 6. Créer les votations
    print("🗳️ Création des votations...")
    
    # Votation 1 - Sujet innovation (fermée avec résultats)
    votation1 = Votation(
        subject_id=str(subject2.id),
        votation_name="Vote priorités tech 2025",
        ideas_list=[str(idea.id) for idea in ideas2[:3]],  # 3 premières idées
        vote_limit=2,
        is_activated=False,
        allow_multiple_active=False,
        created_at=datetime.now() - timedelta(days=4),
        activated_at=datetime.now() - timedelta(days=3),
        closed_at=datetime.now() - timedelta(days=1)
    )
    await Database.engine.save(votation1)
    
    # Votation 2 - Sujet bien-être (active)
    votation2 = Votation(
        subject_id=str(subject3.id),
        votation_name="Initiatives bien-être prioritaires",
        ideas_list=[str(idea.id) for idea in ideas3],  # Toutes les idées
        vote_limit=3,
        is_activated=True,
        allow_multiple_active=False,
        created_at=datetime.now() - timedelta(days=2),
        activated_at=datetime.now() - timedelta(days=1),
        closed_at=None
    )
    await Database.engine.save(votation2)
    
    # Votation 3 - Sujet innovation (créée, pas encore activée)
    votation3 = Votation(
        subject_id=str(subject2.id),
        votation_name="Technologies émergentes - Phase 2",
        ideas_list=[str(idea.id) for idea in ideas2[2:]],  # 3 dernières idées
        vote_limit=1,
        is_activated=False,
        allow_multiple_active=True,  # Autorise multiple
        created_at=datetime.now() - timedelta(hours=6),
        activated_at=None,
        closed_at=None
    )
    await Database.engine.save(votation3)
    
    # 7. Créer les votes
    print("✅ Création des votes...")
    
    # Votes pour la votation1 (fermée)
    vote_patterns1 = [
        (ideas2[0], users[2:5]),  # IA: 3 votes
        (ideas2[1], users[3:6]),  # Blockchain: 3 votes
        (ideas2[2], users[2:4])   # IoT: 2 votes
    ]
    
    for idea, voters in vote_patterns1:
        for user in voters:
            if str(user.id) in subject2.users_ids:  # Vérifier accès au sujet
                vote = Vote(
                    votation_id=str(votation1.id),
                    idea_id=str(idea.id),
                    user_id=str(user.id),
                    created_at=datetime.now() - timedelta(days=2, minutes=hash(str(user.id)) % 120)
                )
                await Database.engine.save(vote)
    
    # Votes pour la votation2 (active)
    vote_patterns2 = [
        (ideas3[0], users[4:7]),  # Salle de sport: 3 votes
        (ideas3[1], users[5:8]),  # Yoga: 3 votes
        (ideas3[2], users[4:6]),  # Jardins: 2 votes
        (ideas3[3], users[6:8])   # Téléconsultation: 2 votes
    ]
    
    for idea, voters in vote_patterns2:
        for user in voters:
            if str(user.id) in subject3.users_ids:  # Vérifier accès au sujet
                vote = Vote(
                    votation_id=str(votation2.id),
                    idea_id=str(idea.id),
                    user_id=str(user.id),
                    created_at=datetime.now() - timedelta(hours=hash(str(user.id)) % 12)
                )
                await Database.engine.save(vote)
    
    # 8. Créer les logs d'activité
    print("📝 Création des logs d'activité...")
    
    activity_logs = [
        # Création des sujets
        ActivityLog(
            action="create_subject",
            subject_id=str(subject1.id),
            user_id=str(superadmin.id),
            user_email=superadmin.email,
            user_name=f"{superadmin.prenom} {superadmin.nom}",
            description=f"Création du sujet '{subject1.name}'",
            details="Sujet créé avec émission d'idées activée",
            timestamp=datetime.now() - timedelta(days=8)
        ),
        
        # Activation émission sujet1
        ActivityLog(
            action="activate_subject_emission",
            subject_id=str(subject1.id),
            user_id=str(gestionnaire1.id),
            user_email=gestionnaire1.email,
            user_name=f"{gestionnaire1.prenom} {gestionnaire1.nom}",
            description=f"Activation de l'émission d'idées pour '{subject1.name}'",
            details="Les utilisateurs peuvent maintenant soumettre des idées",
            timestamp=datetime.now() - timedelta(days=7)
        ),
        
        # Création votation1
        ActivityLog(
            action="create_votation",
            subject_id=str(subject2.id),
            user_id=str(gestionnaire2.id),
            user_email=gestionnaire2.email,
            user_name=f"{gestionnaire2.prenom} {gestionnaire2.nom}",
            description=f"Création de la votation '{votation1.votation_name}'",
            details=f"3 idées sélectionnées, limite de {votation1.vote_limit} votes par utilisateur",
            timestamp=datetime.now() - timedelta(days=4)
        ),
        
        # Activation votation1
        ActivityLog(
            action="activate_votation",
            subject_id=str(subject2.id),
            user_id=str(gestionnaire2.id),
            user_email=gestionnaire2.email,
            user_name=f"{gestionnaire2.prenom} {gestionnaire2.nom}",
            description=f"Activation de la votation '{votation1.votation_name}'",
            details="Session de vote ouverte aux utilisateurs",
            timestamp=datetime.now() - timedelta(days=3)
        ),
        
        # Clôture votation1
        ActivityLog(
            action="close_votation",
            subject_id=str(subject2.id),
            user_id=str(gestionnaire2.id),
            user_email=gestionnaire2.email,
            user_name=f"{gestionnaire2.prenom} {gestionnaire2.nom}",
            description=f"Clôture de la votation '{votation1.votation_name}'",
            details="8 votes reçus, résultats disponibles",
            timestamp=datetime.now() - timedelta(days=1)
        ),
        
        # Activation votation2
        ActivityLog(
            action="activate_votation",
            subject_id=str(subject3.id),
            user_id=str(gestionnaire1.id),
            user_email=gestionnaire1.email,
            user_name=f"{gestionnaire1.prenom} {gestionnaire1.nom}",
            description=f"Activation de la votation '{votation2.votation_name}'",
            details="4 idées disponibles au vote",
            timestamp=datetime.now() - timedelta(days=1)
        )
    ]
    
    for log in activity_logs:
        await Database.engine.save(log)
    
    print("✅ Données de démonstration créées avec succès !")
    print(f"📊 Résumé:")
    print(f"   - 1 organisation: {organization.name}")
    print(f"   - 11 utilisateurs (1 superadmin, 2 gestionnaires, 8 invités)")
    print(f"   - 3 sujets avec états d'émission")
    print(f"   - 13 idées réparties sur les 3 sujets")
    print(f"   - 3 votations (1 fermée, 1 active, 1 créée)")
    print(f"   - {len([v for v in vote_patterns1 for u in v[1]]) + len([v for v in vote_patterns2 for u in v[1]])} votes")
    print(f"   - {len(activity_logs)} logs d'activité")
    print()
    print("🔑 Comptes de test:")
    print("   Superadmin: admin@techcorp-innovation.fr / admin123")
    print("   Gestionnaire 1: pierre.martin@techcorp-innovation.fr / gest123")
    print("   Gestionnaire 2: sophie.laurent@techcorp-innovation.fr / gest123")
    print("   Invités: [prenom].[nom]@techcorp-innovation.fr / user123")


if __name__ == "__main__":
    asyncio.run(create_demo_data())
