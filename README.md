# PFE-assistant-vocal-medical

_Valentine Dumange / Kilian Davoust_

## Gitflow
- branche main pour livraison finale
- branche develop comme espace tampon
- branches features pour le développement des fonctionnalités

### Lancement
1.  Cloner le repo :
    ```bash
    git clone [https://github.com/valentinedum/PFE-assistant-vocal-medical](https://github.com/valentinedum/PFE-assistant-vocal-medical)
    cd PFE-assistant-vocal-medical
    ```

2.  Lancer l'environnement de développement :
    ```bash
    docker-compose up --build
    ```

3.  Accéder aux services :
    * **API & Documentation (Swagger) :** [http://localhost:8000/docs](http://localhost:8000/docs)
    * **MLflow UI (Tracking) :** [http://localhost:5000](http://localhost:5000)

## Structure du Projet

```
├── README.md
├── api
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
├── data
│   ├── processed
│   └── raw
├── docker-compose.yml
├── mlartifacts
├── mlflow.db
└── services
```

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
- **appointments** : Rendez-vous médicaux pris

Ces données sont initialisées via les scripts SQL dans `db/init/` lors du démarrage des conteneurs Docker. 
