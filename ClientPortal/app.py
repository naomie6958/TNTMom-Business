import datetime
import json
import os
import secrets
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session, jsonify, flash, send_from_directory, url_for, Response
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (OSError, ImportError):
    WEASYPRINT_AVAILABLE = False
    print("[!] WeasyPrint (GTK) introuvable. Generation de PDF desactivee en local.")

from database import init_db, seed_db, migrate_db, get_db
from email_templates import (
    email_bienvenue, email_contrat_envoye, email_milestone_livre,
    email_reponse_message, email_message_naomie, email_lead_confirmation,
    email_contrat_signe_naomie, email_milestone_approuve_naomie,
    email_message_recu_naomie, email_lead_naomie, email_formulaire_naomie,
    email_facture
)

from utils import (
    send_notification_email, _compute_deadlines, group_messages,
    _now, login_required, client_login_required, safe_json_loads
)

_EASTERN = ZoneInfo('America/Montreal')

load_dotenv()

app = Flask(__name__)
app.json.ensure_ascii = False


# La secret_key sert à signer les cookies de session.
# Si elle change, toutes les sessions actives sont invalidées.
# En prod elle vient du .env — jamais hardcodée dans le code.
app.secret_key = os.getenv('SECRET_KEY', 'dev-only-change-me')

@app.before_request
def maintenance_mode():
    if os.getenv('MAINTENANCE_MODE', '0') in ('1', 'true'):
        if not request.path.startswith('/static'):
            return render_template('maintenance.html'), 503

# Branchement des Blueprints
from routes_auth import auth_bp
app.register_blueprint(auth_bp)
from routes_api import api_bp
app.register_blueprint(api_bp)
from routes_client import client_bp
app.register_blueprint(client_bp)
from routes_admin_clients import admin_clients_bp
app.register_blueprint(admin_clients_bp)
from routes_admin_compta import admin_compta_bp
app.register_blueprint(admin_compta_bp)
from routes_admin_tools import admin_tools_bp
app.register_blueprint(admin_tools_bp)
from routes_admin_comptes import admin_comptes_bp
app.register_blueprint(admin_comptes_bp)

_MOIS = ['jan', 'fév', 'mar', 'avr', 'mai', 'juin', 'juil', 'août', 'sep', 'oct', 'nov', 'déc']


@app.before_request
def check_maintenance():
    """Intercepte les requêtes clients si le mode maintenance est activé dans le .env"""
    if os.getenv('MAINTENANCE_MODE') == '1':
        if request.path.startswith('/portail') and not request.path.startswith('/static'):
            return render_template('maintenance.html'), 503


@app.context_processor
def portail_badge_ctx():
    ctx = {'messages_non_lus': 0, 'leads_non_lus': 0}
    try:
        if 'client_id' in session:
            try:
                conn = get_db()
                count = conn.execute(
                    "SELECT COUNT(*) FROM messages_client WHERE client_id=? AND lu_client=0 AND reponse IS NOT NULL",
                    (session['client_id'],)
                ).fetchone()[0]
                conn.close()
            except Exception:
                count = 0
            ctx['messages_non_lus'] = count
        if 'user_id' in session:
            try:
                conn = get_db()
                ctx['leads_non_lus'] = conn.execute(
                    "SELECT COUNT(*) FROM leads WHERE lu = 0"
                ).fetchone()[0]
                conn.close()
            except Exception:
                ctx['leads_non_lus'] = 0
    except Exception:
        pass
    return ctx

@app.template_filter('fmt_date')
def fmt_date(s):
    if not s:
        return ''
    try:
        dt = datetime.datetime.strptime(s, '%Y-%m-%d')
        return f"{dt.day} {_MOIS[dt.month - 1]}"
    except Exception:
        return s


@app.template_filter('to_local')
def to_local(dt_str):
    """Convertit une string datetime UTC (stockée en DB) en heure locale Eastern."""
    if not dt_str:
        return ''
    try:
        s = str(dt_str)[:19].replace('T', ' ')
        dt_utc = datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S').replace(
            tzinfo=datetime.timezone.utc
        )
        return dt_utc.astimezone(_EASTERN).strftime('%Y-%m-%dT%H:%M:%S')
    except Exception:
        return str(dt_str)


# Limite la taille des uploads à 16 MB — au-delà Flask retourne une erreur 413
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Permet au cookie de session de fonctionner dans un iframe cross-site (démo portfolio)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE']   = True

# Dossier de stockage des fichiers uploadés — en dehors de static/ pour ne pas
# être servi directement. Flask contrôle qui peut télécharger quoi.
RAILWAY_DIR = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')
if RAILWAY_DIR:
    UPLOAD_ROOT = os.path.join(RAILWAY_DIR, 'uploads')
else:
    UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), 'uploads')

ALLOWED_EXTENSIONS = {
    '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg',
    '.zip', '.doc', '.docx', '.xls', '.xlsx', '.mp4', '.mov', '.txt', '.fig',
}

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
        'admin_impersonating': session.get('admin_impersonating', False),
        'role': session.get('user_role',''),
    }

# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    clients = conn.execute(
        'SELECT * FROM clients WHERE deleted = 0 ORDER BY created_at DESC'
    ).fetchall()

    stats = {
        'total':     sum(1 for c in clients if not c['demo']),
        'prospects': sum(1 for c in clients if c['statut'] == 'prospect' and not c['demo']),
        'actifs':    sum(1 for c in clients if c['statut'] == 'actif' and not c['demo']),
        'completes': sum(1 for c in clients if c['statut'] == 'complété' and not c['demo']),
    }

    unread_rows = conn.execute(
        'SELECT client_id, COUNT(*) as cnt FROM messages_client WHERE lu = 0 GROUP BY client_id'
    ).fetchall()
    unread_counts = {row['client_id']: row['cnt'] for row in unread_rows}

    messages_nonlus = conn.execute('''
        SELECT mc.id, mc.sujet, mc.message, mc.created_at,
               c.nom as client_nom, c.id as client_id
        FROM messages_client mc
        JOIN clients c ON c.id = mc.client_id
        WHERE mc.lu = 0 AND (mc.reponse IS NULL OR mc.reponse = '')
        ORDER BY mc.created_at DESC
        LIMIT 8
    ''').fetchall()

    factures_attente = conn.execute('''
        SELECT f.id, f.numero, f.milestone_titre, f.description,
               f.montant, f.statut, f.date_emission,
               c.nom as client_nom, c.id as client_id
        FROM factures f
        JOIN clients c ON c.id = f.client_id
        WHERE f.statut != 'payée' AND c.demo = 0
        ORDER BY f.date_emission DESC
    ''').fetchall()

    # NOTE: Les projets actifs sont maintenant chargés en AJAX via /api/dashboard/active-projects

    week_start  = (datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())).isoformat()
    month_start = datetime.date.today().replace(day=1).isoformat()

    heures_semaine = conn.execute('''
        SELECT COALESCE(SUM(duree_minutes), 0) as total_min,
               COALESCE(SUM(CASE WHEN type_facturation='horaire' AND taux_applique IS NOT NULL
                    THEN (duree_minutes / 60.0) * taux_applique ELSE 0 END), 0) as montant
        FROM entrees_temps
        WHERE date >= ? AND (heure_fin IS NOT NULL OR mode = 'manuel')
    ''', (week_start,)).fetchone()

    heures_mois = conn.execute('''
        SELECT COALESCE(SUM(duree_minutes), 0) as total_min,
               COALESCE(SUM(CASE WHEN type_facturation='horaire' AND taux_applique IS NOT NULL
                    THEN (duree_minutes / 60.0) * taux_applique ELSE 0 END), 0) as montant
        FROM entrees_temps
        WHERE date >= ? AND (heure_fin IS NOT NULL OR mode = 'manuel')
    ''', (month_start,)).fetchone()

    ratio_data = conn.execute('''
        SELECT
            COALESCE(SUM(CASE WHEN e.client_id IS NOT NULL AND COALESCE(c.rnd, 0) = 0 THEN e.duree_minutes ELSE 0 END), 0) as min_client,
            COALESCE(SUM(CASE WHEN e.client_id IS NULL OR COALESCE(c.rnd, 0) = 1 THEN e.duree_minutes ELSE 0 END), 0) as min_interne,
            COALESCE(SUM(e.duree_minutes), 0) as min_total
        FROM entrees_temps e
        LEFT JOIN clients c ON c.id = e.client_id
        WHERE e.date >= ? AND (e.heure_fin IS NOT NULL OR e.mode = 'manuel')
    ''', (month_start,)).fetchone()

    banques_actives = conn.execute('''
        SELECT b.*, c.nom as client_nom,
               (b.minutes_total - b.minutes_utilisees) as minutes_restantes
        FROM banque_heures b
        JOIN clients c ON c.id = b.client_id
        WHERE b.statut = 'actif'
        ORDER BY minutes_restantes ASC
    ''').fetchall()

    conn.close()

    return render_template('admin_dashboard.html',
                           clients=clients, stats=stats,
                           unread_counts=unread_counts,
                           messages_nonlus=messages_nonlus,
                           factures_attente=factures_attente,
                           heures_semaine=heures_semaine,
                           heures_mois=heures_mois,
                           ratio_data=ratio_data,
                           banques_actives=banques_actives,
                           name=session['user_name'])

@app.route('/api/dashboard/active-projects')
@login_required
def api_dashboard_active_projects():
    """API Endpoint pour le Skeleton Loading du Dashboard"""
    conn = get_db()

    clients_actifs = conn.execute(
        "SELECT * FROM clients WHERE statut IN ('actif', 'prospect', 'complété') AND demo = 0 AND deleted = 0 ORDER BY statut, nom ASC"
    ).fetchall()

    if not clients_actifs:
        conn.close()
        return jsonify([])

    # Batch: tous les contrats en une seule requête au lieu de 1 par client
    client_ids    = [c['id'] for c in clients_actifs]
    placeholders  = ','.join('?' * len(client_ids))
    contrats_all  = conn.execute(
        f'SELECT * FROM contrats WHERE client_id IN ({placeholders}) ORDER BY created_at DESC',
        client_ids
    ).fetchall()

    # Batch: toutes les factures en attente groupées par contrat
    factures_counts = {}
    if contrats_all:
        contrat_ids  = [c['id'] for c in contrats_all]
        ph_contrats  = ','.join('?' * len(contrat_ids))
        factures_counts = {
            row['contrat_id']: row['n']
            for row in conn.execute(
                f"SELECT contrat_id, COUNT(*) as n FROM factures WHERE contrat_id IN ({ph_contrats}) AND statut != 'payée' AND deleted = 0 GROUP BY contrat_id",
                contrat_ids
            ).fetchall()
        }

    conn.close()

    clients_dict = {c['id']: c for c in clients_actifs}

    rows = []
    for contrat in contrats_all:
        c  = clients_dict[contrat['client_id']]
        ms = safe_json_loads(contrat['milestones'], default=[])
        ms = _compute_deadlines(ms)
        action = None
        for m in ms:
            s = m.get('statut', 'en attente')
            if s == 'livré':
                action = {'type': 'attente_appro', 'label': f'Client doit approuver : {m["titre"]}', 'urgent': True}
                break
            if s == 'approuvé':
                action = {'type': 'a_payer', 'label': f'À marquer payé : {m["titre"]}', 'urgent': True}
                break
            if s == 'en cours':
                action = {'type': 'en_cours', 'label': f'En cours : {m["titre"]}', 'urgent': False}
                break
        if not action:
            for m in ms:
                if m.get('statut') == 'en attente':
                    action = {'type': 'a_demarrer', 'label': f'À démarrer : {m["titre"]}', 'urgent': False}
                    break
        if not action and ms:
            action = {'type': 'termine', 'label': 'Tous les milestones complétés', 'urgent': False}

        faits = sum(1 for m in ms if m.get('statut') in ('payé', 'approuvé', 'livré'))
        rows.append({
            'client': dict(c), 'contrat': dict(contrat), 'ms_total': len(ms),
            'ms_faits': faits, 'action': action, 'factures_att': factures_counts.get(contrat['id'], 0),
        })

    return jsonify(rows)


# ─── COMMAND CENTER ───────────────────────────────────────────────────────────

@app.route('/command-center')
@login_required
def command_center():
    return redirect('/dashboard')



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
    ok = send_notification_email(
        f'Facture {facture["numero"] or ""} – {contrat_nom}',
        f'Bonjour {client["nom"]},\n\nTa facture de {montant} pour le projet "{contrat_nom}" est disponible.',
        to=client['email'],
        html=email_facture(
            client['nom'],
            facture['numero'] or '',
            contrat_nom,
            description,
            montant,
            facture['date_emission'],
            facture['statut']
        )
    )
    if not ok:
        return jsonify({'error': 'Erreur SMTP'}), 500
    return jsonify({'ok': True})


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


@app.route('/clients/<int:client_id>/factures/<int:facture_id>/pdf')
@login_required
def facture_pdf(client_id, facture_id):
    if not WEASYPRINT_AVAILABLE:
        flash("La génération de PDF nécessite des librairies Linux. Teste cette fonctionnalité une fois en ligne sur Railway !", "error")
        return redirect(f'/clients/{client_id}')

    conn = get_db()
    facture = conn.execute(
        'SELECT * FROM factures WHERE id = ? AND client_id = ?', (facture_id, client_id)
    ).fetchone()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    conn.close()
    if not facture:
        return redirect(f'/clients/{client_id}')
        
    html_content = render_template('facture_print.html', facture=facture, client=client)
    pdf_data = HTML(string=html_content, base_url=request.url_root).write_pdf()
    
    response = Response(pdf_data, mimetype='application/pdf')
    response.headers['Content-Disposition'] = f'attachment; filename="Facture_{facture["numero"] or "sans-numero"}.pdf"'
    return response


# ── GALERIE LIVRABLES ─────────────────────────────────────────────────────────

@app.route('/clients/<int:client_id>/contrat/<int:contrat_id>/milestone/<int:index>/livrables/upload', methods=['POST'])
@login_required
def livrable_upload(client_id, contrat_id, index):
    fichier = request.files.get('fichier')
    if not fichier or fichier.filename == '':
        flash('Aucun fichier sélectionné.', 'error')
        return redirect(f'/clients/{client_id}')
    nom_original = fichier.filename
    nom_secure   = secure_filename(nom_original)
    if not nom_secure:
        flash('Nom de fichier invalide.', 'error')
        return redirect(f'/clients/{client_id}')
    ext = os.path.splitext(nom_secure)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash(f'Type de fichier non autorisé ({ext or "sans extension"}).', 'error')
        return redirect(f'/clients/{client_id}')
    nom_stocke   = str(uuid.uuid4()) + ext
    dossier      = os.path.join(UPLOAD_ROOT, str(client_id))
    os.makedirs(dossier, exist_ok=True)
    fichier.save(os.path.join(dossier, nom_stocke))
    conn = get_db()
    conn.execute(
        '''INSERT INTO fichiers (client_id, nom_original, nom_stocke, taille, milestone_index)
           VALUES (?, ?, ?, ?, ?)''',
        (client_id, nom_original, nom_stocke,
         os.path.getsize(os.path.join(dossier, nom_stocke)), index)
    )
    conn.commit()
    conn.close()
    flash('Livrable ajouté.', 'success')
    return redirect(f'/clients/{client_id}')


if __name__ == '__main__':
    app.run(debug=True)