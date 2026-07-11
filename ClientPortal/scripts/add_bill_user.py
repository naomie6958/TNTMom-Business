import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'portal.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

#Vérifie si Bill existe déjà
existing = cursor.execute("SELECT id FROM users WHERE username = 'bill'").fetchone()

if existing:
    print("Bill existe déjà. Mise à jour du rôle à 'staff'...")
    cursor.execute("UPDATE users SET role = 'staff' WHERE username = 'bill'")
else:
    print("Création de Bill...")
    # Tu dois définir un mot de passe sécurisé pour Bill
    bill_password = "Chbi@2203!"
    cursor.execute(
        "INSERT INTO users (username, password, name, role) VALUES (?, ?, ?, ?)",
        ("bill", generate_password_hash(bill_password), "Bill", "staff")
    )

conn.commit()
conn.close()
print("✓ Bill est prêt!")