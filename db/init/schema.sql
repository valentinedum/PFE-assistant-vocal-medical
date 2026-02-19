--- SCHEMA DE LA BASE DE DONNÉES POUR L'ASSISTANT VOCAL MÉDICAL ---

-- 1. Table des Médecins
CREATE TABLE IF NOT EXISTS doctors (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    specialty TEXT NOT NULL
);

-- 2. Table de l'Agenda (Créneaux)
CREATE TABLE IF NOT EXISTS slots (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER REFERENCES doctors(id),
    day_of_week INTEGER NOT NULL,  -- 0=Dimanche, 1=Lundi, 2=Mardi, 3=Mercredi, 4=Jeudi, 5=Vendredi, 6=Samedi
    hour INTEGER NOT NULL,         -- 9-17 (heure)
    is_booked BOOLEAN DEFAULT FALSE
);

-- 3. Table des Infos Pratiques
CREATE TABLE IF NOT EXISTS clinic_info (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

--- PEUPLEMENT DES DONNÉES ---

-- On insère les médecins
INSERT INTO doctors (name, specialty) VALUES 
('Dr. House', 'Orthodontiste'),
('Dr. Smith', 'Kinésithérapeute'),
('Dr. Cymes', 'Généraliste');

-- On insère les infos pratiques
INSERT INTO clinic_info (key, value) VALUES 
('clinic_name', 'Clinique Médicale de la République'),
('address', '123 Avenue de la République, Paris'),
('phone', '01 23 45 67 89'),
('hours', 'Du Lundi au Vendredi, 9h - 17h'),
('price', '25€ la consultation (Secteur 1)'),
('parking', 'Oui, parking gratuit au sous-sol, limité à 2 heures');

-- On insère des créneaux (Lundi à Vendredi, 9h à 17h pour chaque médecin)
-- Dr. House (id=1)
INSERT INTO slots (doctor_id, day_of_week, hour)
SELECT 1, day, hour
FROM generate_series(1, 5) AS day  -- 1=Lundi à 5=Vendredi
CROSS JOIN generate_series(9, 17) AS hour;  -- 9h à 17h

-- Dr. Smith (id=2)
INSERT INTO slots (doctor_id, day_of_week, hour)
SELECT 2, day, hour
FROM generate_series(1, 5) AS day
CROSS JOIN generate_series(9, 17) AS hour;

-- Dr. Cymes (id=3)
INSERT INTO slots (doctor_id, day_of_week, hour)
SELECT 3, day, hour
FROM generate_series(1, 5) AS day
CROSS JOIN generate_series(9, 17) AS hour;