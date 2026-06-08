#!/usr/bin/env python3
"""Migration fiscale : ajoute la table household_revenues pour le suivi budgétaire familial."""

from database import get_db


def migrate_fiscal():
    """Crée la table household_revenues si elle n'existe pas."""
    conn = get_db()

    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS household_revenues (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                label            TEXT NOT NULL,
                amount           REAL NOT NULL DEFAULT 0,
                date_received    TEXT NOT NULL,
                is_taxable       INTEGER DEFAULT 1,
                added_by         TEXT NOT NULL,
                created_at       TEXT DEFAULT (datetime('now'))
            )
        ''')
        conn.commit()
        print("✓ Table household_revenues créée ou déjà présente")
    except Exception as e:
        print(f"✗ Erreur migration: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    migrate_fiscal()
