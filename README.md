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