# PFE-assistant-vocal-medical

_Valentine Dumange / Kilian Davoust_

## Présentation du projet

Ce projet consiste en un assistant médical intelligent capable de gérer de manière autonome la prise de rendez-vous par téléphone (via une interface web). Il répond à une problématique d'inclusion numérique pour les populations isolées tout en désengorgeant les secrétariats médicaux.

Contrairement aux chatbots classiques, cette solution repose sur une architecture hybride et déterministe : la compréhension est confiée à l'IA, mais l'exécution des tâches suit une logique métier stricte et sécurisée.

## Gitflow
- `main` : Livraison finale
- `develop` : Espace tampon
- `features/*` : Développement

## Architecture

**Stack technique :** FastAPI + PostgreSQL + MLflow + Ollama (Mistral)

| Composant | Rôle |
|-----------|------|
| **api/** | API FastAPI pour le dialogue (intent classification + réponses dynamiques) |
| **services/dialogue/** | Logique du dialogue (routing, génération de réponses) |
| **services/extraction/** | Client Ollama pour extraction des slots (dates, heures, médecins) |
| **services/model_training/** | Pipeline ML (TF-IDF + SVM) pour classification d'intentions |
| **db/init/** | Schéma PostgreSQL (médecins, créneaux, infos pratiques) |
| **data/processed/** | Datasets d'entraînement et de test (synthétiques, RGPD compliant) |
| **mlartifacts/** | Modèles enregistrés dans MLflow (versioning + Model Registry) |

## Lancement

1. Cloner le repo :
   ```bash
   git clone https://github.com/valentinedum/PFE-assistant-vocal-medical
   cd PFE-assistant-vocal-medical
   ```

2.  Lancer l'environnement de développement :
    ```bash
    docker-compose up --build
    ```

3.  Accéder aux services :
    * **API & Documentation (Swagger) :** [http://localhost:8000/docs](http://localhost:8000/docs)
    * **MLflow UI (Tracking) :** [http://localhost:5000](http://localhost:5000)

## Données

### Données d'entrainement

Faute de données réelles concernant les appels de prise de rendez-vous médicaux (contraintes RGPD), nous générons synthétiquement un dataset d'entraînement diversifié couvrant les principales intentions d'appel :

- **book_appointment** : Demande de prise de rendez-vous
- **medical_urgency** : Situation d'urgence médicale
- **info_practical** : Questions pratiques (horaires, localisation, etc.)
- **cancel_appointment** : Annulation de rendez-vous
- **off_topic** : Requêtes hors sujet

### Données métier (Base de données)

En complément des données d'entraînement, la base de données PostgreSQL contient les données métier structurées :

**Schéma principal :**
- **doctors** : Informations des médecins (id, nom, spécialité, etc.)
- **slots** : Créneaux de disponibilité des médecins
- **info** : Information générales sur le cabinet (adresse, nom, etc.)

Ces données sont initialisées via les scripts SQL dans `db/init/` lors du démarrage des conteneurs Docker.

## Modèles ML

**Entraînement :**
```bash
docker-compose --profile train run train python services/model_training/train.py
```

**Mise en production :**
1. MLflow UI → **Models** > **medical_intent_classifier** > Sélectionnez la version
2. Cliquez **Stage** → **Production**
3. Redémarrez l'API : `docker-compose restart api`

