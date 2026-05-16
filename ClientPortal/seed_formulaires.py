"""
Run once on PythonAnywhere to seed the Formulaires section with
the questionnaire de premiere consultation as a reusable template.

  cd /home/naomie6958/TNTMom-Business/ClientPortal
  python seed_formulaires.py
"""

from database import get_db

TITRE = "Questionnaire de premiere consultation"
DESCRIPTION = "Quelques questions pour mieux cerner ton projet avant notre premiere rencontre."

QUESTIONS = [
    # (ordre, titre, sous_titre, type, options, requis, prefill_field)
    (0,  "Decris ton activite ou ton projet en quelques phrases.",
         "C'est quoi ce que tu fais / ce que tu veux creer ?",
         "paragraphe", None, 1, "questionnaire.activite"),
    (1,  "A qui s'adresse ton projet ? Qui est ta clientele cible ?",
         None,
         "paragraphe", None, 0, "questionnaire.clientele"),
    (2,  "Pourquoi maintenant ?",
         "Qu'est-ce qui t'amene a vouloir avancer sur ce projet en ce moment ?",
         "paragraphe", None, 0, "questionnaire.pourquoi_maintenant"),
    (3,  "Quel type de projet cherches-tu ?",
         None,
         "choix",
         "Site vitrine\nBoutique en ligne\nApplication web\nAutre",
         1, "questionnaire.type_projet"),
    (4,  "As-tu une vision de l'image ou du style que tu veux projeter ?",
         "Couleurs, references, moodboard, exemples de sites que tu aimes...",
         "paragraphe", None, 0, "questionnaire.vision"),
    (5,  "Quel est ton budget approximatif ?",
         None,
         "choix",
         "Moins de 500 $\n500 $ - 1 000 $\n1 000 $ - 2 500 $\n2 500 $ - 5 000 $\nPlus de 5 000 $\nA discuter",
         0, "questionnaire.budget"),
    (6,  "As-tu un echeancier ou une date cible en tete ?",
         None,
         "texte", None, 0, "questionnaire.deadline"),
    (7,  "As-tu deja des contenus ? (textes, photos, logo, etc.)",
         None,
         "paragraphe", None, 0, "questionnaire.assets"),
    (8,  "As-tu des acces techniques existants ?",
         "Nom de domaine, hebergement, compte Google Analytics, etc.",
         "paragraphe", None, 0, "questionnaire.acces_technique"),
    (9,  "Quel niveau d'implication souhaites-tu dans le projet ?",
         None,
         "choix",
         "Je te laisse carte blanche\nJe veux etre consulte(e) aux etapes cles\nJe veux participer activement",
         0, "questionnaire.implication"),
]

def run():
    conn = get_db()

    # Check if already exists
    existing = conn.execute(
        "SELECT id FROM formulaires WHERE titre = ?", (TITRE,)
    ).fetchone()

    if existing:
        fid = existing['id']
        print(f"Formulaire deja present (id={fid}). Mise a jour des questions...")
        conn.execute("DELETE FROM formulaire_questions WHERE formulaire_id = ?", (fid,))
    else:
        conn.execute(
            "INSERT INTO formulaires (titre, description, actif) VALUES (?, ?, 1)",
            (TITRE, DESCRIPTION)
        )
        conn.commit()
        fid = conn.execute(
            "SELECT id FROM formulaires WHERE titre = ?", (TITRE,)
        ).fetchone()['id']
        print(f"Formulaire cree (id={fid})")

    for ordre, titre, sous_titre, type_, options, requis, prefill_field in QUESTIONS:
        conn.execute(
            """INSERT INTO formulaire_questions
               (formulaire_id, ordre, titre, sous_titre, type, options, requis, prefill_field)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (fid, ordre, titre, sous_titre, type_, options, requis, prefill_field)
        )

    conn.commit()
    conn.close()
    print(f"OK - {len(QUESTIONS)} questions inserees.")

if __name__ == '__main__':
    run()
