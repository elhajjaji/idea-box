# Idea Box – Image Docker officielle

## Lancer avec Docker Compose

```yaml
version: '3.8'
services:
  idea-box:
    image: elhajjaji/idea-box:1.0.0  # Remplacez la version si besoin
    ports:
      - "8000:8000"
    environment:
      # Variables d'environnement recommandées
      MONGO_URI: "mongodb://mongo:27017/idea_box"
      MONGO_DB_NAME: "idea_box"
      SUPERADMIN_EMAIL: "admin@demo.com"
      SUPERADMIN_PASSWORD: "admin123"
      SUPERADMIN_PRENOM: "Super"
      SUPERADMIN_NOM: "Admin"
    depends_on:
      - mongo
  mongo:
    image: mongo:6
    restart: always
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
volumes:
  mongo_data:
```

## Création automatique du superadmin

À chaque démarrage, l'application vérifie la présence d'un superadmin. Si les variables `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`, `SUPERADMIN_PRENOM`, `SUPERADMIN_NOM` sont définies, un superadmin est créé automatiquement si besoin.

## Lancer l'application

1. Placez ce fichier `docker-compose.yml` dans un dossier.
2. Lancez :
   ```sh
   docker compose up -d
   ```
3. Accédez à http://localhost:8000

## Variables d'environnement utiles
- `MONGO_URI` : URL de connexion MongoDB
- `MONGO_DB_NAME` : Nom de la base de données
- `SUPERADMIN_EMAIL`, `SUPERADMIN_PASSWORD`, `SUPERADMIN_PRENOM`, `SUPERADMIN_NOM` : infos du superadmin par défaut

## Exemple de connexion
- Email : `admin@demo.com`
- Mot de passe : `admin123`

---

Pour builder et publier votre propre image :
```sh
cd deployment
./build_and_push.sh 1.0.0
```

Voir README.md pour plus d'options.
