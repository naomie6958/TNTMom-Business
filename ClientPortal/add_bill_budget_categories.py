import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'portal.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

categories = [
    ("Loyer", "fixe", 825.00, "#FF6600", 1),
    ("Épicerie", "variable", 600.00, "#00CED1", 2),
    ("Autres", "variable", 500.00, "#FFD700", 3),
]

for nom, type_cat, budget, couleur, ordre in categories:
    existing = cursor.execute(
        "SELECT id FROM budget_categories WHERE nom = ?", (nom,)
    ).fetchone()
    
    if not existing:
        cursor.execute(
            "INSERT INTO budget_categories (nom, type, budget_mensuel, couleur, ordre) VALUES (?, ?, ?, ?, ?)",
            (nom, type_cat, budget, couleur, ordre)
        )
        print(f"✓ {nom} créée")

conn.commit()
conn.close()
print("✓ Catégories initialisées!")