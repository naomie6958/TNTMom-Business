import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'portal.db')



def get_existing_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]



def add_column_if_missing(cursor, table_name, column_name, column_definition):
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