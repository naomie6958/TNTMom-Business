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

load_dotenv()

app = Flask(__name__)
# La secret_key sert à signer les cookies de session.
# Si elle change, toutes les sessions actives sont invalidées.
# En prod elle vient du .env — jamais hardcodée dans le code.
app.secret_key = os.getenv('SECRET_KEY', 'dev-only-change-me')

# Limite la taille des uploads à 16 MB — au-delà Flask retourne une erreur 413
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

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

    # Parse les réponses du questionnaire client pour affichage clé/valeur
    questionnaire_rep = {}
    if questionnaire and questionnaire['reponses']:
        questionnaire_rep = json.loads(questionnaire['reponses'])

    # Prix total du contrat calculé depuis les milestones
    total_contrat = sum(float(m.get('prix', 0)) for m in milestones) if milestones else 0

    return render_template('client_fiche.html',
                           client=client,
                           consultations=consultations_parsed,
                           contrat=contrat,
                           milestones=milestones,
                           total_contrat=total_contrat,
                           questionnaire=questionnaire,
                           questionnaire_rep=questionnaire_rep,
                           fichiers=fichiers,
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
        flash('Contrat sauvegardé.', 'success')
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


@app.route('/clients/<int:client_id>/contrat/print')
@login_required
def contrat_print(client_id):
    conn = get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    contrat = conn.execute(
        'SELECT * FROM contrats WHERE client_id = ? ORDER BY created_at DESC LIMIT 1',
        (client_id,)
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

@app.route('/clients/<int:client_id>/milestone/<int:index>/toggle', methods=['POST'])
@login_required
def toggle_milestone(client_id, index):
    conn = get_db()
    contrat = conn.execute(
        'SELECT * FROM contrats WHERE client_id = ? ORDER BY created_at DESC LIMIT 1',
        (client_id,)
    ).fetchone()

    if not contrat or not contrat['milestones']:
        conn.close()
        return redirect(f'/clients/{client_id}')

    # On charge le JSON, modifie l'élément à l'index voulu, et resauvegarde.
    # L'index vient de l'URL — c'est la position du milestone dans le tableau.
    milestones = json.loads(contrat['milestones'])

    if 0 <= index < len(milestones):
        actuel = milestones[index].get('statut', 'en cours')
        # Bascule entre les deux statuts possibles
        milestones[index]['statut'] = 'complété' if actuel != 'complété' else 'en cours'

    conn.execute(
        'UPDATE contrats SET milestones = ? WHERE id = ?',
        (json.dumps(milestones, ensure_ascii=False), contrat['id'])
    )
    conn.commit()
    conn.close()
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

    contrat = conn.execute(
        'SELECT * FROM contrats WHERE client_id = ? ORDER BY created_at DESC LIMIT 1',
        (session['client_id'],)
    ).fetchone()

    fichiers = conn.execute(
        'SELECT * FROM fichiers WHERE client_id = ? ORDER BY uploaded_at DESC',
        (session['client_id'],)
    ).fetchall()

    conn.close()

    milestones = []
    if contrat and contrat['milestones']:
        milestones = json.loads(contrat['milestones'])

    # float() convertit le prix string en nombre — même logique que client_fiche
    total_contrat = sum(float(m.get('prix', 0)) for m in milestones) if milestones else 0

    return render_template('portail_dashboard.html',
                            client=client,
                            contrat=contrat,
                            milestones=milestones,
                            total_contrat=total_contrat,
                            fichiers=fichiers)


if __name__ == '__main__':
    app.run(debug=True)