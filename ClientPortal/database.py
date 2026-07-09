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

# --- CONFIGURATION DU CHEMIN DE LA BASE DE DONNÉES ---
RAILWAY_DIR = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')

if RAILWAY_DIR:
    # En production sur Railway, on stocke la DB sur le disque persistant (Volume)
    DB_PATH = os.path.join(RAILWAY_DIR, 'portal.db')
else:
    # En local sur l'ordinateur de Naomie, on garde le comportement habituel
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portal.db')

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
            deleted    INTEGER DEFAULT 0,
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
            nom                 TEXT,
            scope               TEXT,
            milestones          TEXT,
            conditions_paiement TEXT,
            politique_revisions TEXT,
            hors_scope          TEXT,
            timeline            TEXT,
            statut              TEXT DEFAULT 'draft',
            signed_at           TEXT,
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

        -- Commentaires liés à un fichier spécifique (collaboration)
        CREATE TABLE IF NOT EXISTS fichier_commentaires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fichier_id INTEGER NOT NULL,
            auteur_type TEXT NOT NULL, -- 'client' ou 'admin'
            auteur_nom TEXT NOT NULL,
            commentaire TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(fichier_id) REFERENCES fichiers(id) ON DELETE CASCADE
        );

        -- Messages envoyés par le client depuis son portail vers Naomie.
        -- lu = 0 tant que Naomie n'a pas ouvert la fiche client.
        CREATE TABLE IF NOT EXISTS messages_client (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id  INTEGER NOT NULL,
            sujet      TEXT,
            message    TEXT NOT NULL,
            lu         INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS client_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS factures (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id       INTEGER NOT NULL,
            contrat_id      INTEGER,
            numero          TEXT,
            milestone_titre TEXT,
            description     TEXT,
            montant         REAL NOT NULL DEFAULT 0,
            statut          TEXT DEFAULT 'envoyée',
            date_emission   TEXT NOT NULL,
            date_paiement   TEXT,
            deleted         INTEGER DEFAULT 0,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS formulaires (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            titre       TEXT NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            actif       INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS formulaire_questions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            formulaire_id INTEGER NOT NULL,
            ordre         INTEGER DEFAULT 0,
            titre         TEXT NOT NULL,
            sous_titre    TEXT,
            type          TEXT DEFAULT 'texte',
            options       TEXT,   -- lignes séparées par saut de ligne (choix et cases)
            requis        INTEGER DEFAULT 0,
            FOREIGN KEY(formulaire_id) REFERENCES formulaires(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS formulaire_reponses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            formulaire_id INTEGER NOT NULL,
            client_id     INTEGER NOT NULL,
            reponses      TEXT NOT NULL,
            submitted_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(formulaire_id) REFERENCES formulaires(id) ON DELETE CASCADE,
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
        conn.execute("ALTER TABLE clients ADD COLUMN last_login_at TEXT")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS client_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        )''')
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS fichier_commentaires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fichier_id INTEGER NOT NULL,
            auteur_type TEXT NOT NULL,
            auteur_nom TEXT NOT NULL,
            commentaire TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(fichier_id) REFERENCES fichiers(id) ON DELETE CASCADE
        )''')
        conn.commit()
    except Exception:
        pass

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

    try:
        # Ajout du rôle pour différencier l'admin principal (Naomie) du staff (Bill)
        # Par défaut, on met 'admin' pour que ton compte principal fonctionne tout de suite.
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'admin'")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE messages_client ADD COLUMN reponse TEXT")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE messages_client ADD COLUMN repondu_at TEXT")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE messages_client ADD COLUMN lu_client INTEGER DEFAULT 1")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE contrats ADD COLUMN nom TEXT")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE contrats ADD COLUMN signed_at TEXT")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE formulaire_questions ADD COLUMN prefill_field TEXT")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS leads (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nom        TEXT NOT NULL,
            email      TEXT,
            message    TEXT,
            lu         INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )''')
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE fichiers ADD COLUMN milestone_index INTEGER")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE clients ADD COLUMN demo INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE clients ADD COLUMN deleted INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE clients ADD COLUMN rnd INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS tarifs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            titre      TEXT NOT NULL,
            description TEXT,
            prix       REAL,
            unite      TEXT DEFAULT '/ projet',
            inclus     TEXT,
            non_inclus TEXT,
            actif      INTEGER DEFAULT 1,
            ordre      INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )''')
        conn.commit()
    except Exception:
        pass

    conn.executescript('''
        CREATE TABLE IF NOT EXISTS factures (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id       INTEGER NOT NULL,
            contrat_id      INTEGER,
            numero          TEXT,
            milestone_titre TEXT,
            description     TEXT,
            montant         REAL NOT NULL DEFAULT 0,
            statut          TEXT DEFAULT 'envoyée',
            date_emission   TEXT NOT NULL,
            date_paiement   TEXT,
            deleted         INTEGER DEFAULT 0,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS formulaires (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            titre       TEXT NOT NULL,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            actif       INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS formulaire_questions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            formulaire_id INTEGER NOT NULL,
            ordre         INTEGER DEFAULT 0,
            titre         TEXT NOT NULL,
            sous_titre    TEXT,
            type          TEXT DEFAULT 'texte',
            options       TEXT,
            requis        INTEGER DEFAULT 0,
            FOREIGN KEY(formulaire_id) REFERENCES formulaires(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS formulaire_reponses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            formulaire_id INTEGER NOT NULL,
            client_id     INTEGER NOT NULL,
            reponses      TEXT NOT NULL,
            submitted_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(formulaire_id) REFERENCES formulaires(id) ON DELETE CASCADE,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS client_formulaires (
            client_id     INTEGER NOT NULL,
            formulaire_id INTEGER NOT NULL,
            assigned_at   TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (client_id, formulaire_id),
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
            FOREIGN KEY(formulaire_id) REFERENCES formulaires(id) ON DELETE CASCADE
        );
    ''')

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

    # Tables punch d'heures
    try:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS categories_temps (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nom         TEXT NOT NULL,
                description TEXT,
                taux_min    REAL DEFAULT 0,
                taux_max    REAL DEFAULT 0,
                couleur     TEXT DEFAULT '#d94fbd',
                actif       INTEGER DEFAULT 1,
                ordre       INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS entrees_temps (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id         INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                contrat_id        INTEGER REFERENCES contrats(id) ON DELETE SET NULL,
                milestone_titre   TEXT,
                categorie_id      INTEGER NOT NULL REFERENCES categories_temps(id),
                description       TEXT,
                date              TEXT NOT NULL,
                heure_debut       TEXT,
                heure_fin         TEXT,
                duree_minutes     INTEGER DEFAULT 0,
                mode              TEXT DEFAULT 'manuel',
                type_facturation  TEXT DEFAULT 'horaire',
                taux_applique     REAL,
                created_at        TEXT DEFAULT (datetime('now'))
            );
        ''')
        conn.commit()
    except Exception:
        pass

    try:
        if conn.execute('SELECT COUNT(*) FROM categories_temps').fetchone()[0] == 0:
            cats = [
                ('Développement & Architecture', 'Code Python/Flask, intégration API, base de données, déploiement, debug complexe', 70.0, 85.0, '#d94fbd', 1),
                ('Design UI/UX & Conception', 'Maquettes, design responsive, architecture information, graphisme, tests UX', 60.0, 70.0, '#87CEEB', 2),
                ('Intégration & Maintenance', 'Intégration contenu client, CSS/HTML, mises à jour, formulaires standards', 50.0, 60.0, '#D4AF37', 3),
                ('Gestion, Admin & Consultation', 'Rencontres clients, appels, devis, support courriel, gestion de projet', 45.0, 55.0, '#4CAF50', 4),
            ]
            for nom, desc, tmin, tmax, couleur, ordre in cats:
                conn.execute(
                    'INSERT INTO categories_temps (nom, description, taux_min, taux_max, couleur, ordre) VALUES (?,?,?,?,?,?)',
                    (nom, desc, tmin, tmax, couleur, ordre)
                )
            conn.commit()
    except Exception:
        pass

    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS packages (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            nom                 TEXT NOT NULL,
            client_id           INTEGER NOT NULL,
            heures_dev          REAL DEFAULT 0,
            heures_design       REAL DEFAULT 0,
            heures_integration  REAL DEFAULT 0,
            heures_admin        REAL DEFAULT 0,
            marge               INTEGER DEFAULT 0,
            prix_final          REAL NOT NULL,
            created_at          TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        )''')
        conn.commit()
    except Exception:
        pass

    # Ajoute la date d'échéance sur les factures (pour détecter les retards de paiement)
    try:
        conn.execute("ALTER TABLE factures ADD COLUMN date_echeance TEXT")
        conn.commit()
    except Exception:
        pass  # Colonne déjà présente

    # Ajout de la colonne deleted pour le soft-delete des factures
    try:
        conn.execute("ALTER TABLE factures ADD COLUMN deleted INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    # Table des dépenses d'entreprise (abonnements, outils, domaines, etc.)
    # Permet de calculer le revenu net et la provision fiscale réelle.
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS depenses (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            date                 TEXT NOT NULL,
            description          TEXT NOT NULL,
            montant              REAL NOT NULL DEFAULT 0,
            categorie            TEXT DEFAULT 'Autre',
            fichier_nom_original TEXT,
            fichier_nom_stocke   TEXT,
            fichier_taille       INTEGER,
            created_at           TEXT DEFAULT (datetime('now'))
        )''')
        conn.commit()
    except Exception:
        pass

    # Colonnes fichier ajoutées après coup sur une table depenses déjà existante
    # (ALTER TABLE lève une erreur si la colonne existe déjà — on l'ignore).
    try:
        conn.execute('ALTER TABLE depenses ADD COLUMN fichier_nom_original TEXT')
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute('ALTER TABLE depenses ADD COLUMN fichier_nom_stocke TEXT')
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute('ALTER TABLE depenses ADD COLUMN fichier_taille INTEGER')
        conn.commit()
    except Exception:
        pass

    # Tables V2: Banque d'heures, Revenus ménage, Budget de Bill
    try:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS banque_heures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                minutes_total INTEGER NOT NULL DEFAULT 300,
                minutes_utilisees INTEGER NOT NULL DEFAULT 0,
                date_achat TEXT,
                statut TEXT NOT NULL DEFAULT 'actif',
                stripe_payment_id TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS household_revenues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                amount REAL NOT NULL,
                date_received TEXT,
                is_taxable INTEGER DEFAULT 1,
                added_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS budget_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                type TEXT DEFAULT 'fixe',
                budget_mensuel REAL DEFAULT 0,
                couleur TEXT DEFAULT '#FF0090',
                ordre INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS budget_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                montant REAL NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES budget_categories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS client_form_submissions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                client_site TEXT NOT NULL,
                data        TEXT NOT NULL,
                lu          INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );
        ''')
        conn.commit()
    except Exception:
        pass

    # Ajout des colonnes de la V2 pour éviter les futurs crashs
    for table, col, col_type in [
        ('contrats', 'package_snapshot', 'TEXT'),
        ('leads', 'access_token', 'TEXT'),
        ('leads', 'token_expiry', 'TEXT'),
        ('consultations', 'banque_heures_id', 'INTEGER')
    ]:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            conn.commit()
        except Exception:
            pass

    # Normalise les statuts de factures sans accent vers les valeurs canoniques.
    # Les anciennes données démo étaient seedées avec 'payee'/'envoyee' (sans é).
    try:
        conn.execute("UPDATE factures SET statut = 'payée'   WHERE statut IN ('payee', 'pay\xe9e')")
        conn.execute("UPDATE factures SET statut = 'envoyée' WHERE statut IN ('envoyee', 'envoy\xe9e', 'envoy\xc3\xa9e')")
        conn.commit()
    except Exception:
        pass

    # Table portfolio - cartes de projets pour tntm.ca
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS portfolio_projets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nom         TEXT NOT NULL,
            tagline     TEXT,
            description TEXT,
            tags        TEXT,
            statut      TEXT DEFAULT 'en-cours',
            couleur     TEXT DEFAULT 'magenta',
            image_url   TEXT,
            link        TEXT,
            ordre       INTEGER DEFAULT 0,
            actif       INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now'))
        )''')
        conn.commit()
    except Exception:
        pass

    # Seed initial des projets portfolio (si table vide)
    try:
        if conn.execute('SELECT COUNT(*) FROM portfolio_projets').fetchone()[0] == 0:
            projets = [
                ('Chopper Burger', 'Site vitrine pour un casse-croûte de St-Rosaire', 'Site one-page Flask avec menu interactif par catégorie, galerie photos, infos et design dark orange Harley Davidson. Mobile friendly, déployé sur Railway.', '["Python","Flask","Jinja2","CSS","Railway"]', 'live', 'orange', 'images/Screenshots/2026-05/chopperburger-desktop.png', 'https://chopperburger.tntm.ca', 1),
                ('ClientPortal', 'Back-office freelance déployé en production', 'Gestion clients, contrats avec timeline milestones, facturation automatique, portail client sécurisé, messagerie intégrée, formulaires personnalisés et envoi de factures par courriel. Premier client actif.', '["Python","Flask","SQLite","Gmail SMTP","Railway"]', 'live', 'magenta', 'images/Screenshots/2026-05/clientportal-fiche.png', 'clientportal.html', 2),
                ('Family Dashboard', 'App homeschool familiale avec IA', 'Calendrier partagé, suivi homeschool, système de points et récompenses pour les enfants, et app d\'anglais avec exercices générés par Claude AI. 4 profils, 4 thèmes visuels. Déployé sur Railway.', '["Python","Flask","Claude API","SQLite","Railway"]', 'live', 'bleu', 'images/Screenshots/2026-05/familydashboard-enfant.png', 'familydashboard.html', 3),
                ('Underground Motorsport', 'Site vitrine pour atelier mécanique spécialisé', 'Site vitrine statique avec présentation des services, galerie photos et formulaire de diagnostic préliminaire (Formspree) qui remplace la prise de rendez-vous Messenger. Logo animé en filigrane avec effet de profondeur au scroll, phares avant du char animés en LED. Design dark et moderne. Hébergé sur GitHub Pages.', '["HTML","CSS","JavaScript","GitHub Pages","Formspree"]', 'live', 'rouge', 'images/Screenshots/UndergroundMotorsport_Screenshot.png', 'https://undergroundmotorsport.ca', 4),
            ]
            for p in projets:
                conn.execute(
                    'INSERT INTO portfolio_projets (nom, tagline, description, tags, statut, couleur, image_url, link, ordre) VALUES (?,?,?,?,?,?,?,?,?)',
                    p
                )
            conn.commit()
    except Exception:
        pass

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
