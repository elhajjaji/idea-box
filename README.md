# Idea Box - Plateforme Collaborative de Gestion d'Idées

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-4.4+-green.svg)](https://www.mongodb.com/)

## 📋 Description

**Idea Box** est une plateforme collaborative moderne conçue pour faciliter la collecte, la gestion et l'évaluation d'idées au sein d'une organisation. Elle permet aux équipes de soumettre des propositions, de voter pour les meilleures idées et de suivre leur progression grâce à un système de gestion par rôles.

## ✨ Fonctionnalités principales

### 🎯 Pour les **Invités** (utilisateurs standard)
- ✍️ Soumettre des idées sur les sujets assignés
- 🗳️ Voter pour les idées (pendant les sessions de vote)
- 📊 Consulter ses propres statistiques et idées
- 👀 Visualiser les résultats des votes

### 👥 Pour les **Gestionnaires**
- 🎛️ Gérer les sujets assignés (activation émission/vote)
- ✏️ Modifier et supprimer les idées de leurs sujets
- 👤 Assigner des invités aux sujets
- 📈 Accéder aux tableaux de bord avec métriques avancées
- 🔄 Promouvoir des invités au rôle gestionnaire
- 📋 Consulter l'historique des activités

### 🔧 Pour les **Super Administrateurs**
- 🏗️ Créer, modifier et supprimer des sujets
- 👥 Gérer tous les utilisateurs (création, modification, suppression)
- 🎭 Assigner les rôles et permissions
- 📊 Accès complet aux statistiques globales
- 📤 Import/export d'utilisateurs en masse

## 🏗️ Architecture technique

### Stack technologique
- **Backend** : FastAPI (Python 3.9+)
- **Base de données** : MongoDB avec ODMantic (ORM)
- **Frontend** : Jinja2 Templates + Bootstrap 5
- **Authentification** : JWT + bcrypt
- **Containerisation** : Docker & Docker Compose

### Structure du projet
```
idea-box/
├── src/
│   ├── main.py                 # Point d'entrée de l'application
│   ├── models/                 # Modèles de données (User, Subject, Idea, ActivityLog)
│   ├── routes/                 # Routes API par rôle (auth, user, gestionnaire, superadmin)
│   ├── services/               # Logique métier et services
│   ├── templates/              # Templates Jinja2
│   └── utils/                  # Utilitaires (flash messages, etc.)
├── tests/                      # Tests unitaires et d'intégration
├── docker-compose.yml          # Configuration Docker
├── Dockerfile                  # Image Docker de l'application
├── requirements.txt            # Dépendances Python
└── SCHEMA_BASE_DONNEES.md     # Documentation technique de la BDD
```

## 🚀 Installation et démarrage

### Prérequis
- Docker et Docker Compose installés
- Git

### 1. Cloner le projet
```bash
git clone <repository-url>
cd idea-box
```

### 2. Démarrer avec Docker Compose
```bash
docker-compose up -d
```

Cette commande va :
- Créer et démarrer le conteneur MongoDB
- Construire et démarrer l'application FastAPI
- Exposer l'application sur http://localhost:8000

### 3. Initialiser les données (optionnel)
```bash
# Créer un super administrateur
python init_admin.py
```

## 🔑 Comptes par défaut

Après l'initialisation, vous pouvez vous connecter avec :

**Super Administrateur :**
- Email : `admin@example.com`
- Mot de passe : `admin123`

## 📖 Utilisation

### 1. Connexion
Accédez à http://localhost:8000 et connectez-vous avec vos identifiants.

### 2. Création d'un sujet (Super Admin)
1. Aller dans "Gestion des sujets"
2. Cliquer sur "Créer un sujet"
3. Remplir les informations et assigner des gestionnaires

### 3. Gestion des invités (Gestionnaire)
1. Accéder au tableau de bord gestionnaire
2. Gérer les invités assignés aux sujets
3. Activer l'émission d'idées

### 4. Soumission d'idées (Invité)
1. Voir les sujets assignés sur le tableau de bord
2. Cliquer sur "Soumettre une idée"
3. Remplir le formulaire et valider

### 5. Session de vote (Gestionnaire)
1. Désactiver l'émission d'idées
2. Activer la session de vote
3. Les invités peuvent voter pour leurs idées préférées

## 🔧 Configuration

### Variables d'environnement
Créez un fichier `.env` à la racine du projet :

```env
# Base de données
MONGODB_URL=mongodb://mongodb:27017/ideabox

# Sécurité
SECRET_KEY=your-super-secret-jwt-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Application
DEBUG=false
HOST=0.0.0.0
PORT=8000
```

### Configuration MongoDB
Par défaut, MongoDB utilise :
- **Host** : `mongodb` (dans Docker Compose)
- **Port** : `27017`
- **Base de données** : `ideabox`

## 📊 Base de données

Le projet utilise MongoDB avec 4 collections principales :

- **`user`** : Utilisateurs avec rôles et informations personnelles
- **`subjects`** : Sujets/thèmes pour la collecte d'idées
- **`ideas`** : Idées soumises par les utilisateurs
- **`activity_logs`** : Journal d'audit des actions

Pour plus de détails, consultez [SCHEMA_BASE_DONNEES.md](./SCHEMA_BASE_DONNEES.md).

## 🧪 Tests

### Lancer les tests
```bash
# Tests unitaires
python -m pytest tests/ -v

# Tests avec couverture
python -m pytest tests/ --cov=src --cov-report=html
```

### Tests d'intégration
```bash
# Test complet de l'API
python -m pytest tests/test_app.py -v
```

## 🚀 Déploiement en production

### 1. Construction de l'image Docker
```bash
docker build -t ideabox:latest .
```

### 2. Déploiement avec compose
```bash
# Production
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Configuration HTTPS (recommandé)
Ajoutez un reverse proxy (nginx, traefik) pour HTTPS en production.

## 🔐 Sécurité

### Authentification
- Mots de passe hashés avec **bcrypt** (coût : 12)
- Sessions sécurisées avec **JWT**
- Expiration automatique des tokens

### Autorisation
- **RBAC** (Role-Based Access Control)
- Validation des permissions à chaque route
- Isolation des données par sujet/utilisateur

### Audit
- Toutes les actions importantes sont loggées
- Traçabilité complète des modifications
- Conservation des adresses IP

## 📈 Évolutions futures

- [ ] **API REST** complète pour applications mobiles
- [ ] **Notifications** en temps réel
- [ ] **Commentaires** sur les idées
- [ ] **Catégories** d'idées
- [ ] **Fichiers joints** aux idées
- [ ] **Export** des résultats (PDF, Excel)
- [ ] **Intégration SSO** (LDAP, OAuth)

## 🤝 Contribution

### Comment contribuer
1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/amazing-feature`)
3. Commit les changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

### Standards de code
- **PEP 8** pour Python
- **Type hints** obligatoires
- **Docstrings** pour toutes les fonctions
- **Tests** pour les nouvelles fonctionnalités

## 🐛 Signaler un bug

Utilisez les [Issues GitHub](../../issues) pour signaler des bugs ou demander des fonctionnalités.

Incluez :
- Description détaillée du problème
- Étapes pour reproduire
- Environnement (OS, version Python, etc.)
- Logs d'erreur si disponibles

## 📄 Licence

Ce projet est sous licence **MIT** - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 📞 Support

- **Documentation** : [SCHEMA_BASE_DONNEES.md](./SCHEMA_BASE_DONNEES.md)
- **Issues** : [GitHub Issues](../../issues)
- **Email** : prof.elhajjaji@gmail.com

---

⭐ **N'hésitez pas à donner une étoile au projet si il vous est utile !**
