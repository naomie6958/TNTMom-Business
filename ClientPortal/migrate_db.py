import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'portal.db')



def get_existing_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]



def add_column_if_missing(cursor, table_name, column_name, column_definition):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        print(f"   SKIP      : table '{table_name}' inexistante (sera créée par init_db)")
        return
    existing = get_existing_columns(cursor, table_name)
    if column_name not in existing:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )
        print(f"   AJOUTEE   : {table_name}.{column_name}")
    else:
        print(f"   EXISTANTE : {table_name}.{column_name}")



def main():
    print("=== MIGRATION portal.db ===\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # --- Point 1 : Contrats + Package Builder ---
        print("[contrats]")
        add_column_if_missing(cursor, "contrats", "package_snapshot", "TEXT")

        # --- Point 2 : Leads + token d'accès temporaire ---
        print("\n[leads]")
        add_column_if_missing(cursor, "leads", "access_token", "TEXT")
        add_column_if_missing(cursor, "leads", "token_expiry", "TEXT")

        # --- Point 3 : Consultation liées à la banque d'heures ---
        print("\n[consultations]")
        add_column_if_missing(cursor, "consultations", "banque_heures_id", "INTEGER")

        # --- Flag R&D sur clients ---
        print("\n[clients]")
        add_column_if_missing(cursor, "clients", "rnd", "INTEGER NOT NULL DEFAULT 0")

        # --- Point 3 : Nouvelle table banque d'heures ---
        print("\n[banque_heures]")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS banque_heures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                minutes_total INTEGER NOT NULL DEFAULT 300,
                minutes_utilisees INTEGER NOT NULL DEFAULT 0,
                date_achat TEXT,
                statut TEXT NOT NULL DEFAULT 'actif',
                stripe_payment_id TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        """)
        print("   TABLE CREEE : table banque_heures")

        # --- Nouvelle section : Revenus du ménage ---
        print("\n[household_revenues]")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS household_revenues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                amount REAL NOT NULL,
                date_received TEXT,
                is_taxable INTEGER DEFAULT 1,
                added_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   TABLE CREEE : table household_revenues")

        # --- Point 4 : Rôle des utilisateurs (admin/staff/client) ---
        print("\n[users]")
        add_column_if_missing(cursor, "users", "role", "TEXT DEFAULT 'client'")

        # --- Point 5 : Budget de Bill ---
        print("\n[budget]")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                type TEXT DEFAULT 'fixe',
                budget_mensuel REAL DEFAULT 0,
                couleur TEXT DEFAULT '#FF0090',
                ordre INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                montant REAL NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES budget_categories(id)
            )
        """)
        print("   TABLES CREEES : budget_categories, budget_expenses")

        # --- Gestionnaire de formulaires multi-clients (remplace Formspree) ---
        print("\n[client_form_submissions]")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_form_submissions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                client_site TEXT NOT NULL,
                data        TEXT NOT NULL,
                lu          INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        print("   TABLE CREEE : table client_form_submissions")

        # --- Underground Motorsport : domaine final + statut live (lance 2026-07-07) ---
        print("\n[portfolio_projets]")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_projets'")
        if cursor.fetchone():
            cursor.execute("""
                UPDATE portfolio_projets
                SET statut = 'live',
                    link = 'https://undergroundmotorsport.ca',
                    description = 'Site vitrine statique avec présentation des services, galerie photos et formulaire de diagnostic préliminaire (Formspree) qui remplace la prise de rendez-vous Messenger. Logo animé en filigrane avec effet de profondeur au scroll, phares avant du char animés en LED. Design dark et moderne. Hébergé sur GitHub Pages.',
                    tags = '["HTML","CSS","JavaScript","GitHub Pages","Formspree"]'
                WHERE nom = 'Underground Motorsport'
            """)
            print("   MISE A JOUR : Underground Motorsport -> live, undergroundmotorsport.ca")
        else:
            print("   SKIP      : table 'portfolio_projets' inexistante (sera créée par init_db)")

        conn.commit()
        print("\n=== MIGRATION TERMINEE AVEC SUCCES ===")
    
    except Exception as e:
        conn.rollback()
        print(f"\n  ERREUR : {e}")
        raise

    finally:
        conn.close()



if __name__ == "__main__":
    main()