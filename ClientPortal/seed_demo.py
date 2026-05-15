import json, datetime
from database import get_db
from werkzeug.security import generate_password_hash

conn = get_db()
today = datetime.date.today()

# Réutilise le premier client existant, ou crée Annie McMahon
import uuid
existing = conn.execute("SELECT id FROM clients LIMIT 1").fetchone()
if existing:
    client_id = existing['id']
    conn.execute(
        "UPDATE clients SET nom=?, email=?, entreprise=?, secteur=?, statut=?, notes=? WHERE id=?",
        ('Annie McMahon', 'annie@chopperbrgr.ca', 'Chopper Burger', 'Restauration',
         'actif', 'Cliente depuis mars 2026. Projet site vitrine + logo.', client_id)
    )
else:
    cur = conn.execute(
        "INSERT INTO clients (nom, email, entreprise, secteur, statut, notes, token) VALUES (?,?,?,?,?,?,?)",
        ('Annie McMahon', 'annie@chopperbrgr.ca', 'Chopper Burger', 'Restauration',
         'actif', 'Cliente depuis mars 2026. Projet site vitrine + logo.', str(uuid.uuid4()))
    )
    client_id = cur.lastrowid
conn.commit()

# ── NETTOYAGE DONNÉES EXISTANTES ──────────────────────────────────────────────
conn.execute('DELETE FROM contrats WHERE client_id = ?', (client_id,))
conn.execute('DELETE FROM factures WHERE client_id = ?', (client_id,))
conn.execute('DELETE FROM messages_client WHERE client_id = ?', (client_id,))
conn.execute('DELETE FROM consultations WHERE client_id = ?', (client_id,))
conn.execute('DELETE FROM questionnaires_client WHERE client_id = ?', (client_id,))
conn.commit()

# ── PROJET 1 : Site web (en cours) ───────────────────────────────────────────
def d(offset): return (today + datetime.timedelta(days=offset)).isoformat()

milestones_1 = json.dumps([
    {'titre': 'Moodboard + palette',             'livrable': 'PDF moodboard',             'prix': '250', 'statut': 'payé',       'date': d(-42)},
    {'titre': 'Design Figma (desktop + mobile)', 'livrable': 'Fichier Figma complet',     'prix': '500', 'statut': 'payé',       'date': d(-20)},
    {'titre': 'Integration HTML/CSS',            'livrable': 'Site statique fonctionnel', 'prix': '400', 'statut': 'livré',      'date': d(-4)},
    {'titre': 'Contenu & SEO de base',           'livrable': 'Textes + balises meta',     'prix': '150', 'statut': 'en cours',   'date': d(14)},
    {'titre': 'Mise en ligne + formation',       'livrable': 'Site live + tutoriel',      'prix': '200', 'statut': 'en attente', 'date': d(30)},
], ensure_ascii=False)

cur = conn.execute(
    'INSERT INTO contrats (client_id, nom, scope, milestones, conditions_paiement, statut, signed_at) VALUES (?,?,?,?,?,?,?)',
    (client_id, 'Site web Chopper Burger',
     'Creation complete du site vitrine. 5 pages : Accueil, Menu, A propos, Galerie, Contact. Design + integration + mise en ligne Netlify.',
     milestones_1,
     '50% au debut, 25% apres Figma, 25% a la mise en ligne.',
     'signe',
     (today - datetime.timedelta(days=45)).isoformat())
)
contrat1_id = cur.lastrowid

# ── PROJET 2 : Logo (complete) ────────────────────────────────────────────────
milestones_2 = json.dumps([
    {'titre': 'Exploration 3 concepts',   'livrable': 'PDF concepts',           'prix': '200', 'statut': 'payé', 'date': d(-88)},
    {'titre': 'Revisions + finalisation', 'livrable': 'Logo final vectoriel',   'prix': '150', 'statut': 'payé', 'date': d(-62)},
    {'titre': 'Charte graphique mini',    'livrable': 'PDF couleurs + typos',   'prix': '100', 'statut': 'payé', 'date': d(-52)},
], ensure_ascii=False)

cur = conn.execute(
    'INSERT INTO contrats (client_id, nom, scope, milestones, conditions_paiement, statut, signed_at) VALUES (?,?,?,?,?,?,?)',
    (client_id, 'Logo & identite visuelle',
     'Creation du logo Chopper Burger et mini charte graphique. 3 concepts initiaux, 2 rondes de revisions incluses.',
     milestones_2,
     '100% a la livraison finale.',
     'signe',
     (today - datetime.timedelta(days=90)).isoformat())
)
contrat2_id = cur.lastrowid

# ── FACTURES ─────────────────────────────────────────────────────────────────
factures = [
    (client_id, contrat2_id, f'{today.year}-001', 'Exploration 3 concepts',           200.0, 'payee',    (today - datetime.timedelta(days=88)).isoformat(), (today - datetime.timedelta(days=85)).isoformat()),
    (client_id, contrat2_id, f'{today.year}-002', 'Revisions + finalisation',          150.0, 'payee',    (today - datetime.timedelta(days=60)).isoformat(), (today - datetime.timedelta(days=58)).isoformat()),
    (client_id, contrat2_id, f'{today.year}-003', 'Charte graphique mini',             100.0, 'payee',    (today - datetime.timedelta(days=55)).isoformat(), (today - datetime.timedelta(days=52)).isoformat()),
    (client_id, contrat1_id, f'{today.year}-004', 'Moodboard + palette',              250.0, 'payee',    (today - datetime.timedelta(days=44)).isoformat(), (today - datetime.timedelta(days=40)).isoformat()),
    (client_id, contrat1_id, f'{today.year}-005', 'Design Figma (desktop + mobile)',   500.0, 'payee',    (today - datetime.timedelta(days=25)).isoformat(), (today - datetime.timedelta(days=22)).isoformat()),
    (client_id, contrat1_id, f'{today.year}-006', 'Integration HTML/CSS',              400.0, 'envoyee', (today - datetime.timedelta(days=5)).isoformat(),  None),
]

for f in factures:
    conn.execute(
        'INSERT INTO factures (client_id, contrat_id, numero, milestone_titre, montant, statut, date_emission, date_paiement) VALUES (?,?,?,?,?,?,?,?)',
        f
    )

# ── MESSAGES ─────────────────────────────────────────────────────────────────
messages = [
    ('Progression du site',
     "Bonjour Naomie! Je voulais savoir ou en est l'integration HTML. Est-ce que je peux voir une preversion quelque part?",
     "Salut Annie! Oui, j'ai mis une preversion en ligne sur Netlify. Le design est integre a environ 80%, il reste la section galerie et le formulaire de contact.",
     (today - datetime.timedelta(days=8)).isoformat() + 'T14:22:00',
     (today - datetime.timedelta(days=7)).isoformat() + 'T09:15:00'),
    ('Photos pour la galerie',
     "Pour la section galerie, est-ce que tu as besoin de photos en haute resolution? J'en ai des super belles prises par un photographe.",
     "Parfait! Oui envoie-moi les via l'onglet Fichiers partages. Idealement des JPG entre 2 et 5 MB chacun.",
     (today - datetime.timedelta(days=6)).isoformat() + 'T11:30:00',
     (today - datetime.timedelta(days=5)).isoformat() + 'T16:45:00'),
    ('Question sur le SEO',
     "C'est quoi exactement le SEO de base que tu vas faire? Est-ce que ca va m'aider a apparaitre sur Google?",
     None,
     (today - datetime.timedelta(days=1)).isoformat() + 'T18:05:00',
     None),
]

for sujet, message, reponse, created_at, repondu_at in messages:
    conn.execute(
        'INSERT INTO messages_client (client_id, sujet, message, lu, reponse, repondu_at, created_at) VALUES (?,?,?,?,?,?,?)',
        (client_id, sujet, message, 1, reponse, repondu_at, created_at)
    )

# ── QUESTIONNAIRE CLIENT ──────────────────────────────────────────────────────
reponses_q = json.dumps({
    'activite': 'Restaurant specialise en burgers artisanaux. Livraisons et evenements prives.',
    'clientele': 'Jeunes adultes 18-35 ans, familles le weekend.',
    'pourquoi_maintenant': 'Nouveau menu, saison estivale approche.',
    'type_projet': 'Site vitrine avec menu en ligne et formulaire de reservation.',
    'vision': 'Moderne et appetissant. Grandes photos de nourriture. Ambiance dark avec accents rouge/or.',
    'budget': '1 500 $ - 2 500 $',
    'deadline': '1er juin 2026',
    'assets': 'Logo cree avec vous. Photos professionnelles disponibles.',
    'acces_technique': 'Domaine Namecheap. Hebergement Netlify.',
    'implication': 'Presente pour les grandes decisions, delègue le reste.',
}, ensure_ascii=False)
conn.execute(
    'INSERT INTO questionnaires_client (client_id, reponses) VALUES (?,?)',
    (client_id, reponses_q)
)

# ── CONSULTATION ──────────────────────────────────────────────────────────────
reponses_c = json.dumps({
    'activite': 'Restaurant burgers artisanaux, livraison et evenements.',
    'clientele': 'Millennials et familles.',
    'pourquoi_maintenant': 'Nouveau menu + saison estivale.',
    'type_projet': 'Site vitrine + menu interactif.',
    'vision': 'Dark, moderne, grandes photos.',
    'budget': '2 000 $',
    'deadline': 'Juin 2026',
    'assets': 'Photos dispo, logo fait.',
    'acces_technique': 'Namecheap + Netlify.',
    'implication': 'Impliquee pour le design, fait confiance pour le technique.',
}, ensure_ascii=False)
conn.execute(
    'INSERT INTO consultations (client_id, date, reponses, notes) VALUES (?,?,?,?)',
    (client_id,
     (today - datetime.timedelta(days=50)).isoformat(),
     reponses_c,
     "Tres bonne energie. Annie sait ce qu'elle veut. Moodboard Pinterest fourni. Budget confirme 2 000 $. Demarrage immediat.")
)

conn.commit()
conn.close()
print('Demo data seeded OK')
print(f'  Contrats: 2  Factures: 6  Messages: 3  Questionnaire: 1  Consultation: 1')
