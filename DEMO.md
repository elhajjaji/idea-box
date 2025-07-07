# 🎯 Guide de Démonstration - Idea Box

## 📋 Table des matières
1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis et installation](#prérequis-et-installation)
3. [Génération des données de démonstration](#génération-des-données-de-démonstration)
4. [Comptes de démonstration](#comptes-de-démonstration)
5. [Scénarios de démonstration](#scénarios-de-démonstration)
6. [Fonctionnalités par rôle](#fonctionnalités-par-rôle)
7. [Tests recommandés](#tests-recommandés)
8. [Dépannage](#dépannage)

---

## 🎯 Vue d'ensemble

**Idea Box** est une plateforme collaborative de gestion d'idées qui permet aux organisations de:
- Collecter et organiser les idées par sujets
- Gérer des sessions d'émission et de vote
- Suivre l'engagement et les statistiques
- Administrer les utilisateurs et leurs rôles

### Architecture des rôles
- **👑 Super Admin** : Administration complète de la plateforme
- **🔧 Gestionnaire** : Gestion des sujets assignés et de leurs participants
- **💡 Invité** : Participation aux sujets (émission d'idées et votes)

---

## 🚀 Prérequis et installation

### 1. Prérequis système
- **Docker** et **Docker Compose** installés
- Port **8000** disponible sur votre machine
- Au moins **2 GB** de RAM disponible

### 2. Déploiement avec Docker
```bash
# Cloner le projet
git clone <repository-url>
cd idea-box

# Démarrer l'application complète avec Docker Compose
docker-compose up -d

# Vérifier que tous les services sont démarrés
docker-compose ps
```

### 3. Services déployés
- **Application FastAPI** : http://localhost:8000
- **Base de données MongoDB** : Port 27017 (interne)
- **Interface d'administration** : Accessible via l'application

> 💡 **Note** : L'application utilise entièrement Docker pour le déploiement. Aucune installation Python locale n'est requise.

---

## 🐳 Architecture Docker

**Idea Box** utilise Docker pour le déploiement, garantissant un environnement cohérent et simplifiant l'installation.

### Services Docker
- **app** : Application FastAPI (Python 3.9+)
- **mongodb** : Base de données MongoDB 5.0
- **Réseau** : Communication interne sécurisée
- **Volumes** : Persistance des données

### Avantages
- ✅ **Installation simplifiée** : Une seule commande pour tout démarrer
- ✅ **Environnement isolé** : Pas de conflit avec votre système
- ✅ **Portabilité** : Fonctionne sur Windows, Mac, Linux
- ✅ **Consistance** : Même environnement en dev/prod
- ✅ **Scalabilité** : Facilite la montée en charge

---

## 🎲 Génération des données de démonstration

### Commande avec Docker
```bash
# Générer les données de démonstration (dans le conteneur)
docker-compose exec app python generate_demo_data.py
```

### Options avancées
```bash
# Générer 50 utilisateurs au lieu de 25 par défaut
docker-compose exec app python generate_demo_data.py 50
```

### Alternative locale (si Python installé)
```bash
# Si vous avez Python installé localement
python generate_demo_data.py
python generate_demo_data.py 50
```

### ⚠️ ATTENTION
Le script supprime **toutes les données existantes** avant de générer les nouvelles données. Confirmez avec `oui` quand demandé.

### Données générées
- **👥 25 utilisateurs** (1 super admin, ~3 gestionnaires, ~21 invités)
- **📋 8 sujets thématiques** avec descriptions réalistes
- **💡 30-60 idées** réparties sur les sujets
- **🗳️ Votes aléatoires** (20-70% de participation par idée)
- **📝 40-120 logs d'activité** historiques

---

## � Comptes de démonstration

### Super Admin
- **Email** : `admin@example.com`
- **Mot de passe** : `admin123`
- **Accès** : Toutes les fonctionnalités

### Gestionnaires (exemples)
- **Email** : `alice.martin@example.com`
- **Mot de passe** : `demo123`
- **Accès** : Gestion des sujets assignés

---

## 🎬 Scénarios de démonstration

### 🚀 Scénario 1 : Découverte rapide (5 minutes)

#### Étape 1 : Connexion en tant qu'invité
1. Connectez-vous avec `bob.bernard@example.com` / `demo123`
2. Explorez le **tableau de bord invité** :
   - Visualisez les métriques personnelles
   - Observez les graphiques d'engagement
3. Naviguez vers **"Mes Sujets"** :
   - Consultez les sujets auxquels vous participez
   - Explorez les idées existantes

#### Étape 2 : Émission d'une idée
1. Cliquez sur un sujet où l'émission est active
2. Proposez une nouvelle idée :
   - **Titre** : "Amélioration de l'éclairage naturel"
   - **Description** : "Installer des puits de lumière pour améliorer l'éclairage naturel et réduire la consommation électrique"
3. Validez et observez l'idée ajoutée

#### Étape 3 : Participation aux votes
1. Accédez à un sujet en phase de vote
2. Votez pour vos idées préférées
3. Observez la mise à jour des compteurs

### 🔧 Scénario 2 : Gestion avancée (10 minutes)

#### Étape 1 : Connexion gestionnaire
1. Connectez-vous avec `alice.martin@example.com` / `demo123`
2. Explorez le **tableau de bord gestionnaire** :
   - Analysez les statistiques détaillées
   - Consultez les graphiques de performance

#### Étape 2 : Gestion d'un sujet
1. Accédez à **"Gestion des Sujets"**
2. Sélectionnez un sujet à gérer :
   - **Basculer** entre émission et vote
   - **Modifier** les paramètres du sujet
   - **Gérer** les participants

#### Étape 3 : Modération des idées
1. Allez dans **"Édition en Lot"**
2. Sélectionnez plusieurs idées
3. Testez les actions groupées :
   - Modification des titres
   - Mise à jour des descriptions
   - Suppression d'idées

#### Étape 4 : Suivi des activités
1. Consultez **"Historique & Logs"**
2. Filtrez par type d'action
3. Analysez l'activité récente

#### Étape 5 : Gestion des gestionnaires
1. Accédez à **"Gestionnaires"**
2. Promouvez un invité au rôle de gestionnaire
3. Vérifiez la mise à jour des permissions

### 👑 Scénario 3 : Administration complète (15 minutes)

#### Étape 1 : Connexion super admin
1. Connectez-vous avec `admin@example.com` / `admin123`
2. Explorez le **tableau de bord super admin** :
   - Vue globale de la plateforme
   - Métriques de tous les sujets
   - Graphiques de tendances

#### Étape 2 : Gestion des utilisateurs
1. Accédez à **"Gestion des Utilisateurs"**
2. **Créer** un nouvel utilisateur :
   - Remplissez les informations
   - Assignez des rôles
   - Sélectionnez des sujets
3. **Modifier** un utilisateur existant :
   - Changez les rôles
   - Mettez à jour les sujets assignés
4. Testez la validation (gestionnaire sans sujet)

#### Étape 3 : Administration des sujets
1. Naviguez vers **"Gestion des Sujets"**
2. **Créer** un nouveau sujet :
   - Définissez nom et description
   - Assignez gestionnaires et invités
3. **Modifier** un sujet existant :
   - Changez les paramètres
   - Réassignez les participants

#### Étape 4 : Import en masse
1. Accédez à **"Import d'Utilisateurs"**
2. Téléchargez le modèle CSV
3. Préparez un fichier d'import test
4. Effectuez l'import et vérifiez les résultats

---

## 🔍 Fonctionnalités par rôle

### 💡 Invité
| Fonctionnalité | Description | Page |
|----------------|-------------|------|
| **Tableau de bord** | Métriques personnelles et graphiques | `/user/dashboard` |
| **Mes Sujets** | Liste des sujets assignés | `/user/subjects` |
| **Émission d'idées** | Proposer de nouvelles idées | `/user/subjects/{id}/ideas` |
| **Participation aux votes** | Voter pour les idées préférées | `/user/vote/{id}` |
| **Mes Idées** | Consulter ses propres idées | `/user/my-ideas` |
| **Profil** | Modifier ses informations | `/profile` |

### 🔧 Gestionnaire
| Fonctionnalité | Description | Page |
|----------------|-------------|------|
| **Tableau de bord avancé** | Statistiques détaillées des sujets | `/gestionnaire/dashboard` |
| **Gestion des sujets** | Administration des sujets assignés | `/gestionnaire/subjects` |
| **Gestion des participants** | Administration des invités par sujet | `/gestionnaire/subject/{id}/manage` |
| **Édition en lot** | Modification groupée des idées | `/gestionnaire/bulk-ideas` |
| **Historique & Logs** | Suivi des activités | `/gestionnaire/logs` |
| **Gestion des gestionnaires** | Promotion d'invités | `/gestionnaire/managers` |
| **États des sujets** | Basculement émission/vote | Intégré aux pages |

### 👑 Super Admin
| Fonctionnalité | Description | Page |
|----------------|-------------|------|
| **Tableau de bord global** | Vue d'ensemble de la plateforme | `/superadmin/dashboard` |
| **Gestion des utilisateurs** | CRUD complet des utilisateurs | `/superadmin/users` |
| **Gestion des sujets** | CRUD complet des sujets | `/superadmin/subjects` |
| **Import d'utilisateurs** | Import CSV en masse | `/superadmin/import-users` |
| **Paramètres système** | Configuration globale | `/superadmin/settings` |

> 💡 **Astuce** : Tous les comptes utilisent le mot de passe `demo123` sauf le super admin

### Invités/Utilisateurs
- **Email** : `[prenom].[nom]@example.com`
- **Mot de passe** : `demo123`
- **Rôles** : Soumission d'idées et votes

## 🎭 Scénarios de Démonstration

### Scénario 1 : Découverte Super Admin
1. **Connexion** avec `admin@example.com` / `admin123`
2. **Dashboard** : Vue d'ensemble des statistiques
3. **Gestion des utilisateurs** : Consulter la liste des utilisateurs
4. **Création de sujet** : Créer un nouveau sujet d'idées
5. **Attribution des rôles** : Assigner des gestionnaires
6. **Configuration** : Paramètres de l'application

### Scénario 2 : Rôle Gestionnaire
1. **Connexion** avec un compte gestionnaire
2. **Sujets assignés** : Voir les sujets sous votre responsabilité
3. **Gestion des phases** :
   - Activer l'émission d'idées
   - Consulter les idées soumises
   - Lancer une session de vote
   - Analyser les résultats
4. **Modération** : Éditer ou supprimer des idées inappropriées
5. **Rapports** : Consulter l'historique et les statistiques

### Scénario 3 : Utilisateur/Invité
1. **Connexion** avec un compte invité
2. **Mes sujets** : Voir les sujets auxquels vous participez
3. **Soumission d'idées** : Proposer de nouvelles idées
4. **Consultation** : Parcourir les idées des autres participants
5. **Vote** : Participer aux sessions de vote actives
6. **Suivi** : Consulter vos idées et leur réception

## 📊 Données de Démonstration

### Sujets Pré-créés
- **Amélioration de l'environnement de travail** (5 idées)
- **Innovation technologique** (5 idées)
- **Processus de recrutement** (4 idées)
- **Formation et développement professionnel** (4 idées)
- **Communication interne** (4 idées)
- **Responsabilité sociale et environnementale** (4 idées)
- **Amélioration des processus métier** (variables)
- **Événements et activités d'équipe** (variables)

---

## ✅ Tests recommandés

### Tests fonctionnels de base

#### 🔐 Authentification
- [ ] Connexion avec chaque type de compte
- [ ] Redirection selon le rôle après connexion
- [ ] Déconnexion et sécurité des sessions
- [ ] Gestion des erreurs de connexion

#### 💡 Gestion des idées
- [ ] Création d'idée (émission active)
- [ ] Impossibilité de créer (émission inactive)
- [ ] Vote sur les idées (vote actif)
- [ ] Impossibilité de voter (vote inactif)
- [ ] Un utilisateur ne peut voter qu'une fois

#### 🔧 Workflow gestionnaire
- [ ] Basculement émission → vote
- [ ] Clôture et abandon de vote
- [ ] Modification d'idées existantes
- [ ] Gestion des participants
- [ ] Promotion d'invités

#### 👑 Administration
- [ ] Création d'utilisateurs avec validation
- [ ] Import CSV avec gestion d'erreurs
- [ ] Création et modification de sujets
- [ ] Assignation de rôles et sujets

### Tests d'interface utilisateur

#### 📱 Responsive Design
- [ ] Navigation mobile
- [ ] Tableaux adaptatifs
- [ ] Formulaires sur petit écran
- [ ] Graphiques redimensionnables

#### 🎨 Cohérence visuelle
- [ ] Menus et sidebars cohérents
- [ ] Messages flash visibles
- [ ] Icônes et couleurs uniformes
- [ ] Chargement et états d'attente

#### ♿ Accessibilité
- [ ] Navigation au clavier
- [ ] Contrastes suffisants
- [ ] Textes alternatifs
- [ ] Structure sémantique

### Tests de performance

#### 📊 Chargement des données
- [ ] Temps de chargement des tableaux de bord
- [ ] Réactivité des graphiques
- [ ] Pagination des listes longues
- [ ] Recherche et filtres

#### 🚀 Gestion de charge
- [ ] Comportement avec 100+ utilisateurs
- [ ] Performance avec 1000+ idées
- [ ] Gestion de multiples sessions

---

## 🛠️ Dépannage

### Problèmes courants

#### ❌ Erreur de connexion à la base de données
```
Erreur : ConnectionFailure
```
**Solution** :
1. Vérifiez que tous les services Docker sont actifs : `docker-compose ps`
2. Redémarrez les services : `docker-compose restart`
3. Vérifiez les logs MongoDB : `docker-compose logs mongodb`
4. Si problème persistant : `docker-compose down && docker-compose up -d`

#### ❌ Échec de génération des données
```
Erreur lors de la génération : [détails]
```
**Solution** :
1. Vérifiez que l'application est démarrée : `docker-compose ps`
2. Accédez au conteneur : `docker-compose exec app bash`
3. Relancez manuellement : `python generate_demo_data.py`
4. Si échec : supprimez les volumes et redémarrez

#### ❌ Application inaccessible (localhost:8000)
**Symptômes** : Erreur de connexion, page inaccessible
**Solution** :
1. Vérifiez que le service app est démarré : `docker-compose ps`
2. Vérifiez les logs : `docker-compose logs app`
3. Vérifiez que le port 8000 n'est pas utilisé : `netstat -ano | findstr :8000`
4. Redémarrez le service : `docker-compose restart app`

#### ❌ Problèmes d'affichage
**Symptômes** : Page "sans style", menus manquants
**Solution** :
1. Vérifiez la console développeur (F12)
2. Actualisez le cache (Ctrl+F5)
3. Vérifiez les logs serveur

#### ❌ Erreurs de validation
**Symptômes** : Impossible d'assigner un gestionnaire
**Cause** : Tentative d'assignation sans sujet
**Solution** : Sélectionnez au moins un sujet avant l'assignation

### Réinitialisation complète

```bash
# Arrêter tous les services Docker
docker-compose down

# Supprimer les volumes de données (⚠️ SUPPRIME TOUTES LES DONNÉES)
docker-compose down -v

# Redémarrer l'application
docker-compose up -d

# Attendre que les services démarrent (30-60 secondes)
docker-compose logs -f app

# Regénérer les données de démonstration
docker-compose exec app python generate_demo_data.py
```

### Commandes Docker utiles

```bash
# Voir les logs de l'application
docker-compose logs app

# Voir les logs de MongoDB
docker-compose logs mongodb

# Accéder au shell du conteneur application
docker-compose exec app bash

# Redémarrer uniquement l'application
docker-compose restart app
```

---

## 📞 Support et ressources

### Documentation technique
- **[README.md](README.md)** - Installation et configuration
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Guide de contribution
- **[SCHEMA_BASE_DONNEES.md](SCHEMA_BASE_DONNEES.md)** - Documentation de la base de données

### Liens utiles
- **Application** : http://localhost:8000
- **API Docs** : http://localhost:8000/docs
- **Status des services** : `docker-compose ps`
- **Logs en temps réel** : `docker-compose logs -f`

### Architecture Docker
- **app** : Application FastAPI (Python)
- **mongodb** : Base de données MongoDB
- **Volumes** : Persistance des données MongoDB
- **Réseau** : Communication interne entre services

### Contact
Pour toute question ou problème :
1. Consultez la documentation
2. Vérifiez les issues GitHub
3. Créez une nouvelle issue avec les détails du problème

---

**🎉 Bon voyage dans l'univers d'Idea Box !**

*Cette démonstration vous a plu ? N'hésitez pas à contribuer au projet ou à l'adapter à vos besoins.*

### Données Générées
- **Idées réalistes** avec titres et descriptions détaillées
- **Votes aléatoires** : 20-70% des participants votent par idée
- **Logs d'activité** : Historique des actions des gestionnaires
- **Assignations variables** : 60-80% des invités par sujet

## 🔧 Fonctionnalités à Tester

### Super Admin
- ✅ Création et édition de sujets
- ✅ Gestion des utilisateurs et rôles
- ✅ Importation en masse d'utilisateurs (CSV)
- ✅ Vue d'ensemble des statistiques
- ✅ Configuration des paramètres globaux

### Gestionnaire
- ✅ Activation/désactivation de l'émission d'idées
- ✅ Gestion des sessions de vote
- ✅ Modération du contenu
- ✅ Consultation des rapports et historiques
- ✅ Gestion des participants au sujet

### Utilisateur
- ✅ Soumission d'idées avec titre et description
- ✅ Consultation des idées des autres participants
- ✅ Participation aux votes (limite respectée)
- ✅ Suivi de ses propres contributions
- ✅ Profil utilisateur

## 🎨 Interface et Expérience

### Navigation
- **Design responsive** : Teste sur mobile et desktop
- **Navigation intuitive** : Menus contextuels selon le rôle
- **Feedback utilisateur** : Messages de succès/erreur

### Sécurité
- **Authentification** : Système de connexion sécurisé
- **Autorizations** : Accès restreint selon les rôles
- **Validation** : Contrôles côté client et serveur

## 📈 Métriques et Statistiques

### Tableaux de Bord
- **Participation** : Taux de soumission et de vote
- **Activité** : Timeline des actions récentes
- **Performance** : Idées les plus populaires
- **Utilisateurs** : Statistiques d'engagement

### Rapports
- **Export** : Données exportables (future fonctionnalité)
- **Historique** : Logs détaillés des activités
- **Tendances** : Évolution de la participation

## 🐛 Dépannage

### Problèmes Courants

**L'application ne démarre pas :**
```bash
# Vérifier le statut des services
docker-compose ps

# Vérifier les logs pour identifier l'erreur
docker-compose logs

# Reconstruire les images si nécessaire
docker-compose down
docker-compose up --build -d
```

**La base de données est vide :**
```bash
# Vérifier que MongoDB est actif
docker-compose ps mongodb

# Relancer la génération de données
docker-compose exec app python generate_demo_data.py
```

**Problèmes de connexion :**
- Vérifier que vous utilisez les bons identifiants
- S'assurer que la base de données contient des utilisateurs
- Vérifier que l'application est accessible : `curl http://localhost:8000`

### Réinitialisation Complète

```bash
# Arrêter tous les services Docker
docker-compose down

# Supprimer les volumes (⚠️ ATTENTION : supprime toutes les données)
docker-compose down -v

# Nettoyer les images si nécessaire
docker-compose down --rmi all

# Redémarrer l'environnement complet
docker-compose up -d

# Attendre le démarrage complet (vérifier les logs)
docker-compose logs -f

# Regénérer les données de démonstration
docker-compose exec app python generate_demo_data.py
```

## 🎯 Points Clés à Présenter

### Innovation
- **Interface moderne** et intuitive
- **Workflow complet** de gestion d'idées
- **Système de rôles** flexible et sécurisé

### Scalabilité
- **Architecture modulaire** avec Docker
- **Base de données MongoDB** performante
- **API REST** bien structurée

### Usabilité
- **Expérience utilisateur** optimisée
- **Feedback temps réel** sur les actions
- **Accessibilité** respectée

## 📞 Support

Pour toute question ou problème durant la démonstration :

1. **Consulter les logs** : `docker-compose logs`
2. **Vérifier la documentation** : README.md et CONTRIBUTING.md
3. **Régénérer les données** si nécessaire
4. **Redémarrer les services** en cas de problème persistant

---

**🎉 Bonne démonstration !**

*Idea Box - Plateforme collaborative de gestion d'idées*
