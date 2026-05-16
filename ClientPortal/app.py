from flask import Flask, render_template, request, redirect, session, jsonify, flash, send_from_directory
from database import init_db, seed_db, migrate_db, get_db
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from functools import wraps
import datetime
import json
import os
import uuid
import smtplib
from email.mime.text import MIMEText

load_dotenv()

app = Flask(__name__)


def send_notification_email(subject, body):
    """Envoie un courriel de notification via Gmail SMTP. Silencieux si non configuré."""
    gmail_user = os.getenv('GMAIL_USER')
    gmail_pass = os.getenv('GMAIL_APP_PASSWORD')
    if not gmail_user or not gmail_pass:
        return
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From']    = gmail_user
        msg['To']      = 'naomiemt@tntm.ca'
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
    except Exception:
        pass  # Ne jamais bloquer l'app si l'email échoue


def _compute_deadlines(milestones):
    """Calcule deadline[i] = milieu entre date[i] et date[i+1]. Modifie la liste en place."""
    for i, m in enumerate(milestones):
        if i < len(milestones) - 1:
            d1 = m.get('date', '')
            d2 = milestones[i + 1].get('date', '')
            if d1 and d2:
                try:
                    dt1 = datetime.datetime.strptime(d1, '%Y-%m-%d')
                    dt2 = datetime.datetime.strptime(d2, '%Y-%m-%d')
                    mid = dt1 + (dt2 - dt1) / 2
                    m['deadline'] = mid.strftime('%Y-%m-%d')
                except Exception:
                    m['deadline'] = ''
            else:
                m['deadline'] = ''
        else:
            m['deadline'] = ''
    return milestones


def group_messages(messages):
    """Regroupe les messages en fils de conversation par sujet de base (ignore les Re:)."""
    from collections import OrderedDict

    def base_subject(s):
        s = (s or '').strip()
        while s.lower().startswith('re: '):
            s = s[4:].strip()
        return s or 'Sans sujet'

    threads = OrderedDict()
    for msg in messages:
        key = base_subject(msg['sujet'])
        if key not in threads:
            threads[key] = []
        threads[key].append(dict(msg))

    return list(threads.items())
# La secret_key sert à signer les cookies de session.
# Si elle change, toutes les sessions actives sont invalidées.
# En prod elle vient du .env — jamais hardcodée dans le code.
app.secret_key = os.getenv('SECRET_KEY', 'dev-only-change-me')

_MOIS = ['jan', 'fév', 'mar', 'avr', 'mai', 'juin', 'juil', 'août', 'sep', 'oct', 'nov', 'déc']

@app.template_filter('fmt_date')
def fmt_date(s):
    if not s:
        return ''
    try:
        dt = datetime.datetime.strptime(s, '%Y-%m-%d')
        return f"{dt.day} {_MOIS[dt.month - 1]}"
    except Exception:
        return s

# Limite la taille des uploads à 16 MB — au-delà Flask retourne une erreur 413
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Permet au cookie de session de fonctionner dans un iframe cross-site (démo portfolio)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE']   = True

# Dossier de stockage des fichiers uploadés — en dehors de static/ pour ne pas
# être servi directement. Flask contrôle qui peut télécharger quoi.
UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), 'uploads')

# On initialise et peuple la DB au démarrage de l'app
init_db()
migrate_db()  # Ajoute token aux clients existants si nécessaire
seed_db()


# ─── DÉCORATEUR LOGIN ────────────────────────────────────────────────────────
#
# Un décorateur "enveloppe" une fonction pour lui ajouter du comportement.
# @login_required appliqué à une route = la route vérifie la session avant d'agir.
# Sans ça, on devrait copier le même if dans chaque route — pas DRY.

@app.context_processor
def inject_user():
    return {
        'name': session.get('user_name', ''),
        'client_nom': session.get('client_nom', ''),
    }


def login_required(f):
    @wraps(f)  # @wraps préserve le nom et la docstring de la fonction originale
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def client_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'client_id' not in session:
            return redirect('/portail/login')
        return f(*args, **kwargs)
    return decorated

# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        conn.close()

        # check_password_hash compare le mot de passe saisi au hash stocké en DB.
        # On ne peut pas "déhasher" — on hash la saisie et on compare les hash.
        if user and check_password_hash(user['password'], password):
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            return redirect('/dashboard')

        error = 'Identifiants incorrects.'

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()  # Vide toute la session = déconnexion
    return redirect('/login')


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    clients = conn.execute(
        'SELECT * FROM clients ORDER BY created_at DESC'
    ).fetchall()

    # Statistiques pour la barre de résumé en haut du hub
    stats = {
        'total':     len(clients),
        'prospects': sum(1 for c in clients if c['statut'] == 'prospect'),
        'actifs':    sum(1 for c in clients if c['statut'] == 'actif'),
        'completes': sum(1 for c in clients if c['statut'] == 'complété'),
    }

    unread_rows = conn.execute(
        'SELECT client_id, COUNT(*) as cnt FROM messages_client WHERE lu = 0 GROUP BY client_id'
    ).fetchall()
    unread_counts = {row['client_id']: row['cnt'] for row in unread_rows}
    conn.close()

    return render_template('admin_dashboard.html',
                           clients=clients,
                           stats=stats,
                           unread_counts=unread_counts,
                           name=session['user_name'])


# ─── CLIENTS ──────────────────────────────────────────────────────────────────

@app.route('/clients/new', methods=['POST'])
@login_required
def new_client():
    nom = request.form.get('nom', '').strip()
    if not nom:
        return redirect('/dashboard')

    conn = get_db()
    # uuid.uuid4() génère un identifiant aléatoire unique — format : xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    # str() le convertit en texte pour le stocker dans SQLite
    token = str(uuid.uuid4())
    cursor = conn.execute(
        'INSERT INTO clients (nom, email, entreprise, secteur, notes, token) VALUES (?,?,?,?,?,?)',
        (
            nom,
            request.form.get('email', '').strip(),
            request.form.get('entreprise', '').strip(),
            request.form.get('secteur', '').strip(),
            request.form.get('notes', '').strip(),
            token,
        )
    )
    client_id = cursor.lastrowid  # lastrowid = l'id de la ligne qu'on vient d'insérer
    conn.commit()
    conn.close()

    return redirect(f'/clients/{client_id}')


@app.route('/clients/<int:client_id>')
@login_required
def client_fiche(client_id):
    conn = get_db()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ?', (client_id,)
    ).fetchone()

    if not client:
        conn.close()
        return redirect('/dashboard')

    consultations = conn.execute(
        'SELECT * FROM consultations WHERE client_id = ? ORDER BY created_at DESC',
        (client_id,)
    ).fetchall()

    # On prend le contrat le plus récent (LIMIT 1) — Phase 1 = un contrat par client
    contrat = conn.execute(
        'SELECT * FROM contrats WHERE client_id = ? ORDER BY created_at DESC LIMIT 1',
        (client_id,)
    ).fetchone()

    questionnaire = conn.execute(
        'SELECT * FROM questionnaires_client WHERE client_id = ?',
        (client_id,)
    ).fetchone()

    fichiers = conn.execute(
        'SELECT * FROM fichiers WHERE client_id = ? ORDER BY uploaded_at DESC',
        (client_id,)
    ).fetchall()

    messages = conn.execute(
        'SELECT * FROM messages_client WHERE client_id = ? ORDER BY created_at ASC',
        (client_id,)
    ).fetchall()

    factures = conn.execute(
        'SELECT * FROM factures WHERE client_id = ? ORDER BY date_emission DESC',
        (client_id,)
    ).fetchall()

    contrats_all = conn.execute(
        'SELECT * FROM contrats WHERE client_id = ? ORDER BY created_at ASC',
        (client_id,)
    ).fetchall()

    form_reponses_raw = conn.execute('''
        SELECT fr.*, f.titre AS form_titre
        FROM formulaire_reponses fr
        JOIN formulaires f ON fr.formulaire_id = f.id
        WHERE fr.client_id = ?
        ORDER BY fr.submitted_at DESC
    ''', (client_id,)).fetchall()

    formulaires_tous = conn.execute(
        'SELECT * FROM formulaires WHERE actif = 1 ORDER BY titre'
    ).fetchall()
    formulaires_assignes_ids = {
        row['formulaire_id'] for row in conn.execute(
            'SELECT formulaire_id FROM client_formulaires WHERE client_id = ?', (client_id,)
        ).fetchall()
    }
    formulaires_assignes    = [f for f in formulaires_tous if f['id'] in formulaires_assignes_ids]
    formulaires_disponibles = [f for f in formulaires_tous if f['id'] not in formulaires_assignes_ids]

    # Auto-marque les messages comme lus dès que Naomie ouvre la fiche
    conn.execute(
        'UPDATE messages_client SET lu = 1 WHERE client_id = ? AND lu = 0',
        (client_id,)
    )
    conn.commit()
    conn.close()

    # Pareil pour les consultations — parse le JSON de chaque consultation
    consultations_parsed = []
    for c in consultations:
        d = dict(c)
        d['reponses_parsed'] = json.loads(c['reponses']) if c['reponses'] else {}
        consultations_parsed.append(d)

    # Parse les réponses du questionnaire client pour affichage clé/valeur
    questionnaire_rep = {}
    if questionnaire and questionnaire['reponses']:
        questionnaire_rep = json.loads(questionnaire['reponses'])

    # Parse les réponses des formulaires soumis par ce client
    # On enrichit chaque soumission avec les titres de questions pour affichage lisible
    conn2 = get_db()
    form_reponses = []
    for fr in form_reponses_raw:
        d = dict(fr)
        try:
            raw = json.loads(fr['reponses'])
        except Exception:
            raw = {}
        questions = conn2.execute(
            'SELECT id, titre, type FROM formulaire_questions WHERE formulaire_id = ? ORDER BY ordre',
            (fr['formulaire_id'],)
        ).fetchall()
        reponses_lisibles = []
        for q in questions:
            key = f'q_{q["id"]}'
            val = raw.get(key, '')
            if val:
                reponses_lisibles.append({'question': q['titre'], 'reponse': val, 'type': q['type']})
        d['reponses_lisibles'] = reponses_lisibles
        form_reponses.append(d)
    conn2.close()

    # Construit la liste enrichie des projets (tous les contrats)
    projets = []
    for c in contrats_all:
        m = _compute_deadlines(json.loads(c['milestones']) if c['milestones'] else [])
        total = sum(float(x.get('prix', 0)) for x in m)
        projets.append({'contrat': dict(c), 'milestones': m, 'total': total})

    # Garde contrat (le dernier) pour les sections qui n'ont pas encore migré
    contrat = contrats_all[-1] if contrats_all else None
    milestones = projets[-1]['milestones'] if projets else []
    total_contrat = projets[-1]['total'] if projets else 0

    return render_template('client_fiche.html',
                           client=client,
                           consultations=consultations_parsed,
                           contrat=contrat,
                           milestones=milestones,
                           total_contrat=total_contrat,
                           projets=projets,
                           questionnaire=questionnaire,
                           questionnaire_rep=questionnaire_rep,
                           fichiers=fichiers,
                           messages=messages,
                           msg_threads=group_messages(messages),
                           factures=factures,
                           form_reponses=form_reponses,
                           formulaires_assignes=formulaires_assignes,
                           formulaires_disponibles=formulaires_disponibles,
                           name=session['user_name'])


@app.route('/clients/<int:client_id>/edit', methods=['POST'])
@login_required
def edit_client(client_id):
    conn = get_db()
    conn.execute('''
        UPDATE clients
        SET nom=?, email=?, entreprise=?, secteur=?, notes=?, statut=?
        WHERE id=?
    ''', (
        request.form.get('nom', '').strip(),
        request.form.get('email', '').strip(),
        request.form.get('entreprise', '').strip(),
        request.form.get('secteur', '').strip(),
        request.form.get('notes', '').strip(),
        request.form.get('statut', 'prospect'),
        client_id
    ))
    conn.commit()
    conn.close()
    flash('Client mis à jour.', 'success')
    return redirect(f'/clients/{client_id}')


@app.route('/clients/<int:client_id>/statut', methods=['POST'])
@login_required
def client_statut(client_id):
    statut = request.form.get('statut', 'prospect')
    conn = get_db()
    conn.execute('UPDATE clients SET statut = ? WHERE id = ?', (statut, client_id))
    conn.commit()
    conn.close()
    flash(f'Statut mis à jour : {statut}.', 'success')
    return redirect(f'/clients/{client_id}')


@app.route('/clients/<int:client_id>/delete', methods=['POST'])
@login_required
def delete_client(client_id):
    conn = get_db()
    # ON DELETE CASCADE dans la DB supprime automatiquement
    # les consultations, contrats et questionnaires liés à ce client
    conn.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.commit()
    conn.close()
    flash('Client supprimé.', 'success')
    return redirect('/dashboard')


# ─── CONSULTATIONS ────────────────────────────────────────────────────────────

@app.route('/clients/<int:client_id>/consultation/new', methods=['GET', 'POST'])
@login_required
def new_consultation(client_id):
    conn = get_db()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ?', (client_id,)
    ).fetchone()

    if not client:
        conn.close()
        return redirect('/dashboard')

    # Pré-charger les réponses du questionnaire client s'il en a soumis un
    # Comme ça Naomie arrive avec les infos déjà lues
    questionnaire = conn.execute(
        'SELECT reponses FROM questionnaires_client WHERE client_id = ?',
        (client_id,)
    ).fetchone()
    prefill = {}
    if questionnaire and questionnaire['reponses']:
        prefill = json.loads(questionnaire['reponses'])

    if request.method == 'POST':
        reponses = {
            'activite':            request.form.get('activite', ''),
            'clientele':           request.form.get('clientele', ''),
            'pourquoi_maintenant': request.form.get('pourquoi_maintenant', ''),
            'type_projet':         request.form.get('type_projet', ''),
            'vision':              request.form.get('vision', ''),
            'budget':              request.form.get('budget', ''),
            'deadline':            request.form.get('deadline', ''),
            'assets':              request.form.get('assets', ''),
            'acces_technique':     request.form.get('acces_technique', ''),
            'implication':         request.form.get('implication', ''),
        }
        today = datetime.date.today().isoformat()
        conn.execute(
            'INSERT INTO consultations (client_id, date, reponses, notes) VALUES (?,?,?,?)',
            (
                client_id,
                today,
                # ensure_ascii=False = garde les accents français lisibles dans la DB
                json.dumps(reponses, ensure_ascii=False),
                request.form.get('notes', ''),
            )
        )
        conn.commit()
        conn.close()
        return redirect(f'/clients/{client_id}')

    conn.close()
    return render_template('consultation.html',
                           client=client,
                           prefill=prefill,
                           name=session['user_name'])


@app.route('/consultations/<int:consult_id>/delete', methods=['POST'])
@login_required
def delete_consultation(consult_id):
    conn = get_db()
    row = conn.execute(
        'SELECT client_id FROM consultations WHERE id = ?', (consult_id,)
    ).fetchone()
    client_id = row['client_id'] if row else None
    conn.execute('DELETE FROM consultations WHERE id = ?', (consult_id,))
    conn.commit()
    conn.close()
    return redirect(f'/clients/{client_id}' if client_id else '/dashboard')


# ─── CONTRATS ─────────────────────────────────────────────────────────────────

@app.route('/clients/<int:client_id>/contrat')
@login_required
def contrat(client_id):
    conn = get_db()
    existing = conn.execute(
        'SELECT id FROM contrats WHERE client_id = ? ORDER BY created_at DESC LIMIT 1',
        (client_id,)
    ).fetchone()
    conn.close()
    if existing:
        return redirect(f'/clients/{client_id}/contrat/{existing["id"]}')
    # Aucun contrat — on en crée un vide et on redirige vers l'édition
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO contrats (client_id, scope, milestones, statut, nom) VALUES (?,?,?,?,?)',
        (client_id, '', '[]', 'draft', 'Projet principal')
    )
    contrat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return redirect(f'/clients/{client_id}/contrat/{contrat_id}')


@app.route('/clients/<int:client_id>/contrat/<int:contrat_id>', methods=['GET', 'POST'])
@login_required
def contrat_edit(client_id, contrat_id):
    conn = get_db()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ?', (client_id,)
    ).fetchone()

    if not client:
        conn.close()
        return redirect('/dashboard')

    existing = conn.execute(
        'SELECT * FROM contrats WHERE id = ? AND client_id = ?', (contrat_id, client_id)
    ).fetchone()

    if not existing:
        conn.close()
        return redirect(f'/clients/{client_id}')

    if request.method == 'POST':
        raw = request.form.get('milestones_json', '[]')
        try:
            milestones = json.loads(raw)
        except json.JSONDecodeError:
            milestones = []

        conn.execute('''
            UPDATE contrats
            SET nom=?, scope=?, milestones=?, conditions_paiement=?,
                politique_revisions=?, hors_scope=?, timeline=?, statut=?
            WHERE id=?
        ''', (
            request.form.get('nom', '').strip() or 'Projet sans titre',
            request.form.get('scope', ''),
            json.dumps(milestones, ensure_ascii=False),
            request.form.get('conditions_paiement', ''),
            request.form.get('politique_revisions', ''),
            request.form.get('hors_scope', ''),
            request.form.get('timeline', ''),
            request.form.get('statut', 'draft'),
            contrat_id,
        ))
        conn.commit()
        conn.close()
        flash('Projet sauvegardé.', 'success')
        return redirect(f'/clients/{client_id}')

    milestones = json.loads(existing['milestones']) if existing['milestones'] else []
    conn.close()
    return render_template('contrat.html',
                           client=client,
                           contrat=existing,
                           milestones=milestones,
                           name=session['user_name'])


# ─── QUESTIONNAIRE CLIENT (accès public, pas de login) ───────────────────────

@app.route('/q/<token>', methods=['GET', 'POST'])
def questionnaire_client(token):
    conn = get_db()
    # On cherche le client par token (pas par id) — l'id ne sort jamais dans l'URL
    # On n'expose que le nom et l'entreprise au client
    client = conn.execute(
        'SELECT id, nom, entreprise FROM clients WHERE token = ?', (token,)
    ).fetchone()

    if not client:
        conn.close()
        return render_template('404.html'), 404

    deja_soumis = conn.execute(
        'SELECT id FROM questionnaires_client WHERE client_id = ?', (client['id'],)
    ).fetchone()

    if request.method == 'POST' and not deja_soumis:
        reponses = {
            'activite':            request.form.get('activite', ''),
            'clientele':           request.form.get('clientele', ''),
            'pourquoi_maintenant': request.form.get('pourquoi_maintenant', ''),
            'type_projet':         request.form.get('type_projet', ''),
            'vision':              request.form.get('vision', ''),
            'budget':              request.form.get('budget', ''),
            'deadline':            request.form.get('deadline', ''),
            'assets':              request.form.get('assets', ''),
            'acces_technique':     request.form.get('acces_technique', ''),
            'implication':         request.form.get('implication', ''),
        }
        conn.execute(
            'INSERT INTO questionnaires_client (client_id, reponses) VALUES (?,?)',
            (client['id'], json.dumps(reponses, ensure_ascii=False))
        )
        conn.commit()
        deja_soumis = True

    conn.close()
    return render_template('questionnaire_client.html',
                           client=client,
                           soumis=bool(deja_soumis))


@app.route('/clients/<int:client_id>/projet/new', methods=['POST'])
@login_required
def projet_new(client_id):
    nom = request.form.get('nom', '').strip() or 'Nouveau projet'
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO contrats (client_id, scope, milestones, statut, nom) VALUES (?,?,?,?,?)',
        (client_id, '', '[]', 'draft', nom)
    )
    contrat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return redirect(f'/clients/{client_id}/contrat/{contrat_id}')


@app.route('/clients/<int:client_id>/contrat/<int:contrat_id>/delete', methods=['POST'])
@login_required
def contrat_delete(client_id, contrat_id):
    conn = get_db()
    conn.execute('DELETE FROM factures WHERE contrat_id = ?', (contrat_id,))
    conn.execute('DELETE FROM contrats WHERE id = ? AND client_id = ?', (contrat_id, client_id))
    conn.commit()
    conn.close()
    flash('Projet supprimé.', 'success')
    return redirect(f'/clients/{client_id}')


@app.route('/clients/<int:client_id>/contrat/<int:contrat_id>/print')
@login_required
def contrat_print(client_id, contrat_id):
    conn = get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    contrat = conn.execute(
        'SELECT * FROM contrats WHERE id = ? AND client_id = ?', (contrat_id, client_id)
    ).fetchone()
    conn.close()
    if not client or not contrat:
        return redirect(f'/clients/{client_id}')
    milestones = json.loads(contrat['milestones']) if contrat['milestones'] else []
    total = sum(float(m.get('prix', 0)) for m in milestones)
    return render_template('contrat_print.html',
                           client=client, contrat=contrat,
                           milestones=milestones, total=total)


# ─── MILESTONES ───────────────────────────────────────────────────────────────

@app.route('/clients/<int:client_id>/contrat/<int:contrat_id>/milestone/<int:index>/toggle', methods=['POST'])
@login_required
def toggle_milestone(client_id, contrat_id, index):
    conn = get_db()
    contrat = conn.execute(
        'SELECT * FROM contrats WHERE id = ? AND client_id = ?', (contrat_id, client_id)
    ).fetchone()

    if not contrat or not contrat['milestones']:
        conn.close()
        return redirect(f'/clients/{client_id}')

    milestones = json.loads(contrat['milestones'])

    if 0 <= index < len(milestones):
        cycle = {
            'en attente': 'en cours',
            'en cours':   'livré',
            'livré':      'payé',
            'payé':       'en attente',
        }
        actuel = milestones[index].get('statut', 'en attente')
        nouveau = cycle.get(actuel, 'en cours')

        # Bloquer le démarrage si le milestone précédent n'est pas payé
        if nouveau == 'en cours' and index > 0:
            prev = milestones[index - 1].get('statut', 'en attente')
            if prev != 'payé':
                conn.close()
                msg = 'Le milestone précédent doit être payé avant de commencer celui-ci.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': msg}), 403
                flash(msg, 'error')
                return redirect(f'/clients/{client_id}')

        milestones[index]['statut'] = nouveau

        # Auto-créer une facture quand le milestone passe à 'livré'
        if nouveau == 'livré':
            m = milestones[index]
            montant = float(m.get('prix', 0) or 0)
            titre   = m.get('titre', f'Milestone {index + 1}')
            deja    = conn.execute(
                'SELECT id FROM factures WHERE contrat_id = ? AND milestone_titre = ?',
                (contrat_id, titre)
            ).fetchone()
            if not deja and montant > 0:
                count = conn.execute('SELECT COUNT(*) FROM factures').fetchone()[0]
                numero = f"{datetime.date.today().year}-{str(count + 1).zfill(3)}"
                conn.execute(
                    '''INSERT INTO factures
                       (client_id, contrat_id, numero, milestone_titre, montant, date_emission)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (client_id, contrat_id, numero, titre, montant,
                     datetime.date.today().isoformat())
                )

    conn.execute(
        'UPDATE contrats SET milestones = ? WHERE id = ?',
        (json.dumps(milestones, ensure_ascii=False), contrat['id'])
    )
    conn.commit()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'statut': milestones[index]['statut']})
    flash('Statut du milestone mis à jour.', 'success')
    return redirect(f'/clients/{client_id}')


# ─── FICHIERS ─────────────────────────────────────────────────────────────────

@app.route('/clients/<int:client_id>/fichiers/upload', methods=['POST'])
@login_required
def upload_fichier(client_id):
    fichier = request.files.get('fichier')
    if not fichier or fichier.filename == '':
        flash('Aucun fichier sélectionné.', 'error')
        return redirect(f'/clients/{client_id}')

    nom_original = fichier.filename
    # secure_filename retire les / et caractères dangereux — évite les path traversal
    nom_secure = secure_filename(nom_original)
    if not nom_secure:
        flash('Nom de fichier invalide.', 'error')
        return redirect(f'/clients/{client_id}')

    # UUID en préfixe = nom unique sur le disque même si deux clients uploadent le même nom
    nom_stocke = f"{uuid.uuid4().hex}_{nom_secure}"

    dossier = os.path.join(UPLOAD_ROOT, str(client_id))
    os.makedirs(dossier, exist_ok=True)   # crée le dossier du client s'il n'existe pas

    chemin = os.path.join(dossier, nom_stocke)
    fichier.save(chemin)
    taille = os.path.getsize(chemin)

    conn = get_db()
    conn.execute(
        'INSERT INTO fichiers (client_id, nom_original, nom_fichier, taille) VALUES (?,?,?,?)',
        (client_id, nom_original, nom_stocke, taille)
    )
    conn.commit()
    conn.close()
    flash(f'"{nom_original}" uploadé.', 'success')
    return redirect(f'/clients/{client_id}')


@app.route('/clients/<int:client_id>/fichiers/<int:fichier_id>/download')
@login_required
def telecharger_fichier_admin(client_id, fichier_id):
    conn = get_db()
    f = conn.execute(
        'SELECT * FROM fichiers WHERE id = ? AND client_id = ?', (fichier_id, client_id)
    ).fetchone()
    conn.close()

    if not f:
        return redirect(f'/clients/{client_id}')

    dossier = os.path.join(UPLOAD_ROOT, str(client_id))
    # as_attachment=True = force le téléchargement (pas d'affichage dans le navigateur)
    # download_name = nom montré à l'utilisateur (le nom original, pas le nom uuid interne)
    return send_from_directory(dossier, f['nom_fichier'],
                               as_attachment=True, download_name=f['nom_original'])


@app.route('/clients/<int:client_id>/fichiers/<int:fichier_id>/delete', methods=['POST'])
@login_required
def delete_fichier(client_id, fichier_id):
    conn = get_db()
    f = conn.execute(
        'SELECT * FROM fichiers WHERE id = ? AND client_id = ?', (fichier_id, client_id)
    ).fetchone()

    if f:
        chemin = os.path.join(UPLOAD_ROOT, str(client_id), f['nom_fichier'])
        if os.path.exists(chemin):
            os.remove(chemin)  # on supprime le fichier physique avant l'entrée DB
        conn.execute('DELETE FROM fichiers WHERE id = ?', (fichier_id,))
        conn.commit()
    conn.close()
    flash('Fichier supprimé.', 'success')
    return redirect(f'/clients/{client_id}')


@app.route('/portail/fichiers/<int:fichier_id>')
@client_login_required
def telecharger_fichier_client(fichier_id):
    conn = get_db()
    # On vérifie que le fichier appartient bien AU client connecté — un client
    # ne peut pas deviner l'id d'un fichier d'un autre client et le télécharger
    f = conn.execute(
        'SELECT * FROM fichiers WHERE id = ? AND client_id = ?',
        (fichier_id, session['client_id'])
    ).fetchone()
    conn.close()

    if not f:
        return redirect('/portail/dashboard')

    dossier = os.path.join(UPLOAD_ROOT, str(session['client_id']))
    return send_from_directory(dossier, f['nom_fichier'],
                               as_attachment=True, download_name=f['nom_original'])


# ─── ACCÈS PORTAIL CLIENT ─────────────────────────────────────────────────────

@app.route('/clients/<int:client_id>/set-password', methods=['POST'])
@login_required
def set_client_password(client_id):
    password = request.form.get('password', '').strip()

    # Validation minimale : on refuse un mot de passe vide
    if not password:
        return redirect(f'/clients/{client_id}')

    conn = get_db()
    # generate_password_hash() transforme le mot de passe en hash sécurisé.
    # Même logique que pour l'admin — on ne stocke jamais un mot de passe en clair.
    conn.execute(
        'UPDATE clients SET password = ? WHERE id = ?',
        (generate_password_hash(password), client_id)
    )
    conn.commit()
    conn.close()
    flash('Mot de passe mis à jour.', 'success')
    return redirect(f'/clients/{client_id}')


@app.route('/clients/<int:client_id>/formulaires/assign', methods=['POST'])
@login_required
def client_formulaire_assign(client_id):
    fid = request.form.get('formulaire_id')
    if fid:
        conn = get_db()
        conn.execute(
            'INSERT OR IGNORE INTO client_formulaires (client_id, formulaire_id) VALUES (?,?)',
            (client_id, int(fid))
        )
        conn.commit()
        conn.close()
    return redirect(f'/clients/{client_id}#formulaires')


@app.route('/clients/<int:client_id>/formulaires/<int:fid>/remove', methods=['POST'])
@login_required
def client_formulaire_remove(client_id, fid):
    conn = get_db()
    conn.execute(
        'DELETE FROM client_formulaires WHERE client_id = ? AND formulaire_id = ?',
        (client_id, fid)
    )
    conn.commit()
    conn.close()
    return redirect(f'/clients/{client_id}#formulaires')


@app.route('/plan')
@login_required
def plan():
    return render_template('plan.html')


@app.route('/roadmap')
@login_required
def roadmap():
    return render_template('roadmap.html')


# ─── PORTAIL CLIENT ───────────────────────────────────────────────────────────

@app.route('/portail/login', methods=['GET', 'POST'])
def portail_login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        client = conn.execute(
            'SELECT * FROM clients WHERE email = ?', (email,)
        ).fetchone()
        conn.close()

        if client and client['password'] and check_password_hash(client['password'], password):
            session['client_id']   = client['id']
            session['client_nom'] = client['nom']
            return redirect('/portail/dashboard')

        error = 'Courriel ou mot de passe incorrect.'

    return render_template('portail_login.html', error=error)


@app.route('/portail/logout')
def portail_logout():
    session.pop('client_id', None)
    session.pop('client_nom', None)
    return redirect('/portail/login')



@app.route('/portail/dashboard')
@client_login_required
def portail_dashboard():
    conn = get_db()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ?', (session['client_id'],)
    ).fetchone()

    contrats_all = conn.execute(
        'SELECT * FROM contrats WHERE client_id = ? ORDER BY created_at ASC',
        (session['client_id'],)
    ).fetchall()

    fichiers = conn.execute(
        'SELECT * FROM fichiers WHERE client_id = ? ORDER BY uploaded_at DESC',
        (session['client_id'],)
    ).fetchall()

    conn.close()

    # Construit une liste de projets enrichis pour le template
    projets = []
    for c in contrats_all:
        m = _compute_deadlines(json.loads(c['milestones']) if c['milestones'] else [])
        total = sum(float(x.get('prix', 0)) for x in m)
        faits = sum(1 for x in m if x.get('statut') in ['livré', 'payé'])
        projets.append({
            'contrat': dict(c),
            'milestones': m,
            'total': total,
            'faits': faits,
        })

    return render_template('portail_dashboard.html',
                            client=client,
                            projets=projets,
                            fichiers=fichiers)


@app.route('/clients/<int:client_id>/messages/<int:message_id>/repondre', methods=['POST'])
@login_required
def repondre_message(client_id, message_id):
    reponse = request.form.get('reponse', '').strip()
    if reponse:
        now = datetime.datetime.now().isoformat(timespec='seconds')
        conn = get_db()
        conn.execute(
            'UPDATE messages_client SET reponse=?, repondu_at=? WHERE id=? AND client_id=?',
            (reponse, now, message_id, client_id)
        )
        conn.commit()
        conn.close()
        flash('Réponse envoyée.', 'success')
    return redirect(f'/clients/{client_id}')


@app.route('/portail/contrat/<int:contrat_id>/print')
@client_login_required
def portail_contrat_print(contrat_id):
    conn = get_db()
    contrat = conn.execute(
        'SELECT * FROM contrats WHERE id = ? AND client_id = ?',
        (contrat_id, session['client_id'])
    ).fetchone()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (session['client_id'],)).fetchone()
    conn.close()
    if not contrat or contrat['statut'] != 'signé':
        return redirect('/portail/dashboard')
    milestones = json.loads(contrat['milestones']) if contrat['milestones'] else []
    total = sum(float(m.get('prix', 0)) for m in milestones)
    return render_template('contrat_print.html', client=client, contrat=contrat,
                           milestones=milestones, total=total)


@app.route('/portail/contrat/<int:contrat_id>/signer', methods=['POST'])
@client_login_required
def portail_signer(contrat_id):
    conn = get_db()
    contrat = conn.execute(
        'SELECT * FROM contrats WHERE id = ? AND client_id = ?',
        (contrat_id, session['client_id'])
    ).fetchone()

    if contrat and contrat['statut'] == 'envoyé':
        now = datetime.datetime.now().isoformat(timespec='seconds')
        conn.execute(
            "UPDATE contrats SET statut='signé', signed_at=? WHERE id=?",
            (now, contrat_id)
        )
        conn.commit()
        flash('Contrat signé. Merci !', 'success')
    conn.close()
    return redirect('/portail/dashboard')


@app.route('/portail/contact', methods=['GET', 'POST'])
@client_login_required
def portail_contact():
    conn = get_db()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ?', (session['client_id'],)
    ).fetchone()

    if request.method == 'POST':
        sujet   = request.form.get('sujet', '').strip()
        message = request.form.get('message', '').strip()
        if message:
            conn.execute(
                'INSERT INTO messages_client (client_id, sujet, message) VALUES (?,?,?)',
                (session['client_id'], sujet, message)
            )
            conn.commit()
            conn.close()
            send_notification_email(
                f'[ClientPortal] Nouveau message de {session["client_nom"]}',
                f'Client : {session["client_nom"]}\nSujet : {sujet or "(aucun)"}\n\n{message}'
            )
            flash('Message envoyé. Naomie te reviendra sous peu !', 'success')
        else:
            conn.close()
            flash('Le message ne peut pas être vide.', 'error')
        return redirect('/portail/contact')

    historique = conn.execute(
        'SELECT * FROM messages_client WHERE client_id = ? ORDER BY created_at ASC',
        (session['client_id'],)
    ).fetchall()
    conn.close()
    return render_template('portail_contact.html', client=client,
                           threads=group_messages(historique))


# ─── FACTURES ADMIN ──────────────────────────────────────────────────────────

@app.route('/clients/<int:client_id>/factures/new', methods=['POST'])
@login_required
def facture_new(client_id):
    conn = get_db()
    montant = float(request.form.get('montant', 0) or 0)
    count   = conn.execute('SELECT COUNT(*) FROM factures').fetchone()[0]
    numero  = f"{datetime.date.today().year}-{str(count + 1).zfill(3)}"
    contrat_id = request.form.get('contrat_id') or None
    conn.execute(
        '''INSERT INTO factures
           (client_id, contrat_id, numero, milestone_titre, description, montant, date_emission)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (client_id, contrat_id, numero,
         request.form.get('milestone_titre', '').strip(),
         request.form.get('description', '').strip(),
         montant, datetime.date.today().isoformat())
    )
    conn.commit()
    conn.close()
    flash('Facture créée.', 'success')
    return redirect(f'/clients/{client_id}')


@app.route('/clients/<int:client_id>/factures/<int:facture_id>/marquer-payee', methods=['POST'])
@login_required
def facture_marquer_payee(client_id, facture_id):
    conn = get_db()
    facture = conn.execute(
        'SELECT * FROM factures WHERE id = ? AND client_id = ?', (facture_id, client_id)
    ).fetchone()

    if facture:
        conn.execute(
            "UPDATE factures SET statut = 'payée', date_paiement = ? WHERE id = ?",
            (datetime.date.today().isoformat(), facture_id)
        )

        # Sync le milestone correspondant → 'payé'
        if facture['contrat_id'] and facture['milestone_titre']:
            contrat = conn.execute(
                'SELECT * FROM contrats WHERE id = ?', (facture['contrat_id'],)
            ).fetchone()
            if contrat and contrat['milestones']:
                milestones = json.loads(contrat['milestones'])
                changed = False
                for m in milestones:
                    if m.get('titre') == facture['milestone_titre'] and m.get('statut') == 'livré':
                        m['statut'] = 'payé'
                        changed = True
                if changed:
                    conn.execute(
                        'UPDATE contrats SET milestones = ? WHERE id = ?',
                        (json.dumps(milestones, ensure_ascii=False), facture['contrat_id'])
                    )

        conn.commit()

    conn.close()
    flash('Facture marquée comme payée — milestone mis à jour.', 'success')
    return redirect(f'/clients/{client_id}')


@app.route('/clients/<int:client_id>/factures/<int:facture_id>/delete', methods=['POST'])
@login_required
def facture_delete(client_id, facture_id):
    conn = get_db()
    conn.execute('DELETE FROM factures WHERE id = ? AND client_id = ?', (facture_id, client_id))
    conn.commit()
    conn.close()
    flash('Facture supprimée.', 'success')
    return redirect(f'/clients/{client_id}')


@app.route('/clients/<int:client_id>/factures/<int:facture_id>/envoyer', methods=['POST'])
@login_required
def facture_envoyer(client_id, facture_id):
    conn = get_db()
    client  = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    facture = conn.execute(
        'SELECT * FROM factures WHERE id = ? AND client_id = ?', (facture_id, client_id)
    ).fetchone()
    if not client or not facture:
        conn.close()
        return jsonify({'error': 'Introuvable'}), 404
    if not client['email']:
        conn.close()
        return jsonify({'error': 'Ce client n\'a pas d\'adresse courriel.'}), 400
    contrat_nom = '—'
    if facture['contrat_id']:
        c = conn.execute('SELECT nom FROM contrats WHERE id = ?', (facture['contrat_id'],)).fetchone()
        if c and c['nom']:
            contrat_nom = c['nom']
    conn.close()

    montant     = f"{facture['montant']:,.2f} $".replace(',', ' ')
    description = facture['milestone_titre'] or facture['description'] or '—'
    html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#222;max-width:600px;margin:0 auto;padding:2rem;">
<h2 style="color:#111;border-bottom:2px solid #d946ef;padding-bottom:.5rem;">Facture {facture['numero'] or ''}</h2>
<p>Bonjour {client['nom']},</p>
<p>Veuillez trouver ci-dessous le détail de votre facture.</p>
<table style="width:100%;border-collapse:collapse;margin:1.5rem 0;font-size:.95rem;">
<tr style="background:#f5f5f5;"><td style="padding:.6rem;border:1px solid #ddd;font-weight:bold;">Projet</td><td style="padding:.6rem;border:1px solid #ddd;">{contrat_nom}</td></tr>
<tr><td style="padding:.6rem;border:1px solid #ddd;font-weight:bold;">Description</td><td style="padding:.6rem;border:1px solid #ddd;">{description}</td></tr>
<tr style="background:#f5f5f5;"><td style="padding:.6rem;border:1px solid #ddd;font-weight:bold;">Montant</td><td style="padding:.6rem;border:1px solid #ddd;font-size:1.1rem;color:#d946ef;font-weight:bold;">{montant}</td></tr>
<tr><td style="padding:.6rem;border:1px solid #ddd;font-weight:bold;">Date d'émission</td><td style="padding:.6rem;border:1px solid #ddd;">{facture['date_emission'] or '—'}</td></tr>
<tr style="background:#f5f5f5;"><td style="padding:.6rem;border:1px solid #ddd;font-weight:bold;">Statut</td><td style="padding:.6rem;border:1px solid #ddd;">{facture['statut']}</td></tr>
</table>
<p>Pour toute question, répondez à ce courriel ou écrivez à <a href="mailto:naomiemt@tntm.ca">naomiemt@tntm.ca</a>.</p>
<p>Merci pour votre confiance !</p>
<p style="margin-top:2rem;color:#888;font-size:.85rem;">— Naomie McMahon · <a href="https://tntm.ca" style="color:#d946ef;">tntm.ca</a></p>
</body></html>"""

    gmail_user = os.getenv('GMAIL_USER')
    gmail_pass = os.getenv('GMAIL_APP_PASSWORD')
    if not gmail_user or not gmail_pass:
        return jsonify({'error': 'SMTP non configuré'}), 500
    try:
        msg = MIMEText(html, 'html', 'utf-8')
        msg['Subject'] = f'Facture {facture["numero"] or ""} – {contrat_nom}'
        msg['From']    = f'Naomie McMahon <{gmail_user}>'
        msg['To']      = client['email']
        msg['Reply-To'] = 'naomiemt@tntm.ca'
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/clients/<int:client_id>/factures/<int:facture_id>/print')
@login_required
def facture_print(client_id, facture_id):
    conn = get_db()
    facture = conn.execute(
        'SELECT * FROM factures WHERE id = ? AND client_id = ?', (facture_id, client_id)
    ).fetchone()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    conn.close()
    if not facture:
        return redirect(f'/clients/{client_id}')
    return render_template('facture_print.html', facture=facture, client=client)


# ─── FACTURES PORTAIL CLIENT ──────────────────────────────────────────────────

@app.route('/portail/factures')
@client_login_required
def portail_factures():
    conn = get_db()
    client   = conn.execute('SELECT * FROM clients WHERE id = ?', (session['client_id'],)).fetchone()
    factures = conn.execute(
        'SELECT * FROM factures WHERE client_id = ? ORDER BY date_emission DESC',
        (session['client_id'],)
    ).fetchall()
    conn.close()
    return render_template('portail_factures.html', client=client, factures=factures)


@app.route('/portail/factures/<int:facture_id>/print')
@client_login_required
def portail_facture_print(facture_id):
    conn = get_db()
    facture = conn.execute(
        'SELECT * FROM factures WHERE id = ? AND client_id = ?',
        (facture_id, session['client_id'])
    ).fetchone()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (session['client_id'],)).fetchone()
    conn.close()
    if not facture:
        return redirect('/portail/factures')
    return render_template('facture_print.html', facture=facture, client=client)


# ── FORMULAIRES CUSTOM ────────────────────────────────────────────────────────

@app.route('/formulaires')
@login_required
def formulaires():
    conn = get_db()
    rows = conn.execute('''
        SELECT f.*,
               (SELECT COUNT(*) FROM formulaire_questions WHERE formulaire_id = f.id) AS nb_questions
        FROM formulaires f ORDER BY f.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('formulaires.html', formulaires=rows)


@app.route('/formulaires/new', methods=['POST'])
@login_required
def formulaire_new():
    titre = request.form.get('titre', '').strip()
    desc  = request.form.get('description', '').strip()
    if not titre:
        flash('Le titre est requis.', 'error')
        return redirect('/formulaires')
    conn = get_db()
    cur = conn.execute('INSERT INTO formulaires (titre, description) VALUES (?, ?)', (titre, desc or None))
    conn.commit()
    fid = cur.lastrowid
    conn.close()
    return redirect(f'/formulaires/{fid}')


@app.route('/formulaires/<int:fid>')
@login_required
def formulaire_edit(fid):
    conn = get_db()
    f = conn.execute('SELECT * FROM formulaires WHERE id = ?', (fid,)).fetchone()
    if not f:
        conn.close()
        flash('Formulaire introuvable.', 'error')
        return redirect('/formulaires')
    questions = conn.execute(
        'SELECT * FROM formulaire_questions WHERE formulaire_id = ? ORDER BY ordre', (fid,)
    ).fetchall()
    conn.close()
    return render_template('formulaire_edit.html', formulaire=f, questions=questions)


@app.route('/formulaires/<int:fid>/edit', methods=['POST'])
@login_required
def formulaire_update(fid):
    titre = request.form.get('titre', '').strip()
    desc  = request.form.get('description', '').strip()
    conn = get_db()
    conn.execute('UPDATE formulaires SET titre = ?, description = ? WHERE id = ?', (titre, desc or None, fid))
    conn.commit()
    conn.close()
    flash('Formulaire mis à jour.', 'success')
    return redirect(f'/formulaires/{fid}')


@app.route('/formulaires/<int:fid>/delete', methods=['POST'])
@login_required
def formulaire_delete(fid):
    conn = get_db()
    conn.execute('DELETE FROM formulaires WHERE id = ?', (fid,))
    conn.commit()
    conn.close()
    flash('Formulaire supprimé.', 'success')
    return redirect('/formulaires')


@app.route('/formulaires/<int:fid>/questions/add', methods=['POST'])
@login_required
def formulaire_question_add(fid):
    titre     = request.form.get('titre', '').strip()
    type_     = request.form.get('type', 'texte')
    sous_titre = request.form.get('sous_titre', '').strip()
    options   = request.form.get('options', '').strip()
    requis    = 1 if request.form.get('requis') else 0
    if not titre and type_ != 'section':
        flash('Le titre de la question est requis.', 'error')
        return redirect(f'/formulaires/{fid}')
    conn = get_db()
    max_ordre = conn.execute(
        'SELECT COALESCE(MAX(ordre), -1) FROM formulaire_questions WHERE formulaire_id = ?', (fid,)
    ).fetchone()[0]
    conn.execute(
        'INSERT INTO formulaire_questions (formulaire_id, ordre, titre, sous_titre, type, options, requis) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (fid, max_ordre + 1, titre or '—', sous_titre or None, type_, options or None, requis)
    )
    conn.commit()
    conn.close()
    return redirect(f'/formulaires/{fid}')


@app.route('/formulaires/<int:fid>/questions/<int:qid>/edit', methods=['POST'])
@login_required
def formulaire_question_edit(fid, qid):
    titre      = request.form.get('titre', '').strip()
    sous_titre = request.form.get('sous_titre', '').strip()
    type_      = request.form.get('type', 'texte')
    options    = request.form.get('options', '').strip()
    requis     = 1 if request.form.get('requis') else 0
    conn = get_db()
    conn.execute(
        'UPDATE formulaire_questions SET titre=?, sous_titre=?, type=?, options=?, requis=? WHERE id=? AND formulaire_id=?',
        (titre, sous_titre or None, type_, options or None, requis, qid, fid)
    )
    conn.commit()
    conn.close()
    return redirect(f'/formulaires/{fid}')


@app.route('/formulaires/<int:fid>/questions/<int:qid>/delete', methods=['POST'])
@login_required
def formulaire_question_delete(fid, qid):
    conn = get_db()
    conn.execute('DELETE FROM formulaire_questions WHERE id = ? AND formulaire_id = ?', (qid, fid))
    conn.commit()
    conn.close()
    return redirect(f'/formulaires/{fid}')


@app.route('/formulaires/<int:fid>/questions/reorder', methods=['POST'])
@login_required
def formulaire_questions_reorder(fid):
    data  = request.get_json(silent=True) or {}
    ordre = data.get('ordre', [])
    conn  = get_db()
    for i, qid in enumerate(ordre):
        conn.execute(
            'UPDATE formulaire_questions SET ordre = ? WHERE id = ? AND formulaire_id = ?', (i, qid, fid)
        )
    conn.commit()
    conn.close()
    return {'ok': True}


# ── FORMULAIRES PORTAIL CLIENT ────────────────────────────────────────────────

@app.route('/portail/formulaires')
@client_login_required
def portail_formulaires():
    conn = get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (session['client_id'],)).fetchone()
    formulaires = conn.execute('''
        SELECT f.* FROM formulaires f
        JOIN client_formulaires cf ON f.id = cf.formulaire_id
        WHERE cf.client_id = ? AND f.actif = 1
        ORDER BY cf.assigned_at DESC
    ''', (session['client_id'],)).fetchall()
    deja_remplis = {
        row['formulaire_id']
        for row in conn.execute(
            'SELECT formulaire_id FROM formulaire_reponses WHERE client_id = ?',
            (session['client_id'],)
        ).fetchall()
    }
    questionnaire = conn.execute(
        'SELECT reponses FROM questionnaires_client WHERE client_id = ?',
        (session['client_id'],)
    ).fetchone()
    conn.close()
    return render_template('portail_formulaires.html',
                           client=client,
                           formulaires=formulaires,
                           deja_remplis=deja_remplis,
                           questionnaire=questionnaire)


@app.route('/portail/formulaires/<int:fid>')
@client_login_required
def portail_formulaire_fill(fid):
    conn = get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (session['client_id'],)).fetchone()
    f = conn.execute('SELECT * FROM formulaires WHERE id = ? AND actif = 1', (fid,)).fetchone()
    if not f:
        conn.close()
        return redirect('/portail/formulaires')
    questions = conn.execute(
        'SELECT * FROM formulaire_questions WHERE formulaire_id = ? ORDER BY ordre', (fid,)
    ).fetchall()
    deja = conn.execute(
        'SELECT id FROM formulaire_reponses WHERE formulaire_id = ? AND client_id = ?',
        (fid, session['client_id'])
    ).fetchone()
    conn.close()
    if deja:
        flash('Tu as déjà rempli ce formulaire.', 'success')
        return redirect('/portail/formulaires')
    return render_template('portail_formulaire_fill.html',
                           client=client, formulaire=f, questions=questions)


@app.route('/portail/formulaires/<int:fid>/submit', methods=['POST'])
@client_login_required
def portail_formulaire_submit(fid):
    conn = get_db()
    deja = conn.execute(
        'SELECT id FROM formulaire_reponses WHERE formulaire_id = ? AND client_id = ?',
        (fid, session['client_id'])
    ).fetchone()
    if not deja:
        reponses = {k: v for k, v in request.form.items() if k != 'csrf_token'}
        conn.execute(
            'INSERT INTO formulaire_reponses (formulaire_id, client_id, reponses) VALUES (?,?,?)',
            (fid, session['client_id'], json.dumps(reponses, ensure_ascii=False))
        )
        conn.commit()
        client = conn.execute('SELECT nom FROM clients WHERE id = ?', (session['client_id'],)).fetchone()
        formulaire = conn.execute('SELECT titre FROM formulaires WHERE id = ?', (fid,)).fetchone()
        if client and formulaire:
            send_notification_email(
                f'[ClientPortal] Formulaire rempli par {client["nom"]}',
                f'{client["nom"]} a rempli le formulaire : {formulaire["titre"]}'
            )
    conn.close()
    flash('Formulaire envoyé, merci !', 'success')
    return redirect('/portail/formulaires')


if __name__ == '__main__':
    app.run(debug=True)