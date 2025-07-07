# Guide de Contribution - Idea Box

Merci de votre intérêt pour contribuer au projet **Idea Box** ! Ce guide vous aidera à comprendre comment participer au développement de manière efficace.

## 🚀 Comment commencer

### 1. Fork et Clone
```bash
# Fork le projet sur GitHub puis clonez votre fork
git clone https://github.com/votre-username/idea-box.git
cd idea-box

# Ajoutez le repo original comme remote
git remote add upstream https://github.com/original-owner/idea-box.git
```

### 2. Configuration de l'environnement de développement
```bash
# Installation des dépendances
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Si existe

# Démarrage avec Docker (recommandé)
docker-compose up -d

# Ou installation locale
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 3. Créer une branche de travail
```bash
git checkout -b feature/description-courte
# ou
git checkout -b fix/description-du-bug
# ou  
git checkout -b docs/amelioration-documentation
```

## 📋 Types de contributions

### 🐛 Correction de bugs
- Vérifiez qu'un issue existe déjà
- Créez un issue si nécessaire avec :
  - Description détaillée du bug
  - Étapes pour reproduire
  - Comportement attendu vs actuel
  - Environnement (OS, versions, etc.)

### ✨ Nouvelles fonctionnalités
- Discutez d'abord de la fonctionnalité dans un issue
- Assurez-vous qu'elle s'aligne avec la vision du projet
- Préparez des tests pour la nouvelle fonctionnalité

### 📖 Documentation
- Améliorations du README
- Documentation technique (commentaires, docstrings)
- Guides d'utilisation
- Traductions

### 🧪 Tests
- Ajout de tests unitaires
- Tests d'intégration
- Amélioration de la couverture de tests

## 💻 Standards de développement

### Code Python
Suivez **PEP 8** et ces conventions :

```python
# Type hints obligatoires
async def create_user(user_data: dict) -> Optional[User]:
    """
    Crée un nouvel utilisateur dans la base de données.
    
    Args:
        user_data: Dictionnaire contenant les données utilisateur
        
    Returns:
        User object si succès, None sinon
        
    Raises:
        ValidationError: Si les données sont invalides
    """
    pass

# Nommage des variables/fonctions en snake_case
user_count = get_total_users()

# Nommage des classes en PascalCase
class UserService:
    pass
```

### Structure des commits
Utilisez des messages de commit clairs :

```bash
# Format : type(scope): description courte
feat(auth): ajouter authentification JWT
fix(ui): corriger affichage des idées sur mobile
docs(readme): mettre à jour instructions d'installation
test(user): ajouter tests pour création utilisateur
refactor(db): optimiser requêtes MongoDB
```

**Types de commits :**
- `feat`: nouvelle fonctionnalité
- `fix`: correction de bug
- `docs`: documentation
- `test`: ajout/modification de tests
- `refactor`: refactoring sans changement fonctionnel
- `style`: changements de style (formatting, etc.)
- `perf`: amélioration de performance

### Tests
Chaque nouvelle fonctionnalité doit inclure des tests :

```python
# tests/test_user_service.py
import pytest
from src.services.user_service import create_user
from src.models.user import User

@pytest.mark.asyncio
async def test_create_user_success():
    """Test de création d'utilisateur avec données valides."""
    user_data = {
        "email": "test@example.com",
        "nom": "Doe",
        "prenom": "John",
        "pwd": "password123"
    }
    
    user = await create_user(user_data)
    
    assert user is not None
    assert user.email == "test@example.com"
    assert "user" in user.roles

@pytest.mark.asyncio 
async def test_create_user_duplicate_email():
    """Test de création avec email déjà existant."""
    # Test logic here
    pass
```

### Architecture du code

#### Modèles (models/)
```python
# src/models/user.py
from pydantic import EmailStr
from typing import List
from odmantic import Model

class User(Model):
    __collection__ = "user"
    email: EmailStr
    nom: str
    prenom: str
    pwd: str
    roles: List[str] = ["user"]
```

#### Services (services/)
```python
# src/services/user_service.py
from typing import Optional
from src.models.user import User

async def get_user_by_email(email: str) -> Optional[User]:
    """Récupère un utilisateur par son email."""
    return await Database.engine.find_one(User, User.email == email)
```

#### Routes (routes/)
```python
# src/routes/user.py
from fastapi import APIRouter, Depends
from src.services.auth_service import get_current_user

router = APIRouter()

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    """Récupère le profil de l'utilisateur connecté."""
    return {"user": current_user}
```

## 🧪 Exécution des tests

### Tests locaux
```bash
# Tous les tests
python -m pytest tests/ -v

# Tests spécifiques
python -m pytest tests/test_user_service.py -v

# Avec couverture
python -m pytest tests/ --cov=src --cov-report=html

# Tests d'intégration seulement
python -m pytest tests/integration/ -v
```

### Tests dans Docker
```bash
# Lancer les tests dans un conteneur
docker-compose run --rm app python -m pytest tests/ -v
```

## 📝 Documentation

### Docstrings
Utilisez le format Google :

```python
def calculate_idea_score(idea: Idea, weights: dict) -> float:
    """
    Calcule le score d'une idée basé sur différents critères.
    
    Args:
        idea: L'idée à évaluer
        weights: Poids des différents critères (votes, date, etc.)
        
    Returns:
        Score calculé entre 0 et 100
        
    Example:
        >>> weights = {"votes": 0.7, "recency": 0.3}
        >>> score = calculate_idea_score(idea, weights)
        >>> print(f"Score: {score}")
        Score: 85.5
    """
    pass
```

### Templates
Pour les templates Jinja2 :

```html
<!-- src/templates/user/dashboard.html -->
{% extends "base.html" %}

{% block title %}Tableau de bord - {{ current_user.prenom }}{% endblock %}

{% block content %}
<!-- Contenu du template avec commentaires explicatifs -->
<div class="container-fluid">
    <!-- Section des métriques utilisateur -->
    <div class="row mb-4">
        <!-- Carte du nombre d'idées -->
        <div class="col-md-4">
            <!-- ... -->
        </div>
    </div>
</div>
{% endblock %}
```

## 🔍 Review Process

### Avant de soumettre une PR
- [ ] Les tests passent localement
- [ ] Le code respecte les standards
- [ ] La documentation est à jour
- [ ] Les commits sont propres et atomiques
- [ ] La branche est à jour avec main

### Checklist de la Pull Request
```markdown
## Description
Résumé des changements apportés

## Type de changement
- [ ] Bug fix
- [ ] Nouvelle fonctionnalité  
- [ ] Breaking change
- [ ] Documentation

## Tests
- [ ] Tests unitaires ajoutés/modifiés
- [ ] Tests d'intégration mis à jour
- [ ] Tous les tests passent

## Documentation
- [ ] README mis à jour si nécessaire
- [ ] Docstrings ajoutées/mises à jour
- [ ] Commentaires de code appropriés
```

### Process de review
1. **Auto-review** : Relisez votre code avant soumission
2. **CI/CD checks** : Assurez-vous que tous les checks passent
3. **Peer review** : Au moins 1 approbation requise
4. **Merge** : Squash and merge préféré pour garder un historique propre

## 🚀 Déploiement et releases

### Versioning
Le projet suit [Semantic Versioning](https://semver.org/) :
- **MAJOR** : Changements incompatibles
- **MINOR** : Nouvelles fonctionnalités compatibles
- **PATCH** : Corrections de bugs

### Branches
- **`main`** : Branche principale, toujours stable
- **`develop`** : Branche de développement pour intégration
- **`feature/*`** : Branches de fonctionnalités
- **`fix/*`** : Branches de correction de bugs
- **`release/*`** : Branches de préparation de release

## 🎯 Priorités actuelles

### High Priority
- [ ] Tests d'intégration complets
- [ ] Documentation API avec OpenAPI/Swagger
- [ ] Amélioration des performances MongoDB
- [ ] Sécurité : audit des permissions

### Medium Priority  
- [ ] Interface mobile responsive
- [ ] Notifications en temps réel
- [ ] Export des données (PDF, Excel)
- [ ] Système de commentaires

### Low Priority
- [ ] Intégration SSO/LDAP
- [ ] API GraphQL
- [ ] Internationalisation (i18n)
- [ ] Thèmes personnalisables

## 🤝 Code of Conduct

### Nos engagements
- **Respect** : Traiter tous les contributeurs avec respect
- **Bienveillance** : Fournir des retours constructifs
- **Inclusion** : Accueillir les contributeurs de tous niveaux
- **Collaboration** : Privilégier l'entraide et le partage

### Standards
- Utiliser un langage professionnel et inclusif
- Accepter les critiques constructives
- Se concentrer sur ce qui est le mieux pour la communauté
- Faire preuve d'empathie envers les autres membres

## 📞 Aide et support

### Communication
- **Issues GitHub** : Pour bugs et demandes de fonctionnalités
- **Discussions** : Pour questions générales et aide
- **Email** : dev@votre-domaine.com pour questions sensibles

### Ressources utiles
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [ODMantic Documentation](https://art049.github.io/odmantic/)
- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.0/)

---

**Merci de contribuer à rendre Idea Box encore meilleur ! 🚀**
