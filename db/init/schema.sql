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
    start_time TIMESTAMP NOT NULL,
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
('address', '123 Avenue de la République, Paris'),
('phone', '01 23 45 67 89'),
('hours', 'Du Lundi au Vendredi, 9h - 19h'),
('price', '25€ la consultation (Secteur 1)'),
('parking', 'Oui, parking gratuit au sous-sol, limité à 2 heures');

-- On insère des créneaux 

INSERT INTO slots (doctor_id, start_time, is_booked)
SELECT 
    1,
    (CURRENT_DATE + (d || ' day')::INTERVAL + (h || ' hour')::INTERVAL + '9 hours'),
    FALSE
FROM generate_series(1, 7) AS d   -- 👈 Pour les 7 prochains jours
CROSS JOIN generate_series(0, 8) AS h; -- 👈 De 9h à 17h (9 créneaux par jour)

INSERT INTO slots (doctor_id, start_time, is_booked)
SELECT
    2,
    (CURRENT_DATE + (d || ' day')::INTERVAL + (h || ' hour')::INTERVAL + '9 hours'),
    FALSE
FROM generate_series(1, 7) AS d
CROSS JOIN generate_series(0, 8) AS h;

INSERT INTO slots (doctor_id, start_time, is_booked)
SELECT
    3,
    (CURRENT_DATE + (d || ' day')::INTERVAL + (h || ' hour')::INTERVAL + '9 hours'),
    FALSE
FROM generate_series(1, 7) AS d
CROSS JOIN generate_series(0, 8) AS h;