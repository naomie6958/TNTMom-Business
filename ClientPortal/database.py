import sqlite3
import os
import uuid
import json
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Charge le .env pour que os.getenv() puisse lire ADMIN_PASSWORD et SECRET_KEY
load_dotenv()

# SQLite = base de données dans un seul fichier .db, pas de serveur séparé.
# Parfait pour une app mono-utilisateur ou petit trafic.
DB_PATH = os.path.join(os.path.dirname(__file__), 'portal.db')


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
            token      TEXT UNIQUE,  -- UUID pour le lien questionnaire public /q/<token>
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

        -- Fichiers uploadés par Naomie et visibles par le client dans son portail.
        -- nom_original = ce que l'utilisateur voit (ex: "devis-v2.pdf")
        -- nom_fichier  = ce qui est stocké sur le disque (uuid + nom sécurisé, évite les collisions)
        CREATE TABLE IF NOT EXISTS fichiers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id    INTEGER NOT NULL,
            nom_original TEXT NOT NULL,
            nom_fichier  TEXT NOT NULL,
            taille       INTEGER,   -- en bytes
            uploaded_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

    ''')
    conn.commit()
    conn.close()


def migrate_db():
    conn = get_db()

    # ALTER TABLE ajoute une colonne à une table existante.
    # Si la colonne existe déjà (redémarrage), SQLite lève une erreur — on l'ignore.
    try:
        # SQLite ne supporte pas UNIQUE dans ALTER TABLE ADD COLUMN.
        # L'unicité est garantie de fait par uuid.uuid4() — collision impossible en pratique.
        conn.execute("ALTER TABLE clients ADD COLUMN token TEXT")
        conn.commit()
    except Exception:
        pass  # Colonne déjà présente, rien à faire

    try:
        # password est nullable : NULL = pas de compte client encore créé.
        # On ne crée le compte que quand Naomie décide d'en donner l'accès.
        conn.execute("ALTER TABLE clients ADD COLUMN password TEXT")
        conn.commit()
    except Exception:
        pass  # Colonne déjà présente, rien à faire

    # Génère un token UUID pour chaque client qui n'en a pas encore
    # (clients créés avant la migration)
    existing = conn.execute("SELECT id FROM clients WHERE token IS NULL").fetchall()
    for row in existing:
        conn.execute(
            "UPDATE clients SET token = ? WHERE id = ?",
            (str(uuid.uuid4()), row['id'])
        )
    if existing:
        conn.commit()

    # Traduit les anciens statuts anglais des milestones en français dans tous les contrats.
    # Les valeurs 'pending' et 'en_cours' viennent de la Phase 1 — on les remplace une fois.
    statut_map = {'pending': 'en attente', 'en_cours': 'en cours'}
    contrats = conn.execute(
        'SELECT id, milestones FROM contrats WHERE milestones IS NOT NULL'
    ).fetchall()
    for contrat in contrats:
        try:
            milestones = json.loads(contrat['milestones'])
            changed = False
            for m in milestones:
                if m.get('statut') in statut_map:
                    m['statut'] = statut_map[m['statut']]
                    changed = True
            if changed:
                conn.execute(
                    'UPDATE contrats SET milestones = ? WHERE id = ?',
                    (json.dumps(milestones, ensure_ascii=False), contrat['id'])
                )
        except (json.JSONDecodeError, KeyError):
            pass
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
