Je souhaite realiser une application "boite à idées" permettant de creer un sujet par un superadmin et laisser la gestion à une ou plusieur personne(gestionnaires).
Pour ce sujet, les utilisateurs attribués à ce sujet par les gestionnaires peuvent:
- Emmetre des idées
- Voter pour la selection des idées (nombre parametrables par les gestionnaires. Les idées sur lequelles pouront votés peuvent être préselectionnées)

BREF:
# Notion utilisateur:
- email
- nom
- prenom
- pwd
# Notion de superadmin: 
Est un utilisateur ayant en plus les droits de:
- Il ajout à l'application des utilisateurs individuellement ou via des imports depuis un fichier excel/csv
- Il crée des sujets et attribué à chaque sujet un ou plusieur gestionnaire

# Notion gestionnaire: Est un utilisateur ayant en plus les droits de:
Est un utilisateur qui a été ajouter comme gestionnaire d'un sujet
S'il est gestionnaire de plusieur sujets. Il doit activer un seul. Les actions qu'il fera par la suite seront en lien avec le sujet actif
- Ajout des autres gestionnaires au sujet active pour lui
- importer/ajouter/retirer des utilisateurs au sujet active
- activer l'emission des idées au sujet: Permettre aux individus liés de commencer à emettre des idées
- désactiver l'emission des idées au sujet: Bloquer aux individus liés d'emettre des idées
- activer la session de vote: Permettre aux utilisateurs du sujet de commencer à voter pour les idées du sujet. Ceci desactivera l'emission des idées
- fermer la session du vote: colturer la session de vote et afficher les resulta
- abondonner vote: abondonner une session de vote


Les technologies:
- Python, flask, fastapi, mongo, docker, jingo, 
- Autre si necessaire