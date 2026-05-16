"""
Peuple le compte "Démo Client" pour la démo publique du portail.

Credentials portail : demo@tntm.ca / demo2026
Lancer depuis le dossier ClientPortal :  python seed_portail_demo.py
"""
import json, datetime, uuid
from database import get_db
from werkzeug.security import generate_password_hash

conn  = get_db()
today = datetime.date.today()
def d(offset): return (today + datetime.timedelta(days=offset)).isoformat()

# ── Trouver le client démo ────────────────────────────────────────────────────
demo = conn.execute("SELECT id FROM clients WHERE nom = 'Démo Client'").fetchone()
if not demo:
    demo = conn.execute("SELECT id FROM clients WHERE nom LIKE '%emo%'").fetchone()
if not demo:
    print("ERREUR : aucun client 'Demo Client' trouve. Cree-le dans l'admin d'abord.")
    conn.close()
    exit(1)

client_id = demo['id']
print(f'Client demo trouve : id={client_id}')

# ── Mettre à jour les infos du client ────────────────────────────────────────
conn.execute("""
    UPDATE clients
    SET nom=?, email=?, password=?, entreprise=?, secteur=?, statut=?, notes=?
    WHERE id=?
""", (
    'Sophie Tremblay',
    'demo@tntm.ca',
    generate_password_hash('demo2026'),
    'Studio Lumière',
    'Photographie',
    'actif',
    'Compte démo public — données fictives. Ne pas supprimer.',
    client_id
))
conn.commit()

# ── Nettoyage ─────────────────────────────────────────────────────────────────
for table in ('contrats', 'factures', 'messages_client', 'consultations', 'questionnaires_client'):
    conn.execute(f'DELETE FROM {table} WHERE client_id = ?', (client_id,))
conn.commit()

# ── PROJET : Site vitrine + réservations ─────────────────────────────────────
milestones = json.dumps([
    {
        'titre':    'Moodboard & direction artistique',
        'livrable': 'PDF moodboard + palette couleurs',
        'prix':     '300',
        'statut':   'payé',
        'date':     d(-55),
    },
    {
        'titre':    'Design Figma (desktop + mobile)',
        'livrable': 'Maquettes complètes toutes sections',
        'prix':     '600',
        'statut':   'payé',
        'date':     d(-28),
    },
    {
        'titre':    'Intégration HTML/CSS + galerie',
        'livrable': 'Site statique fonctionnel',
        'prix':     '500',
        'statut':   'livré',
        'date':     d(-8),
    },
    {
        'titre':    'Module réservation en ligne',
        'livrable': 'Formulaire réservation + confirmation courriel',
        'prix':     '400',
        'statut':   'en cours',
        'date':     d(15),
    },
    {
        'titre':    'Mise en ligne + formation',
        'livrable': 'Site live + tutoriel vidéo',
        'prix':     '200',
        'statut':   'en attente',
        'date':     d(32),
    },
], ensure_ascii=False)

cur = conn.execute(
    'INSERT INTO contrats (client_id, nom, scope, milestones, conditions_paiement, statut, signed_at) VALUES (?,?,?,?,?,?,?)',
    (
        client_id,
        'Site vitrine Studio Lumière',
        'Création complète du site vitrine photographique. Pages : Accueil, Portfolio, Services, À propos, Contact. '
        'Galerie filtrée par catégorie, module de réservation de séances en ligne, optimisation SEO de base.',
        milestones,
        '40 % à la signature, 30 % après les maquettes Figma, 30 % à la mise en ligne.',
        'signe',
        d(-58),
    )
)
contrat_id = cur.lastrowid
conn.commit()

# ── FACTURES ─────────────────────────────────────────────────────────────────
factures = [
    (client_id, contrat_id, f'{today.year}-007', 'Moodboard & direction artistique',  300.0, 'payee',   d(-54), d(-50)),
    (client_id, contrat_id, f'{today.year}-008', 'Design Figma (desktop + mobile)',   600.0, 'payee',   d(-27), d(-24)),
    (client_id, contrat_id, f'{today.year}-009', 'Intégration HTML/CSS + galerie',    500.0, 'envoyee', d(-9),  None),
]
for f in factures:
    conn.execute(
        'INSERT INTO factures (client_id, contrat_id, numero, milestone_titre, montant, statut, date_emission, date_paiement) VALUES (?,?,?,?,?,?,?,?)',
        f
    )
conn.commit()

# ── MESSAGES ─────────────────────────────────────────────────────────────────
messages = [
    (
        'Retour sur le moodboard',
        "Bonjour Naomie ! J'ai regardé le moodboard et j'adore la direction. "
        "Est-ce qu'on peut jouer un peu plus avec le noir et or pour la palette ?",
        "Absolument ! J'ai ajusté les teintes, regarde la version 2 dans les fichiers partagés. "
        "L'or chaud avec le fond presque noir donne quelque chose de très élégant.",
        d(-52) + 'T10:15:00',
        d(-51) + 'T14:30:00',
    ),
    (
        'Photos pour le portfolio',
        "Mes photos sont en 4K, est-ce que c'est trop lourd pour le web ? "
        "Je veux pas que le site soit lent.",
        "Pas d'inquiète ! Je vais les optimiser à la bonne taille pour le web. "
        "Envoie-les en full résolution dans l'onglet Fichiers, je m'occupe de tout.",
        d(-18) + 'T16:00:00',
        d(-17) + 'T09:45:00',
    ),
    (
        'Question sur le module réservation',
        "Pour les réservations, est-ce que les clients vont recevoir un courriel de confirmation automatique ?",
        None,
        d(-2) + 'T11:20:00',
        None,
    ),
]
for sujet, message, reponse, created_at, repondu_at in messages:
    conn.execute(
        'INSERT INTO messages_client (client_id, sujet, message, lu, reponse, repondu_at, created_at) VALUES (?,?,?,?,?,?,?)',
        (client_id, sujet, message, 1, reponse, repondu_at, created_at)
    )
conn.commit()

# ── QUESTIONNAIRE DE PREMIÈRE CONSULTATION ────────────────────────────────────
reponses_q = json.dumps({
    'activite':           'Photographe professionnelle — portraits, mariages, événements corporatifs. Studio à Montréal.',
    'clientele':          'Couples (mariages), familles, professionnels (LinkedIn, headshots). Clientèle haut de gamme.',
    'pourquoi_maintenant':'Mon site actuel date de 2019, il est pas mobile. Je perds des clients à cause de ça.',
    'type_projet':        'Site vitrine complet avec galerie filtrée, page services + tarifs, et formulaire de réservation de séances.',
    'vision':             'Épuré, élégant, noir et or. Les photos doivent être les vedettes. Ambiance luxe discret.',
    'budget':             '1 800 $ – 2 500 $',
    'deadline':           'Avant le 15 juin 2026 — début de la haute saison mariages.',
    'assets':             'Portfolio de 200+ photos haute résolution. Textes à rédiger ensemble.',
    'acces_technique':    'Domaine Squarespace (à transférer). Hébergement à décider.',
    'implication':        'Très impliquée pour le look, fait confiance pour le technique et le code.',
}, ensure_ascii=False)

conn.execute(
    'INSERT INTO questionnaires_client (client_id, reponses) VALUES (?,?)',
    (client_id, reponses_q)
)
conn.commit()

# ── CONSULTATION ──────────────────────────────────────────────────────────────
reponses_c = json.dumps({
    'activite':           'Studio photo pro — portraits, mariages, corporatif.',
    'clientele':          'Haut de gamme, couples et entreprises.',
    'pourquoi_maintenant':'Site 2019 non-mobile, perd des clients.',
    'type_projet':        'Vitrine + galerie + réservations.',
    'vision':             'Noir, or, épuré — photos en avant-plan.',
    'budget':             '2 000 $',
    'deadline':           'Mi-juin 2026',
    'assets':             '200+ photos dispo, textes à co-rédiger.',
    'acces_technique':    'Domaine Squarespace à transférer.',
    'implication':        'Impliquée design, délègue technique.',
}, ensure_ascii=False)

conn.execute(
    'INSERT INTO consultations (client_id, date, reponses, notes) VALUES (?,?,?,?)',
    (
        client_id,
        d(-60),
        reponses_c,
        "Excellente première impression. Sophie arrive avec un moodboard Pinterest très précis. "
        "Budget confirmé 2 000 $, flexibilité si module résa complexe. "
        "Urgence réelle : haute saison juin. Dispo pour révisions rapides. Démarrage immédiat.",
    )
)
conn.commit()
conn.close()

print('OK - Demo client peuple avec succes')
print('  Email    : demo@tntm.ca')
print('  Password : demo2026')
print(f'  Client ID: {client_id}')
print('  Contrat : 1 | Factures : 3 | Messages : 3 | Questionnaire : 1 | Consultation : 1')
