# Schéma de Base de Données - Idea Box

## Vue d'ensemble

L'application **Idea Box** utilise **MongoDB** comme base de données NoSQL avec **ODMantic** comme ORM. Le système gère une plateforme collaborative de gestion d'idées avec trois types d'utilisateurs : superadmin, gestionnaires et invités.

## Architecture de la Base de Données

### Technologie
- **Base de données** : MongoDB
- **ORM** : ODMantic (basé sur Pydantic)
- **Collections** : 4 collections principales

---

## Modèle Conceptuel de Données (MCD)

### Collections et Relations

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      USER       │────▶│     SUBJECT     │◀────│      IDEA       │
│                 │     │                 │     │                 │
│ • _id           │     │ • _id           │     │ • _id           │
│ • email         │     │ • name          │     │ • subject_id    │
│ • nom           │     │ • description   │     │ • user_id       │
│ • prenom        │     │ • superadmin_id │     │ • title         │
│ • pwd (hash)    │     │ • gest_ids[]    │     │ • description   │
│ • roles[]       │     │ • users_ids[]   │     │ • created_at    │
└─────────────────┘     │ • emission_act  │     │ • votes[]       │
         │               │ • vote_active   │     └─────────────────┘
         │               │ • vote_limit    │              │
         │               └─────────────────┘              │
         └─────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────┐
                    │  ACTIVITY_LOG   │
                    │                 │
                    │ • _id           │
                    │ • action        │
                    │ • subject_id    │
                    │ • user_id       │
                    │ • user_email    │
                    │ • user_name     │
                    │ • description   │
                    │ • details       │
                    │ • timestamp     │
                    │ • ip_address    │
                    └─────────────────┘
```

---

## Descriptions des Collections

### 1. Collection `user`

**Description** : Stocke tous les utilisateurs du système avec leurs rôles et informations personnelles.

| Champ | Type | Description | Contraintes |
|-------|------|-------------|-------------|
| `_id` | ObjectId | Identifiant unique auto-généré | Clé primaire |
| `email` | EmailStr | Adresse email de l'utilisateur | Unique, obligatoire |
| `nom` | str | Nom de famille | Obligatoire |
| `prenom` | str | Prénom | Obligatoire |
| `pwd` | str | Mot de passe hashé (bcrypt) | Obligatoire |
| `roles` | List[str] | Liste des rôles assignés | Par défaut: ["user"] |

**Rôles possibles** :
- `"user"` : Invité standard
- `"gestionnaire"` : Gestionnaire de sujets
- `"superadmin"` : Administrateur système

**Index** :
- Index unique sur `email`

#### Exemple de document

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5e6"),
  "email": "jean.dupont@example.com",
  "nom": "Dupont",
  "prenom": "Jean",
  "pwd": "$2b$12$KIXWJl0L5qZ8WqZ8WqZ8We5qZ8WqZ8WqZ8WqZ8WqZ8WqZ8WqZ8Wq",
  "roles": ["user", "gestionnaire"]
}
```

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5e7"),
  "email": "admin@example.com",
  "nom": "Admin",
  "prenom": "Super",
  "pwd": "$2b$12$KIXWJl0L5qZ8WqZ8WqZ8We5qZ8WqZ8WqZ8WqZ8WqZ8WqZ8WqZ8Wq",
  "roles": ["user", "superadmin"]
}
```

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5e8"),
  "email": "marie.martin@example.com",
  "nom": "Martin",
  "prenom": "Marie",
  "pwd": "$2b$12$KIXWJl0L5qZ8WqZ8WqZ8We5qZ8WqZ8WqZ8WqZ8WqZ8WqZ8WqZ8Wq",
  "roles": ["user"]
}

---

### 2. Collection `subjects`

**Description** : Représente les sujets/thèmes pour lesquels les utilisateurs peuvent soumettre des idées.

| Champ | Type | Description | Contraintes |
|-------|------|-------------|-------------|
| `_id` | ObjectId | Identifiant unique auto-généré | Clé primaire |
| `name` | str | Nom du sujet | Obligatoire |
| `description` | str? | Description détaillée du sujet | Optionnel |
| `superadmin_id` | str | ID du superadmin créateur | Obligatoire, FK vers User |
| `gestionnaires_ids` | List[str] | IDs des gestionnaires assignés | Liste des FK vers User |
| `users_ids` | List[str] | IDs des invités assignés | Liste des FK vers User |
| `emission_active` | bool | État de l'émission d'idées | Par défaut: false |
| `vote_active` | bool | État du système de vote | Par défaut: false |
| `vote_limit` | int | Nombre max de votes par utilisateur | Par défaut: 1 |

**Attributs calculés** (non stockés) :
- `ideas_count` : Nombre d'idées soumises
- `votes_count` : Nombre total de votes
- `user_ideas_count` : Nombre d'idées par utilisateur

**Index** :
- Index sur `superadmin_id`
- Index sur `gestionnaires_ids`
- Index sur `users_ids`

#### Exemple de document

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5e9"),
  "name": "Amélioration du processus de recrutement",
  "description": "Idées pour optimiser notre processus de recrutement interne et améliorer l'expérience candidat.",
  "superadmin_id": "60d5ecf0f3e4c1a2b3c4d5e7",
  "gestionnaires_ids": ["60d5ecf0f3e4c1a2b3c4d5e6"],
  "users_ids": ["60d5ecf0f3e4c1a2b3c4d5e8", "60d5ecf0f3e4c1a2b3c4d5ea"],
  "emission_active": true,
  "vote_active": false,
  "vote_limit": 3
}
```

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5eb"),
  "name": "Innovation technologique",
  "description": "Propositions d'outils et technologies pour moderniser notre infrastructure.",
  "superadmin_id": "60d5ecf0f3e4c1a2b3c4d5e7",
  "gestionnaires_ids": ["60d5ecf0f3e4c1a2b3c4d5e6"],
  "users_ids": ["60d5ecf0f3e4c1a2b3c4d5e8"],
  "emission_active": false,
  "vote_active": true,
  "vote_limit": 5
}
```

---

### 3. Collection `ideas`

**Description** : Stocke les idées soumises par les utilisateurs pour les différents sujets.

| Champ | Type | Description | Contraintes |
|-------|------|-------------|-------------|
| `_id` | ObjectId | Identifiant unique auto-généré | Clé primaire |
| `subject_id` | str | ID du sujet parent | Obligatoire, FK vers Subject |
| `user_id` | str | ID de l'auteur de l'idée | Obligatoire, FK vers User |
| `title` | str | Titre de l'idée | Obligatoire |
| `description` | str? | Description détaillée | Optionnel |
| `created_at` | datetime | Date/heure de création | Auto-généré |
| `votes` | List[str] | IDs des utilisateurs ayant voté | Liste des FK vers User |

**Index** :
- Index sur `subject_id`
- Index sur `user_id`
- Index sur `created_at` (décroissant)

#### Exemple de document

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5ec"),
  "subject_id": "60d5ecf0f3e4c1a2b3c4d5e9",
  "user_id": "60d5ecf0f3e4c1a2b3c4d5e8",
  "title": "Mettre en place un système de covoiturage",
  "description": "Proposer une plateforme interne pour faciliter le covoiturage entre employés, réduire les coûts de transport et l'impact environnemental.",
  "created_at": ISODate("2025-07-07T09:30:00.000Z"),
  "votes": ["60d5ecf0f3e4c1a2b3c4d5ea", "60d5ecf0f3e4c1a2b3c4d5ed"]
}
```

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5ee"),
  "subject_id": "60d5ecf0f3e4c1a2b3c4d5e9",
  "user_id": "60d5ecf0f3e4c1a2b3c4d5ea",
  "title": "Automatiser les entretiens préliminaires",
  "description": "Utiliser des chatbots IA pour effectuer un premier tri des candidatures et planifier automatiquement les entretiens.",
  "created_at": ISODate("2025-07-07T14:15:00.000Z"),
  "votes": ["60d5ecf0f3e4c1a2b3c4d5e8"]
}
```

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5ef"),
  "subject_id": "60d5ecf0f3e4c1a2b3c4d5eb",
  "user_id": "60d5ecf0f3e4c1a2b3c4d5e8",
  "title": "Migration vers le cloud",
  "description": "Planifier la migration de nos serveurs vers une infrastructure cloud pour améliorer la scalabilité et réduire les coûts.",
  "created_at": ISODate("2025-07-06T16:45:00.000Z"),
  "votes": []
}
```

---

### 4. Collection `activity_logs`

**Description** : Journal d'audit de toutes les actions importantes effectuées dans le système.

| Champ | Type | Description | Contraintes |
|-------|------|-------------|-------------|
| `_id` | ObjectId | Identifiant unique auto-généré | Clé primaire |
| `action` | str | Code de l'action effectuée | Obligatoire |
| `subject_id` | str | ID du sujet concerné | Obligatoire, FK vers Subject |
| `user_id` | str | ID de l'utilisateur acteur | Obligatoire, FK vers User |
| `user_email` | str | Email de l'utilisateur | Obligatoire |
| `user_name` | str | Nom complet de l'utilisateur | Obligatoire |
| `description` | str | Description lisible de l'action | Obligatoire |
| `details` | str? | Détails supplémentaires | Optionnel |
| `timestamp` | datetime | Horodatage de l'action | Auto-généré |
| `ip_address` | str? | Adresse IP de l'utilisateur | Optionnel |

**Actions trackées** :
- `activate_emission` : Activation émission d'idées
- `deactivate_emission` : Désactivation émission d'idées
- `activate_vote` : Activation session de vote
- `close_vote` : Clôture session de vote
- `abandon_vote` : Abandon session de vote
- `edit_idea` : Modification d'une idée
- `delete_idea` : Suppression d'une idée
- `add_manager` : Ajout d'un gestionnaire
- `remove_manager` : Suppression d'un gestionnaire

**Index** :
- Index sur `subject_id`
- Index sur `user_id`
- Index sur `timestamp` (décroissant)
- Index sur `action`

#### Exemple de document

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5f0"),
  "action": "activate_emission",
  "subject_id": "60d5ecf0f3e4c1a2b3c4d5e9",
  "user_id": "60d5ecf0f3e4c1a2b3c4d5e6",
  "user_email": "jean.dupont@example.com",
  "user_name": "Jean Dupont",
  "description": "Activation de l'émission d'idées pour le sujet 'Amélioration du processus de recrutement'",
  "details": "État précédent: Inactive",
  "timestamp": ISODate("2025-07-07T08:00:00.000Z"),
  "ip_address": "192.168.1.42"
}
```

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5f1"),
  "action": "edit_idea",
  "subject_id": "60d5ecf0f3e4c1a2b3c4d5e9",
  "user_id": "60d5ecf0f3e4c1a2b3c4d5e6",
  "user_email": "jean.dupont@example.com",
  "user_name": "Jean Dupont",
  "description": "Modification de l'idée 'Mettre en place un système de covoiturage' par le gestionnaire",
  "details": "Ancien titre: 'Covoiturage employés' -> Nouveau titre: 'Mettre en place un système de covoiturage'",
  "timestamp": ISODate("2025-07-07T10:30:00.000Z"),
  "ip_address": "192.168.1.42"
}
```

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5f2"),
  "action": "activate_vote",
  "subject_id": "60d5ecf0f3e4c1a2b3c4d5eb",
  "user_id": "60d5ecf0f3e4c1a2b3c4d5e6",
  "user_email": "jean.dupont@example.com",
  "user_name": "Jean Dupont",
  "description": "Activation de la session de vote pour le sujet 'Innovation technologique'",
  "details": "Émission d'idées automatiquement désactivée",
  "timestamp": ISODate("2025-07-07T15:00:00.000Z"),
  "ip_address": "192.168.1.42"
}
```

```json
{
  "_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5f3"),
  "action": "add_manager",
  "subject_id": "60d5ecf0f3e4c1a2b3c4d5e9",
  "user_id": "60d5ecf0f3e4c1a2b3c4d5e7",
  "user_email": "admin@example.com",
  "user_name": "Super Admin",
  "description": "Gestionnaire Marie Martin ajouté au sujet Amélioration du processus de recrutement",
  "details": "Utilisateur marie.martin@example.com promu gestionnaire",
  "timestamp": ISODate("2025-07-07T11:20:00.000Z"),
  "ip_address": "192.168.1.100"
}
```

---

## Exemples de Données et Statistiques

### Volume de données type

Pour une organisation de **200 employés** avec **10 sujets actifs** :

| Collection | Nombre de documents | Taille moyenne | Taille totale estimée |
|------------|-------------------|-----------------|----------------------|
| `user` | 200 | 150 bytes | 30 KB |
| `subjects` | 10 | 300 bytes | 3 KB |
| `ideas` | 500 | 500 bytes | 250 KB |
| `activity_logs` | 2000 | 400 bytes | 800 KB |
| **Total** | **2710** | - | **~1.1 MB** |

### Exemples de requêtes métier

#### Statistiques d'un sujet
```javascript
// Sujet avec ses métriques complètes
db.subjects.aggregate([
  {$match: {"_id": ObjectId("60d5ecf0f3e4c1a2b3c4d5e9")}},
  {$lookup: {
    from: "ideas",
    localField: "_id",
    foreignField: "subject_id", 
    as: "ideas"
  }},
  {$lookup: {
    from: "activity_logs",
    localField: "_id", 
    foreignField: "subject_id",
    as: "activities"
  }},
  {$addFields: {
    "ideas_count": {$size: "$ideas"},
    "total_votes": {$sum: {$map: {
      input: "$ideas",
      as: "idea", 
      in: {$size: "$$idea.votes"}
    }}},
    "activities_count": {$size: "$activities"},
    "unique_voters": {$size: {$setUnion: {$reduce: {
      input: "$ideas",
      initialValue: [],
      in: {$setUnion: ["$$value", "$$this.votes"]}
    }}}}
  }}
])
```

#### Top 5 des idées les plus votées
```javascript
db.ideas.aggregate([
  {$match: {"subject_id": "60d5ecf0f3e4c1a2b3c4d5e9"}},
  {$addFields: {"vote_count": {$size: "$votes"}}},
  {$sort: {"vote_count": -1, "created_at": -1}},
  {$limit: 5},
  {$lookup: {
    from: "user",
    localField: "user_id",
    foreignField: "_id",
    as: "author"
  }},
  {$project: {
    "title": 1,
    "vote_count": 1,
    "created_at": 1,
    "author_name": {$concat: [
      {$arrayElemAt: ["$author.prenom", 0]}, 
      " ", 
      {$arrayElemAt: ["$author.nom", 0]}
    ]}
  }}
])
```

#### Activité récente d'un gestionnaire
```javascript
db.activity_logs.find({
  "user_id": "60d5ecf0f3e4c1a2b3c4d5e6",
  "timestamp": {
    $gte: ISODate("2025-07-01T00:00:00.000Z")
  }
}).sort({"timestamp": -1}).limit(10)
```

---

## Relations et Contraintes

### Relations principales

1. **User → Subject** (1:N via superadmin_id)
   - Un superadmin peut créer plusieurs sujets
   - Un sujet appartient à un seul superadmin

2. **User ↔ Subject** (N:M via gestionnaires_ids)
   - Un utilisateur peut être gestionnaire de plusieurs sujets
   - Un sujet peut avoir plusieurs gestionnaires

3. **User ↔ Subject** (N:M via users_ids)
   - Un invité peut être assigné à plusieurs sujets
   - Un sujet peut avoir plusieurs invités assignés

4. **User → Idea** (1:N)
   - Un utilisateur peut créer plusieurs idées
   - Une idée appartient à un seul utilisateur

5. **Subject → Idea** (1:N)
   - Un sujet peut avoir plusieurs idées
   - Une idée appartient à un seul sujet

6. **User ↔ Idea** (N:M via votes)
   - Un utilisateur peut voter pour plusieurs idées
   - Une idée peut recevoir des votes de plusieurs utilisateurs

7. **User → ActivityLog** (1:N)
   - Un utilisateur peut effectuer plusieurs actions
   - Une action est effectuée par un seul utilisateur

8. **Subject → ActivityLog** (1:N)
   - Un sujet peut avoir plusieurs activités loggées
   - Une activité concerne un seul sujet

### Règles métier

#### Contraintes sur les rôles
- Un utilisateur avec le rôle `superadmin` peut :
  - Créer, modifier, supprimer des sujets
  - Assigner des gestionnaires aux sujets
  - Gérer tous les utilisateurs
  
- Un utilisateur avec le rôle `gestionnaire` peut :
  - Gérer les sujets où il est assigné (gestionnaires_ids)
  - Modifier/supprimer les idées de ses sujets
  - Activer/désactiver émission et vote
  - Assigner des invités à ses sujets
  - Promouvoir des invités au rôle gestionnaire

- Un utilisateur avec le rôle `user` (invité) peut :
  - Soumettre des idées sur les sujets assignés
  - Voter sur les idées (si vote actif)
  - Consulter ses propres idées et statistiques

#### Contraintes sur les états des sujets
- `emission_active` et `vote_active` sont mutuellement exclusifs
- L'activation du vote désactive automatiquement l'émission
- L'abandon du vote réactive l'émission
- La clôture du vote désactive les deux états

#### Contraintes sur les votes
- Un utilisateur ne peut voter qu'une fois par idée
- Le nombre total de votes par utilisateur par sujet est limité par `vote_limit`
- Les votes ne sont possibles que si `vote_active = true`

---

## Performances et Optimisations

### Index recommandés

```javascript
// Collection users
db.user.createIndex({"email": 1}, {unique: true})

// Collection subjects
db.subjects.createIndex({"superadmin_id": 1})
db.subjects.createIndex({"gestionnaires_ids": 1})
db.subjects.createIndex({"users_ids": 1})

// Collection ideas
db.ideas.createIndex({"subject_id": 1})
db.ideas.createIndex({"user_id": 1})
db.ideas.createIndex({"created_at": -1})
db.ideas.createIndex({"subject_id": 1, "created_at": -1})

// Collection activity_logs
db.activity_logs.createIndex({"subject_id": 1})
db.activity_logs.createIndex({"user_id": 1})
db.activity_logs.createIndex({"timestamp": -1})
db.activity_logs.createIndex({"action": 1})
db.activity_logs.createIndex({"subject_id": 1, "timestamp": -1})
```

### Requêtes fréquentes optimisées

1. **Récupération des sujets d'un gestionnaire** :
   ```javascript
   db.subjects.find({"gestionnaires_ids": user_id})
   ```

2. **Récupération des idées d'un sujet avec tri** :
   ```javascript
   db.ideas.find({"subject_id": subject_id}).sort({"created_at": -1})
   ```

3. **Calcul des statistiques d'un sujet** :
   ```javascript
   // Nombre d'idées
   db.ideas.countDocuments({"subject_id": subject_id})
   
   // Nombre total de votes
   db.ideas.aggregate([
     {$match: {"subject_id": subject_id}},
     {$project: {"vote_count": {$size: "$votes"}}},
     {$group: {"_id": null, "total_votes": {$sum: "$vote_count"}}}
   ])
   ```

4. **Historique d'activités d'un sujet** :
   ```javascript
   db.activity_logs.find({"subject_id": subject_id}).sort({"timestamp": -1})
   ```

---

## Sécurité

### Authentification
- Mots de passe hashés avec **bcrypt** (coût : 12)
- Sessions utilisateur avec tokens JWT

### Autorisation
- Contrôle d'accès basé sur les rôles (RBAC)
- Vérification des permissions au niveau des routes
- Validation des appartenances utilisateur/sujet

### Audit
- Toutes les actions importantes sont loggées dans `activity_logs`
- Traçabilité complète des modifications
- Conservation de l'adresse IP pour l'audit

---

## Évolutions futures

### Améliorations possibles
1. **Catégories d'idées** : Ajouter une collection `categories`
2. **Commentaires** : Collection `comments` pour les discussions sur les idées
3. **Notifications** : Collection `notifications` pour alerter les utilisateurs
4. **Fichiers joints** : Support des pièces jointes aux idées
5. **Historique des versions** : Versioning des modifications d'idées
6. **Archivage** : Collection `archived_subjects` pour l'historique

### Optimisations avancées
1. **Sharding** : Partitionnement par `subject_id` pour la scalabilité
2. **Read replicas** : Réplication pour les requêtes de lecture
3. **Caching** : Redis pour les données fréquemment consultées
4. **Text search** : Index full-text sur les titres et descriptions d'idées

---

*Document généré le 7 juillet 2025*  
*Version de l'application : 1.0.0*  
*Base de données : MongoDB 4.4+*
