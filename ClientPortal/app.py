import datetime
import json
import os
import secrets
import smtplib
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
    print("⚠️ WeasyPrint (GTK) introuvable. Génération de PDF désactivée en local.")

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


# La secret_key sert à signer les cookies de session.
# Si elle change, toutes les sessions actives sont invalidées.
# En prod elle vient du .env — jamais hardcodée dans le code.
app.secret_key = os.getenv('SECRET_KEY', 'dev-only-change-me')

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

    rows = []
    for c in clients_actifs:
        contrats = conn.execute(
            'SELECT * FROM contrats WHERE client_id = ? ORDER BY created_at DESC',
            (c['id'],)
        ).fetchall()
        for contrat in contrats:
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
            factures_att = conn.execute(
                "SELECT COUNT(*) as n FROM factures WHERE contrat_id = ? AND statut != 'payée' AND deleted = 0",
                (contrat['id'],)
            ).fetchone()['n']
            rows.append({
                'client': dict(c), 'contrat': dict(contrat), 'ms_total': len(ms),
                'ms_faits': faits, 'action': action, 'factures_att': factures_att,
            })
    conn.close()
    return jsonify(rows)


# ─── COMMAND CENTER ───────────────────────────────────────────────────────────

@app.route('/command-center')
@login_required
def command_center():
    return redirect('/dashboard')

@app.route('/command-center-legacy')
@login_required
def command_center_legacy():
    conn = get_db()
    clients_all = conn.execute(
        "SELECT * FROM clients WHERE statut IN ('actif', 'prospect', 'complété') AND demo = 0 ORDER BY statut, nom ASC"
    ).fetchall()

    rows = []
    for c in clients_all:
        contrats = conn.execute(
            'SELECT * FROM contrats WHERE client_id = ? ORDER BY created_at DESC',
            (c['id'],)
        ).fetchall()

        for contrat in contrats:
            ms = safe_json_loads(contrat['milestones'], default=[])
            ms = _compute_deadlines(ms)

            # Milestone en cours + prochaine action
            action = None
            for i, m in enumerate(ms):
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
            factures_att = conn.execute(
                "SELECT COUNT(*) as n FROM factures WHERE contrat_id = ? AND statut != 'payée'",
                (contrat['id'],)
            ).fetchone()['n']

            rows.append({
                'client':         dict(c),
                'contrat':        dict(contrat),
                'ms_total':       len(ms),
                'ms_faits':       faits,
                'action':         action,
                'factures_att':   factures_att,
            })

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
    return render_template('command_center.html', rows=rows,
                           heures_semaine=heures_semaine, heures_mois=heures_mois,
                           ratio_data=ratio_data, banques_actives=banques_actives)


@app.route('/plan')
@login_required
def plan():
    conn = get_db()
    plan_stats = conn.execute('''
        SELECT
            COUNT(*) as total_clients,
            COUNT(CASE WHEN statut = 'actif' THEN 1 END) as clients_actifs,
            (SELECT COALESCE(SUM(montant), 0) FROM factures WHERE statut = 'payée') as revenus_realises
        FROM clients
        WHERE deleted = 0
    ''').fetchone()
    conn.close()
    return render_template('plan.html', stats=plan_stats)



@app.route('/roadmap')
@login_required
def roadmap():
    return redirect('/plan')


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


# ── LEADS (formulaire de contact public tntm.ca) ──────────────────────────────

@app.route('/leads')
@login_required
def leads_list():
    conn = get_db()
    leads = conn.execute('SELECT * FROM leads ORDER BY created_at DESC').fetchall()
    conn.execute('UPDATE leads SET lu = 1 WHERE lu = 0')
    conn.commit()
    conn.close()
    return render_template('leads.html', leads=leads)


@app.route('/leads/<int:lead_id>/delete', methods=['POST'])
@login_required
def lead_delete(lead_id):
    conn = get_db()
    conn.execute('DELETE FROM leads WHERE id = ?', (lead_id,))
    conn.commit()
    conn.close()
    return redirect('/leads')


# ── GALERIE LIVRABLES ─────────────────────────────────────────────────────────

@app.route('/clients/<int:client_id>/contrat/<int:contrat_id>/milestone/<int:index>/livrables/upload', methods=['POST'])
@login_required
def livrable_upload(client_id, contrat_id, index):
    fichier = request.files.get('fichier')
    if not fichier or fichier.filename == '':
        flash('Aucun fichier sélectionné.', 'error')
        return redirect(f'/clients/{client_id}')
    nom_original = fichier.filename
    ext          = os.path.splitext(nom_original)[1].lower()
    nom_stocke   = str(uuid.uuid4()) + ext
    dossier      = os.path.join('uploads', str(client_id))
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
    titre        = request.form.get('titre', '').strip()
    type_        = request.form.get('type', 'texte')
    sous_titre   = request.form.get('sous_titre', '').strip()
    options      = request.form.get('options', '').strip()
    requis       = 1 if request.form.get('requis') else 0
    prefill_field = request.form.get('prefill_field', '').strip() or None
    if not titre and type_ != 'section':
        flash('Le titre de la question est requis.', 'error')
        return redirect(f'/formulaires/{fid}')
    conn = get_db()
    max_ordre = conn.execute(
        'SELECT COALESCE(MAX(ordre), -1) FROM formulaire_questions WHERE formulaire_id = ?', (fid,)
    ).fetchone()[0]
    conn.execute(
        'INSERT INTO formulaire_questions (formulaire_id, ordre, titre, sous_titre, type, options, requis, prefill_field) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (fid, max_ordre + 1, titre or '—', sous_titre or None, type_, options or None, requis, prefill_field)
    )
    conn.commit()
    conn.close()
    return redirect(f'/formulaires/{fid}')


@app.route('/formulaires/<int:fid>/questions/<int:qid>/edit', methods=['POST'])
@login_required
def formulaire_question_edit(fid, qid):
    titre         = request.form.get('titre', '').strip()
    sous_titre    = request.form.get('sous_titre', '').strip()
    type_         = request.form.get('type', 'texte')
    options       = request.form.get('options', '').strip()
    requis        = 1 if request.form.get('requis') else 0
    prefill_field = request.form.get('prefill_field', '').strip() or None
    conn = get_db()
    conn.execute(
        'UPDATE formulaire_questions SET titre=?, sous_titre=?, type=?, options=?, requis=?, prefill_field=? WHERE id=? AND formulaire_id=?',
        (titre, sous_titre or None, type_, options or None, requis, prefill_field, qid, fid)
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


# ── TARIFS ────────────────────────────────────────────────────────────────────

@app.route('/tarifs')
@login_required
def tarifs():
    conn = get_db()
    rows = conn.execute('SELECT * FROM tarifs ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('tarifs_admin.html', tarifs=rows)


@app.route('/tarifs/new', methods=['POST'])
@login_required
def tarif_new():
    conn = get_db()
    max_ordre = conn.execute('SELECT COALESCE(MAX(ordre), -1) FROM tarifs').fetchone()[0]
    conn.execute(
        'INSERT INTO tarifs (titre, description, prix, unite, inclus, non_inclus, actif, ordre) VALUES (?,?,?,?,?,?,?,?)',
        (
            request.form.get('titre', '').strip(),
            request.form.get('description', '').strip() or None,
            float(request.form.get('prix') or 0) or None,
            request.form.get('unite', '/ projet').strip(),
            request.form.get('inclus', '').strip() or None,
            request.form.get('non_inclus', '').strip() or None,
            1 if request.form.get('actif') else 0,
            max_ordre + 1,
        )
    )
    conn.commit()
    conn.close()
    flash('Tarif ajouté.', 'success')
    return redirect('/tarifs')


@app.route('/tarifs/<int:tid>/edit', methods=['POST'])
@login_required
def tarif_edit(tid):
    conn = get_db()
    conn.execute(
        'UPDATE tarifs SET titre=?, description=?, prix=?, unite=?, inclus=?, non_inclus=?, actif=?, ordre=? WHERE id=?',
        (
            request.form.get('titre', '').strip(),
            request.form.get('description', '').strip() or None,
            float(request.form.get('prix') or 0) or None,
            request.form.get('unite', '/ projet').strip(),
            request.form.get('inclus', '').strip() or None,
            request.form.get('non_inclus', '').strip() or None,
            1 if request.form.get('actif') else 0,
            int(request.form.get('ordre', 0)),
            tid,
        )
    )
    conn.commit()
    conn.close()
    flash('Tarif mis à jour.', 'success')
    return redirect('/tarifs')


@app.route('/tarifs/<int:tid>/delete', methods=['POST'])
@login_required
def tarif_delete(tid):
    conn = get_db()
    conn.execute('DELETE FROM tarifs WHERE id = ?', (tid,))
    conn.commit()
    conn.close()
    flash('Tarif supprimé.', 'success')
    return redirect('/tarifs')


# ── PACKAGES ──────────────────────────────────────────────────────────────────

@app.route('/packages', methods=['GET', 'POST'])
@login_required
def packages():
    conn = get_db()
    clients = conn.execute(
        "SELECT id, nom FROM clients WHERE demo = 0 ORDER BY nom"
    ).fetchall()

    if request.method == 'POST':
        nom           = request.form.get('nom', '').strip()
        client_id     = int(request.form.get('client_id', 0))
        h_dev         = float(request.form.get('h_dev') or 0)
        h_design      = float(request.form.get('h_design') or 0)
        h_integration = float(request.form.get('h_integration') or 0)
        h_admin       = float(request.form.get('h_admin') or 0)
        marge         = int(request.form.get('marge') or 0)

        sous_total = h_dev * 80 + h_design * 65 + h_integration * 55 + h_admin * 50
        avec_marge = sous_total * (1 + marge / 100)

        def _arrondir(montant):
            if montant <= 0:
                return 0
            centaine = int(montant // 100) * 100
            for candidat in (centaine + 50, centaine + 99, centaine + 150):
                if candidat >= montant:
                    return candidat
            return centaine + 199

        prix_final = _arrondir(avec_marge)

        conn.execute('''
            INSERT INTO packages
                (nom, client_id, heures_dev, heures_design, heures_integration, heures_admin, marge, prix_final)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nom, client_id, h_dev, h_design, h_integration, h_admin, marge, prix_final))
        conn.commit()
        flash(f'Forfait "{nom}" enregistré — {prix_final:.0f}$', 'success')
        conn.close()
        return redirect('/packages')

    packages_list = conn.execute('''
        SELECT p.*, c.nom as client_nom
        FROM packages p
        JOIN clients c ON p.client_id = c.id
        ORDER BY p.created_at DESC
    ''').fetchall()
    conn.close()

    return render_template('packages.html', clients=clients, packages=packages_list)


@app.route('/packages/<int:pkg_id>/delete', methods=['POST'])
@login_required
def package_delete(pkg_id):
    conn = get_db()
    conn.execute('DELETE FROM packages WHERE id = ?', (pkg_id,))
    conn.commit()
    conn.close()
    flash('Forfait supprimé.', 'success')
    return redirect('/packages')

@app.route('/packages/<int:pkg_id>/creer-contrat', methods=['POST'])
@login_required
def package_creer_contrat(pkg_id):
    conn = get_db()
    pkg = conn.execute(
        'SELECT p.*, c.nom as client_nom FROM packages p JOIN clients c ON c.id = p.client_id WHERE p.id = ?',
        (pkg_id,)
    ).fetchone()

    if not pkg:
        conn.close()
        flash('Forfait introuvable.', 'error')
        return redirect('/packages')

    prix = pkg['prix_final']

    # 4 milestones pré-remplis avec la répartition standard 25/25/35/15%
    milestones = [
        {'titre': 'M1 — Démarrage & Contrat', 'livrable': 'Acompte initial — lancement du projet', 'prix': str(round(prix * 0.25)), 'date': '', 'statut': 'en attente', 'lien_preview': '', 'preview_visible': False},
        {'titre': 'M2 — Design & Maquettes', 'livrable': 'Maquettes approuvées par le client', 'prix': str(round(prix * 0.25)), 'date': '', 'statut': 'en attente', 'lien_preview': '', 'preview_visible': False},
        {'titre': 'M3 — Développement', 'livrable': 'Site fonctionnel livré en prévisualisation', 'prix': str(round(prix * 0.35)), 'date': '', 'statut': 'en attente', 'lien_preview': '', 'preview_visible': False},
        {'titre': 'M4 — Livraison finale', 'livrable': 'Mise en ligne + passation de dossier', 'prix': str(round(prix * 0.15)), 'date': '', 'statut': 'en attente', 'lien_preview': '', 'preview_visible': False},
    ]

    snapshot = {
        'nom': pkg['nom'],
        'heures_dev': pkg['heures_dev'],
        'heures_design': pkg['heures_design'],
        'heures_integration': pkg['heures_integration'],
        'heures_admin': pkg['heures_admin'],
        'marge': pkg['marge'],
        'prix_final': pkg['prix_final'],
    }

    titre_scope = "Migration / Copie Conforme" if pkg['heures_design'] == 0 else "Développement web complet"

    scope_auto = f"{titre_scope} — {pkg['nom']}\n\n"
    scope_auto += f"• Développement : {pkg['heures_dev']}h\n"
    
    if pkg['heures_design'] > 0:
        scope_auto += f"• Design UI/UX : {pkg['heures_design']}h\n"
        
    scope_auto += f"• Intégration & Maintenance : {pkg['heures_integration']}h\n"
    scope_auto += f"• Admin & Gestion : {pkg['heures_admin']}h"

    cursor = conn.execute(
        'INSERT INTO contrats (client_id, nom, scope, milestones, statut, package_snapshot) VALUES (?,?,?,?,?,?)',
        (
            pkg['client_id'],
            pkg['nom'],
            scope_auto,
            json.dumps(milestones, ensure_ascii=False),
            'draft',
            json.dumps(snapshot, ensure_ascii=False),
        )
    )
    contrat_id = cursor.lastrowid
    conn.commit()
    conn.close()

    flash(f'Contrat créé depuis le forfait « {pkg["nom"]} ». Révise et envoie au client !', 'success')
    return redirect(f'/clients/{pkg["client_id"]}/contrat/{contrat_id}')

if __name__ == '__main__':
    app.run(debug=True)