from flask import Flask, render_template, request, redirect, session, jsonify
from database import init_db, seed_db, get_db
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
from functools import wraps
import datetime
import json
import os

load_dotenv()

app = Flask(__name__)
# La secret_key sert à signer les cookies de session.
# Si elle change, toutes les sessions actives sont invalidées.
# En prod elle vient du .env — jamais hardcodée dans le code.
app.secret_key = os.getenv('SECRET_KEY', 'dev-only-change-me')

# On initialise et peuple la DB au démarrage de l'app
init_db()
seed_db()


# ─── DÉCORATEUR LOGIN ────────────────────────────────────────────────────────
#
# Un décorateur "enveloppe" une fonction pour lui ajouter du comportement.
# @login_required appliqué à une route = la route vérifie la session avant d'agir.
# Sans ça, on devrait copier le même if dans chaque route — pas DRY.

def login_required(f):
    @wraps(f)  # @wraps préserve le nom et la docstring de la fonction originale
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
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
    conn.close()

    return render_template('admin_dashboard.html',
                           clients=clients,
                           stats=stats,
                           name=session['user_name'])


# ─── CLIENTS ──────────────────────────────────────────────────────────────────

@app.route('/clients/new', methods=['POST'])
@login_required
def new_client():
    nom = request.form.get('nom', '').strip()
    if not nom:
        return redirect('/dashboard')

    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO clients (nom, email, entreprise, secteur, notes) VALUES (?,?,?,?,?)',
        (
            nom,
            request.form.get('email', '').strip(),
            request.form.get('entreprise', '').strip(),
            request.form.get('secteur', '').strip(),
            request.form.get('notes', '').strip(),
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

    conn.close()

    # Parse le JSON des milestones pour l'affichage dans le template
    milestones = []
    if contrat and contrat['milestones']:
        milestones = json.loads(contrat['milestones'])

    # Pareil pour les consultations — parse le JSON de chaque consultation
    consultations_parsed = []
    for c in consultations:
        d = dict(c)
        d['reponses_parsed'] = json.loads(c['reponses']) if c['reponses'] else {}
        consultations_parsed.append(d)

    # Prix total du contrat calculé depuis les milestones
    total_contrat = sum(float(m.get('prix', 0)) for m in milestones) if milestones else 0

    return render_template('client_fiche.html',
                           client=client,
                           consultations=consultations_parsed,
                           contrat=contrat,
                           milestones=milestones,
                           total_contrat=total_contrat,
                           questionnaire=questionnaire,
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

@app.route('/clients/<int:client_id>/contrat', methods=['GET', 'POST'])
@login_required
def contrat(client_id):
    conn = get_db()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ?', (client_id,)
    ).fetchone()

    if not client:
        conn.close()
        return redirect('/dashboard')

    existing = conn.execute(
        'SELECT * FROM contrats WHERE client_id = ? ORDER BY created_at DESC LIMIT 1',
        (client_id,)
    ).fetchone()

    if request.method == 'POST':
        # milestones_json est construit côté client par le JS de contrat.html
        # et soumis dans un champ <input type="hidden"> — voir le template
        raw = request.form.get('milestones_json', '[]')
        try:
            milestones = json.loads(raw)
        except json.JSONDecodeError:
            milestones = []

        fields = (
            request.form.get('scope', ''),
            json.dumps(milestones, ensure_ascii=False),
            request.form.get('conditions_paiement', ''),
            request.form.get('politique_revisions', ''),
            request.form.get('hors_scope', ''),
            request.form.get('timeline', ''),
            request.form.get('statut', 'draft'),
        )

        if existing:
            # UPDATE : le contrat existe déjà pour ce client
            conn.execute('''
                UPDATE contrats
                SET scope=?, milestones=?, conditions_paiement=?,
                    politique_revisions=?, hors_scope=?, timeline=?, statut=?
                WHERE id=?
            ''', fields + (existing['id'],))
        else:
            # INSERT : premier contrat pour ce client
            conn.execute('''
                INSERT INTO contrats
                    (client_id, scope, milestones, conditions_paiement,
                     politique_revisions, hors_scope, timeline, statut)
                VALUES (?,?,?,?,?,?,?,?)
            ''', (client_id,) + fields)

        conn.commit()
        conn.close()
        return redirect(f'/clients/{client_id}')

    # Pré-remplir le form avec les données existantes
    milestones = []
    if existing and existing['milestones']:
        milestones = json.loads(existing['milestones'])

    conn.close()
    return render_template('contrat.html',
                           client=client,
                           contrat=existing,
                           milestones=milestones,
                           name=session['user_name'])


# ─── QUESTIONNAIRE CLIENT (accès public, pas de login) ───────────────────────

@app.route('/q/<int:client_id>', methods=['GET', 'POST'])
def questionnaire_client(client_id):
    conn = get_db()
    # On n'expose que le nom du client — pas l'email ni les notes
    client = conn.execute(
        'SELECT id, nom, entreprise FROM clients WHERE id = ?', (client_id,)
    ).fetchone()

    if not client:
        conn.close()
        return render_template('404.html'), 404

    deja_soumis = conn.execute(
        'SELECT id FROM questionnaires_client WHERE client_id = ?', (client_id,)
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
            (client_id, json.dumps(reponses, ensure_ascii=False))
        )
        conn.commit()
        deja_soumis = True

    conn.close()
    return render_template('questionnaire_client.html',
                           client=client,
                           soumis=bool(deja_soumis))


@app.route('/plan')
@login_required
def plan():
    # Le plan d'affaires est une page standalone — render_template la sert telle quelle
    return render_template('plan.html')


if __name__ == '__main__':
    app.run(debug=True)
