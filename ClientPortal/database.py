import sqlite3
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Charge le .env pour que os.getenv() puisse lire ADMIN_PASSWORD et SECRET_KEY
load_dotenv()

# SQLite = base de données dans un seul fichier .db, pas de serveur séparé.
# Parfait pour une app mono-utilisateur ou petit trafic.
DB_PATH = 'portal.db'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    # row_factory = sqlite3.Row : permet d'accéder aux colonnes par nom
    # ex: row['email'] plutôt que row[2] — beaucoup plus lisible
    conn.row_factory = sqlite3.Row
    # Active les clés étrangères (SQLite les désactive par défaut pour la compat)
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    conn = get_db()
    # executescript() exécute plusieurs instructions SQL d'un coup
    conn.executescript('''

        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,   -- toujours hashé, jamais en clair
            name     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS clients (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nom        TEXT NOT NULL,
            email      TEXT,
            entreprise TEXT,
            secteur    TEXT,
            notes      TEXT,
            statut     TEXT DEFAULT 'prospect',
            -- statuts possibles : prospect / actif / complété / archivé
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Une consultation = session de questionnaire remplie EN DIRECT avec le client.
        -- reponses est un JSON string : {"activite": "...", "budget": "..."}
        -- Stocker en JSON évite 10 colonnes pour 10 questions —
        -- si les questions changent, la structure DB reste la même.
        CREATE TABLE IF NOT EXISTS consultations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id  INTEGER NOT NULL,
            date       TEXT NOT NULL,
            reponses   TEXT,            -- JSON string
            notes      TEXT,            -- notes libres post-consultation
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

        -- ON DELETE CASCADE = si on supprime un client, ses consultations et contrats
        -- sont aussi supprimés automatiquement. Pas d'orphelins dans la DB.

        -- milestones = JSON array : [{titre, livrable, prix, statut}, ...]
        -- Stocker en JSON en Phase 1 est plus simple qu'une table séparée.
        -- En Phase 2, on pourrait normaliser si on veut des queries SQL sur les milestones.
        CREATE TABLE IF NOT EXISTS contrats (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id           INTEGER NOT NULL,
            scope               TEXT,   -- description du projet + périmètre
            milestones          TEXT,   -- JSON array
            conditions_paiement TEXT,
            politique_revisions TEXT,
            hors_scope          TEXT,   -- ce qui n'est PAS inclus (important!)
            timeline            TEXT,
            statut              TEXT DEFAULT 'draft',
            -- statuts : draft / envoyé / signé
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

        -- Réponses envoyées par le CLIENT lui-même via lien public /q/<client_id>
        -- UNIQUE sur client_id : un seul questionnaire par client
        CREATE TABLE IF NOT EXISTS questionnaires_client (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id    INTEGER NOT NULL UNIQUE,
            reponses     TEXT,   -- JSON string, mêmes champs que consultation
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

    ''')
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    # Vérifie si l'admin existe déjà — évite de créer en double au redémarrage
    already = conn.execute(
        "SELECT id FROM users WHERE username = 'naomie'"
    ).fetchone()

    if not already:
        # generate_password_hash() transforme le mot de passe en hash sécurisé.
        # On ne stocke JAMAIS un mot de passe en clair dans une DB.
        conn.execute(
            "INSERT INTO users (username, password, name) VALUES (?, ?, ?)",
            # Le mot de passe vient du .env (jamais hardcodé dans le code public)
        ('naomie', generate_password_hash(os.getenv('ADMIN_PASSWORD', 'change-me')), 'Naomie')
        )
        # Client de démo pour avoir quelque chose à voir au premier lancement
        conn.execute('''
            INSERT INTO clients (nom, email, entreprise, secteur, statut, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            'Jean Tremblay',
            'jean@foodtruck.ca',
            'Chez Jean Foodtruck',
            'Restauration mobile',
            'actif',
            'Premier client potentiel. Veut un site vitrine avec menu + localisation.'
        ))
        conn.commit()

    conn.close()
