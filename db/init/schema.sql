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

-- 4. Table des Rendez-vous
CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    slot_id INTEGER REFERENCES slots(id),
    doctor_id INTEGER REFERENCES doctors(id),
    patient_name TEXT DEFAULT 'Patient vocal',
    booked_at TIMESTAMP DEFAULT NOW(),
    transcription TEXT
);

--- PEUPLEMENT DES DONNÉES ---

-- On insère les médecins
INSERT INTO doctors (name, specialty) VALUES 
('Dr. Maison', 'Orthodontiste'),
('Dr. Smith', 'Kinésithérapeute'),
('Dr. Robert', 'Généraliste');

-- On insère les infos pratiques
INSERT INTO clinic_info (key, value) VALUES 
('clinic_name', 'Clinique Médicale de la République'),
('address', '123 Avenue de la République, Paris'),
('phone', '01 23 45 67 89'),
('hours', 'Du Lundi au Vendredi, 9h - 19h'),
('price', '25€ la consultation (Secteur 1)'),
('parking', 'Oui, parking gratuit au sous-sol, limité à 2 heures');

-- On insère des créneaux (uniquement du lundi au vendredi, de 9h à 18h)

INSERT INTO slots (doctor_id, start_time, is_booked)
SELECT 
    1,
    slot_time,
    FALSE
FROM (
    SELECT (CURRENT_DATE + (d || ' day')::INTERVAL + (h || ' hour')::INTERVAL + '9 hours') AS slot_time
    FROM generate_series(1, 14) AS d
    CROSS JOIN generate_series(0, 9) AS h
) sub
WHERE EXTRACT(DOW FROM slot_time) BETWEEN 1 AND 5; -- 1=lundi ... 5=vendredi

INSERT INTO slots (doctor_id, start_time, is_booked)
SELECT 
    2,
    slot_time,
    FALSE
FROM (
    SELECT (CURRENT_DATE + (d || ' day')::INTERVAL + (h || ' hour')::INTERVAL + '9 hours') AS slot_time
    FROM generate_series(1, 14) AS d
    CROSS JOIN generate_series(0, 9) AS h
) sub
WHERE EXTRACT(DOW FROM slot_time) BETWEEN 1 AND 5;

INSERT INTO slots (doctor_id, start_time, is_booked)
SELECT 
    3,
    slot_time,
    FALSE
FROM (
    SELECT (CURRENT_DATE + (d || ' day')::INTERVAL + (h || ' hour')::INTERVAL + '9 hours') AS slot_time
    FROM generate_series(1, 14) AS d
    CROSS JOIN generate_series(0, 9) AS h
) sub
WHERE EXTRACT(DOW FROM slot_time) BETWEEN 1 AND 5;