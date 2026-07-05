import json
import uuid
import datetime
import os
from flask import Blueprint, render_template, request, redirect, session, flash, jsonify, send_from_directory
from database import get_db
from utils import login_required, _compute_deadlines, group_messages, send_notification_email, _now, safe_json_loads
from email_templates import email_contrat_envoye, email_milestone_livre, email_bienvenue, email_reponse_message, email_message_naomie, email_commentaire_fichier_admin
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

admin_clients_bp = Blueprint('admin_clients', __name__)

if os.getenv('RAILWAY_VOLUME_MOUNT_PATH'):
    UPLOAD_ROOT = os.path.join(os.getenv('RAILWAY_VOLUME_MOUNT_PATH'), 'uploads')
else:
    UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), 'uploads')

ALLOWED_EXTENSIONS = {
    '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg',
    '.zip', '.doc', '.docx', '.xls', '.xlsx', '.mp4', '.mov', '.txt', '.fig',
}

# ─── CLIENTS ──────────────────────────────────────────────────────────────────

@admin_clients_bp.route('/clients/new', methods=['POST'])
@login_required
def new_client():
    nom = request.form.get('nom', '').strip()
    if not nom:
        return redirect('/dashboard')

    conn = get_db()
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
    client_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return redirect(f'/clients/{client_id}')


@admin_clients_bp.route('/clients/<int:client_id>')
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

    contrat = conn.execute(
        'SELECT * FROM contrats WHERE client_id = ? ORDER BY created_at DESC LIMIT 1',
        (client_id,)
    ).fetchone()

    questionnaire = conn.execute(
        'SELECT * FROM questionnaires_client WHERE client_id = ?',
        (client_id,)
    ).fetchone()

    fichiers_raw = conn.execute(
        'SELECT * FROM fichiers WHERE client_id = ? ORDER BY uploaded_at DESC',
        (client_id,)
    ).fetchall()

    comments_raw = conn.execute(
        '''SELECT fc.* FROM fichier_commentaires fc
           JOIN fichiers f ON f.id = fc.fichier_id
           WHERE f.client_id = ? ORDER BY fc.created_at ASC''',
        (client_id,)
    ).fetchall()

    comments_by_file = {}
    for c in comments_raw:
        comments_by_file.setdefault(c['fichier_id'], []).append(dict(c))

    fichiers = []
    for f in fichiers_raw:
        fd = dict(f)
        fd['commentaires'] = comments_by_file.get(f['id'], [])
        fichiers.append(fd)

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

    conn.execute(
        'UPDATE messages_client SET lu = 1 WHERE client_id = ? AND lu = 0',
        (client_id,)
    )
    conn.commit()

    banques_heures = conn.execute(
        'SELECT * FROM banque_heures WHERE client_id = ? ORDER BY date_achat DESC',
        (client_id,)
    ).fetchall()

    activites = conn.execute(
        'SELECT * FROM client_activity WHERE client_id = ? ORDER BY created_at DESC LIMIT 50',
        (client_id,)
    ).fetchall()

    conn.close()

    consultations_parsed = []
    for c in consultations:
        d = dict(c)
        d['reponses_parsed'] = safe_json_loads(c['reponses'], default={})
        consultations_parsed.append(d)

    questionnaire_rep = safe_json_loads(questionnaire['reponses'], default={}) if questionnaire else {}

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

    projets = []
    for c in contrats_all:
        m = _compute_deadlines(safe_json_loads(c['milestones'], default=[]))
        total = sum(float(x.get('prix', 0) or 0) for x in m)
        projets.append({'contrat': dict(c), 'milestones': m, 'total': total})

    contrat = contrats_all[-1] if contrats_all else None
    milestones = projets[-1]['milestones'] if projets else []
    total_contrat = projets[-1]['total'] if projets else 0

    return render_template('client_fiche.html',
                           client=client, consultations=consultations_parsed,
                           contrat=contrat, milestones=milestones, total_contrat=total_contrat,
                           projets=projets, questionnaire=questionnaire, questionnaire_rep=questionnaire_rep,
                           fichiers=fichiers, messages=messages, msg_threads=group_messages(messages),
                           factures=factures, form_reponses=form_reponses,
                           formulaires_assignes=formulaires_assignes, formulaires_disponibles=formulaires_disponibles,
                           banques_heures=banques_heures, activites=activites, name=session['user_name'])


@admin_clients_bp.route('/clients/<int:client_id>/edit', methods=['POST'])
@login_required
def edit_client(client_id):
    conn = get_db()
    conn.execute('''
        UPDATE clients
        SET nom=?, email=?, entreprise=?, secteur=?, notes=?, statut=?
        WHERE id=?
    ''', (
        request.form.get('nom', '').strip(), request.form.get('email', '').strip(),
        request.form.get('entreprise', '').strip(), request.form.get('secteur', '').strip(),
        request.form.get('notes', '').strip(), request.form.get('statut', 'prospect'), client_id
    ))
    conn.commit()
    conn.close()
    flash('Client mis à jour.', 'success')
    return redirect(f'/clients/{client_id}')

@admin_clients_bp.route('/clients/<int:client_id>/toggle-demo', methods=['POST'])
@login_required
def toggle_demo(client_id):
    conn = get_db()
    current = conn.execute('SELECT demo FROM clients WHERE id = ?', (client_id,)).fetchone()
    new_val = 0 if (current and current['demo']) else 1
    conn.execute('UPDATE clients SET demo = ? WHERE id = ?', (new_val, client_id))
    conn.commit()
    conn.close()
    return redirect(f'/clients/{client_id}')

@admin_clients_bp.route('/clients/<int:client_id>/toggle-rnd', methods=['POST'])
@login_required
def toggle_rnd(client_id):
    conn = get_db()
    current = conn.execute('SELECT rnd FROM clients WHERE id = ?', (client_id,)).fetchone()
    new_val = 0 if (current and current['rnd']) else 1
    conn.execute('UPDATE clients SET rnd = ? WHERE id = ?', (new_val, client_id))
    conn.commit()
    conn.close()
    return redirect(f'/clients/{client_id}')

@admin_clients_bp.route('/clients/<int:client_id>/statut', methods=['POST'])
@login_required
def client_statut(client_id):
    statut = request.form.get('statut', 'prospect')
    conn = get_db()
    conn.execute('UPDATE clients SET statut = ? WHERE id = ?', (statut, client_id))
    conn.commit()
    conn.close()
    flash(f'Statut mis à jour : {statut}.', 'success')
    return redirect(f'/clients/{client_id}')

@admin_clients_bp.route('/clients/<int:client_id>/delete', methods=['POST'])
@login_required
def delete_client(client_id):
    conn = get_db()
    conn.execute('UPDATE clients SET deleted = 1 WHERE id = ?', (client_id,))
    conn.commit()
    conn.close()
    flash('Client déplacé dans la corbeille (données conservées pour la comptabilité).', 'success')
    return redirect('/dashboard')

# ─── CONSULTATIONS ────────────────────────────────────────────────────────────

@admin_clients_bp.route('/clients/<int:client_id>/consultation/new', methods=['GET', 'POST'])
@login_required
def new_consultation(client_id):
    conn = get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    if not client:
        conn.close()
        return redirect('/dashboard')

    questionnaire = conn.execute('SELECT reponses FROM questionnaires_client WHERE client_id = ?', (client_id,)).fetchone()
    prefill = safe_json_loads(questionnaire['reponses'], default={}) if questionnaire else {}

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
            (client_id, today, json.dumps(reponses, ensure_ascii=False), request.form.get('notes', ''))
        )
        conn.commit()
        conn.close()
        return redirect(f'/clients/{client_id}')

    conn.close()
    return render_template('consultation.html', client=client, prefill=prefill, name=session['user_name'])

@admin_clients_bp.route('/consultations/<int:consult_id>/delete', methods=['POST'])
@login_required
def delete_consultation(consult_id):
    conn = get_db()
    row = conn.execute('SELECT client_id FROM consultations WHERE id = ?', (consult_id,)).fetchone()
    client_id = row['client_id'] if row else None
    conn.execute('DELETE FROM consultations WHERE id = ?', (consult_id,))
    conn.commit()
    conn.close()
    return redirect(f'/clients/{client_id}' if client_id else '/dashboard')

# ─── CONTRATS ─────────────────────────────────────────────────────────────────

@admin_clients_bp.route('/clients/<int:client_id>/contrat')
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
    
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO contrats (client_id, scope, milestones, statut, nom) VALUES (?,?,?,?,?)',
        (client_id, '', '[]', 'draft', 'Projet principal')
    )
    contrat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return redirect(f'/clients/{client_id}/contrat/{contrat_id}')

@admin_clients_bp.route('/clients/<int:client_id>/contrat/<int:contrat_id>', methods=['GET', 'POST'])
@login_required
def contrat_edit(client_id, contrat_id):
    conn = get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    if not client:
        conn.close()
        return redirect('/dashboard')

    existing = conn.execute('SELECT * FROM contrats WHERE id = ? AND client_id = ?', (contrat_id, client_id)).fetchone()
    if not existing:
        conn.close()
        return redirect(f'/clients/{client_id}')

    if request.method == 'POST':
        raw = request.form.get('milestones_json', '[]')
        milestones = safe_json_loads(raw, default=[])

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

    milestones = safe_json_loads(existing['milestones'], default=[])
    conn.close()
    return render_template('contrat.html', client=client, contrat=existing, milestones=milestones, name=session['user_name'])

@admin_clients_bp.route('/clients/<int:client_id>/projet/new', methods=['POST'])
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

@admin_clients_bp.route('/clients/<int:client_id>/contrat/<int:contrat_id>/envoyer-email', methods=['POST'])
@login_required
def contrat_envoyer_email(client_id, contrat_id):
    conn = get_db()
    client  = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    contrat = conn.execute('SELECT * FROM contrats WHERE id = ? AND client_id = ?', (contrat_id, client_id)).fetchone()
    conn.close()
    if not client or not contrat:
        flash('Client ou contrat introuvable.', 'error')
        return redirect(f'/clients/{client_id}')
    if not client['email']:
        flash('Ce client n\'a pas d\'adresse email enregistrée.', 'error')
        return redirect(f'/clients/{client_id}')
    nom_projet = contrat['nom'] or 'ton projet'
    ok = send_notification_email(
        f'[TNTMom] Ton contrat est prêt à signer — {nom_projet}',
        f'Bonjour {client["nom"]},\n\nTon contrat "{nom_projet}" est prêt. Connecte-toi pour le signer.',
        to=client['email'],
        html=email_contrat_envoye(client['nom'], nom_projet)
    )
    if ok: flash(f'Email envoyé à {client["email"]}.', 'success')
    else: flash(f'Échec de l\'envoi — vérifie les variables GMAIL dans le .env de PA.', 'error')
    return redirect(f'/clients/{client_id}')

@admin_clients_bp.route('/clients/<int:client_id>/contrat/<int:contrat_id>/delete', methods=['POST'])
@login_required
def contrat_delete(client_id, contrat_id):
    conn = get_db()
    conn.execute('DELETE FROM factures WHERE contrat_id = ?', (contrat_id,))
    conn.execute('DELETE FROM contrats WHERE id = ? AND client_id = ?', (contrat_id, client_id))
    conn.commit()
    conn.close()
    flash('Projet supprimé.', 'success')
    return redirect(f'/clients/{client_id}')

@admin_clients_bp.route('/clients/<int:client_id>/banque-heures/new', methods=['POST'])
@login_required
def banque_heures_new(client_id):
    conn = get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    if not client:
        conn.close()
        return redirect('/dashboard')
    conn.execute(
        "INSERT INTO banque_heures (client_id, minutes_total, minutes_utilisees, date_achat, statut) VALUES (?, 300, 0, date('now'), 'actif')",
        (client_id,)
    )
    conn.commit()
    conn.close()
    flash(f'Banque de 5h ajoutée pour {client["nom"]}.', 'success')
    return redirect(f'/clients/{client_id}')

@admin_clients_bp.route('/clients/<int:client_id>/contrat/<int:contrat_id>/print')
@login_required
def contrat_print(client_id, contrat_id):
    conn = get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    contrat = conn.execute('SELECT * FROM contrats WHERE id = ? AND client_id = ?', (contrat_id, client_id)).fetchone()
    conn.close()
    if not client or not contrat:
        return redirect(f'/clients/{client_id}')
    milestones = safe_json_loads(contrat['milestones'], default=[])
    total = sum(float(m.get('prix', 0) or 0) for m in milestones)
    return render_template('contrat_print.html', client=client, contrat=contrat, milestones=milestones, total=total)

# ─── MILESTONES ───────────────────────────────────────────────────────────────

@admin_clients_bp.route('/clients/<int:client_id>/contrat/<int:contrat_id>/milestone/<int:index>/toggle', methods=['POST'])
@login_required
def toggle_milestone(client_id, contrat_id, index):
    # ... Logique intacte du toggle avec la gestion de la facturation et des courriels ...
    conn = get_db()
    contrat = conn.execute('SELECT * FROM contrats WHERE id = ? AND client_id = ?', (contrat_id, client_id)).fetchone()
    if not contrat or not contrat['milestones']: return redirect(f'/clients/{client_id}')
    milestones = safe_json_loads(contrat['milestones'], default=[])
    
    if 0 <= index < len(milestones):
        cycle = {'en attente': 'en cours', 'en cours': 'livré', 'livré': 'payé', 'approuvé': 'payé', 'payé': 'en attente'}
        actuel = milestones[index].get('statut', 'en attente')
        nouveau = cycle.get(actuel, 'en cours')

        if nouveau == 'en cours' and index > 0:
            prev = milestones[index - 1].get('statut', 'en attente')
            if prev != 'payé':
                msg = 'Le milestone précédent doit être payé avant de commencer celui-ci.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'error': msg}), 403
                flash(msg, 'error')
                return redirect(f'/clients/{client_id}')

        milestones[index]['statut'] = nouveau
        hist = milestones[index].get('historique', [])
        hist.append({'statut': nouveau, 'at': _now()[:10]})
        milestones[index]['historique'] = hist

        if nouveau == 'livré':
            m = milestones[index]
            montant = float(m.get('prix', 0) or 0)
            titre   = m.get('titre', f'Milestone {index + 1}')
            deja    = conn.execute('SELECT id FROM factures WHERE contrat_id = ? AND milestone_titre = ?', (contrat_id, titre)).fetchone()
            if not deja and montant > 0:
                count = conn.execute('SELECT COUNT(*) FROM factures').fetchone()[0]
                numero = f"{datetime.date.today().year}-{str(count + 1).zfill(3)}"
                conn.execute(
                    '''INSERT INTO factures (client_id, contrat_id, numero, milestone_titre, montant, date_emission) VALUES (?, ?, ?, ?, ?, ?)''',
                    (client_id, contrat_id, numero, titre, montant, datetime.date.today().isoformat())
                )
            client_notif = conn.execute('SELECT nom, email FROM clients WHERE id = ?', (client_id,)).fetchone()
            if client_notif and client_notif['email']:
                send_notification_email(
                    f'[TNTMom] Ton livrable est prêt — {titre}',
                    f'Bonjour {client_notif["nom"]},\n\nTon livrable "{titre}" est prêt. Connecte-toi pour le consulter.',
                    to=client_notif['email'],
                    html=email_milestone_livre(client_notif['nom'], titre)
                )

    conn.execute('UPDATE contrats SET milestones = ? WHERE id = ?', (json.dumps(milestones, ensure_ascii=False), contrat['id']))
    conn.commit()
    conn.close()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return jsonify({'statut': milestones[index]['statut']})
    flash('Statut du milestone mis à jour.', 'success')
    return redirect(f'/clients/{client_id}')

# ─── FICHIERS ─────────────────────────────────────────────────────────────────

@admin_clients_bp.route('/clients/<int:client_id>/fichiers/upload', methods=['POST'])
@login_required
def upload_fichier(client_id):
    fichier = request.files.get('fichier')
    if not fichier or fichier.filename == '':
        flash('Aucun fichier sélectionné.', 'error')
        return redirect(f'/clients/{client_id}')

    nom_original = fichier.filename
    nom_secure = secure_filename(nom_original)
    if not nom_secure:
        flash('Nom de fichier invalide.', 'error')
        return redirect(f'/clients/{client_id}')

    ext = os.path.splitext(nom_secure)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash(f'Type de fichier non autorisé ({ext or "sans extension"}).', 'error')
        return redirect(f'/clients/{client_id}')

    nom_stocke = f"{uuid.uuid4().hex}_{nom_secure}"
    dossier = os.path.join(UPLOAD_ROOT, str(client_id))
    os.makedirs(dossier, exist_ok=True)

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

@admin_clients_bp.route('/clients/<int:client_id>/fichiers/<int:fichier_id>/download')
@login_required
def telecharger_fichier_admin(client_id, fichier_id):
    conn = get_db()
    f = conn.execute('SELECT * FROM fichiers WHERE id = ? AND client_id = ?', (fichier_id, client_id)).fetchone()
    conn.close()
    if not f:
        return redirect(f'/clients/{client_id}')
    dossier = os.path.join(UPLOAD_ROOT, str(client_id))
    return send_from_directory(dossier, f['nom_fichier'], as_attachment=True, download_name=f['nom_original'])

@admin_clients_bp.route('/clients/<int:client_id>/fichiers/<int:fichier_id>/delete', methods=['POST'])
@login_required
def delete_fichier(client_id, fichier_id):
    conn = get_db()
    f = conn.execute('SELECT * FROM fichiers WHERE id = ? AND client_id = ?', (fichier_id, client_id)).fetchone()
    if f:
        chemin = os.path.join(UPLOAD_ROOT, str(client_id), f['nom_fichier'])
        if os.path.exists(chemin):
            os.remove(chemin)
        conn.execute('DELETE FROM fichiers WHERE id = ?', (fichier_id,))
        conn.commit()
    conn.close()
    flash('Fichier supprimé.', 'success')
    return redirect(f'/clients/{client_id}')

@admin_clients_bp.route('/clients/<int:client_id>/fichiers/<int:fichier_id>/commenter', methods=['POST'])
@login_required
def commenter_fichier_admin(client_id, fichier_id):
    commentaire = request.form.get('commentaire', '').strip()
    if commentaire:
        conn = get_db()
        f = conn.execute('SELECT * FROM fichiers WHERE id = ? AND client_id = ?', (fichier_id, client_id)).fetchone()
        if f:
            conn.execute(
                'INSERT INTO fichier_commentaires (fichier_id, auteur_type, auteur_nom, commentaire) VALUES (?, ?, ?, ?)',
                (fichier_id, 'admin', session.get('user_name', 'Admin'), commentaire)
            )
            conn.commit()
            client = conn.execute('SELECT nom, email FROM clients WHERE id = ?', (client_id,)).fetchone()
            if client and client['email']:
                send_notification_email(
                    f'[TNTMom] Nouveau commentaire sur le fichier {f["nom_original"]}',
                    f'Bonjour {client["nom"]},\n\nNaomie a ajouté un commentaire sur le fichier "{f["nom_original"]}" :\n\n"{commentaire}"\n\nConnecte-toi à ton portail pour répondre.',
                    to=client['email'],
                    html=email_commentaire_fichier_admin(client['nom'], f['nom_original'], commentaire)
                )
        conn.close()
        flash('Commentaire ajouté.', 'success')
    return redirect(f'/clients/{client_id}')

# ─── ACCÈS PORTAIL CLIENT ─────────────────────────────────────────────────────

@admin_clients_bp.route('/clients/<int:client_id>/set-password', methods=['POST'])
@login_required
def set_client_password(client_id):
    password = request.form.get('password', '').strip()
    if not password:
        return redirect(f'/clients/{client_id}')

    conn = get_db()
    conn.execute('UPDATE clients SET password = ? WHERE id = ?', (generate_password_hash(password), client_id))
    conn.commit()
    client_notif = conn.execute('SELECT nom, email FROM clients WHERE id = ?', (client_id,)).fetchone()
    conn.close()
    
    if client_notif and client_notif['email']:
        lien_portail = 'https://portail.tntm.ca/portail/login'
        send_notification_email(
            '[TNTMom] Ton accès au portail client est prêt ✨',
            f'Bonjour {client_notif["nom"]},\n\nTon portail est prêt. Connecte-toi ici : {lien_portail}',
            to=client_notif['email'],
            html=email_bienvenue(client_notif['nom'], lien_portail)
        )
    flash('Mot de passe mis à jour.', 'success')
    return redirect(f'/clients/{client_id}')

@admin_clients_bp.route('/clients/<int:client_id>/formulaires/assign', methods=['POST'])
@login_required
def client_formulaire_assign(client_id):
    fid = request.form.get('formulaire_id')
    if fid:
        conn = get_db()
        conn.execute('INSERT OR IGNORE INTO client_formulaires (client_id, formulaire_id) VALUES (?,?)', (client_id, int(fid)))
        conn.commit()
        conn.close()
    return redirect(f'/clients/{client_id}#formulaires')

@admin_clients_bp.route('/clients/<int:client_id>/formulaires/<int:fid>/remove', methods=['POST'])
@login_required
def client_formulaire_remove(client_id, fid):
    conn = get_db()
    conn.execute('DELETE FROM client_formulaires WHERE client_id = ? AND formulaire_id = ?', (client_id, fid))
    conn.commit()
    conn.close()
    return redirect(f'/clients/{client_id}#formulaires')

# ─── ACTIONS PORTAIL (ADMIN IMPERSONATE & MESSAGES) ───────────────────────────

@admin_clients_bp.route('/admin/switch-client/<int:client_id>', methods=['POST'])
@login_required
def admin_switch_client(client_id):
    conn = get_db()
    client = conn.execute('SELECT * FROM clients WHERE id=?', (client_id,)).fetchone()
    conn.close()
    if not client:
        flash('Client introuvable.', 'error')
        return redirect('/dashboard')
    session['client_id'] = client['id']
    session['client_nom'] = client['nom']
    session['admin_impersonating'] = True
    return redirect('/portail/dashboard')

@admin_clients_bp.route('/admin/exit-client')
def admin_exit_client():
    client_id = session.pop('client_id', None)
    session.pop('client_nom', None)
    session.pop('admin_impersonating', None)
    return redirect(f'/clients/{client_id}' if client_id else '/dashboard')

@admin_clients_bp.route('/clients/<int:client_id>/messages/thread/<int:first_msg_id>/delete', methods=['POST'])
@login_required
def delete_thread(client_id, first_msg_id):
    conn = get_db()
    row = conn.execute('SELECT sujet FROM messages_client WHERE id = ? AND client_id = ?', (first_msg_id, client_id)).fetchone()
    if row:
        sujet = row['sujet'] or ''
        conn.execute('DELETE FROM messages_client WHERE client_id = ? AND (sujet = ? OR (sujet IS NULL AND ? = ""))', (client_id, sujet, sujet))
        conn.commit()
    conn.close()
    flash('Conversation supprimée.', 'success')
    return redirect(f'/clients/{client_id}#messages')

@admin_clients_bp.route('/clients/<int:client_id>/messages/<int:message_id>/reponse/delete', methods=['POST'])
@login_required
def delete_reponse(client_id, message_id):
    conn = get_db()
    conn.execute('UPDATE messages_client SET reponse = NULL, repondu_at = NULL, lu_client = 1 WHERE id = ? AND client_id = ?', (message_id, client_id))
    conn.commit()
    conn.close()
    flash('Réponse supprimée.', 'success')
    return redirect(f'/clients/{client_id}#messages')

@admin_clients_bp.route('/clients/<int:client_id>/messages/<int:message_id>/repondre', methods=['POST'])
@login_required
def repondre_message(client_id, message_id):
    reponse = request.form.get('reponse', '').strip()
    if reponse:
        now = _now()
        conn = get_db()
        conn.execute('UPDATE messages_client SET reponse=?, repondu_at=?, lu_client=0 WHERE id=? AND client_id=?', (reponse, now, message_id, client_id))
        conn.commit()
        client_notif = conn.execute('SELECT nom, email FROM clients WHERE id = ?', (client_id,)).fetchone()
        msg_row = conn.execute('SELECT sujet FROM messages_client WHERE id = ?', (message_id,)).fetchone()
        conn.close()
        if client_notif and client_notif['email']:
            sujet = msg_row['sujet'] if msg_row and msg_row['sujet'] else 'ton message'
            send_notification_email(
                f'[TNTMom] Naomie t\'a répondu — {sujet}',
                f'Bonjour {client_notif["nom"]},\n\nNaomie vient de répondre à ton message « {sujet} ».',
                to=client_notif['email'],
                html=email_reponse_message(client_notif['nom'], sujet)
            )
        flash('Réponse envoyée.', 'success')
    return redirect(f'/clients/{client_id}')

@admin_clients_bp.route('/clients/<int:client_id>/messages/admin', methods=['POST'])
@login_required
def admin_message_nouveau(client_id):
    sujet = request.form.get('sujet', '').strip()
    message = request.form.get('message', '').strip()
    if not sujet or not message:
        flash('Sujet et message requis.', 'error')
        return redirect(f'/clients/{client_id}')

    conn = get_db()
    conn.execute('''INSERT INTO messages_client (client_id, sujet, message, reponse, repondu_at) VALUES (?, ?, ?, ?, datetime('now'))''', (client_id, sujet, '[Message initié par admin]', message))
    conn.commit()
    client = conn.execute('SELECT nom, email FROM clients WHERE id = ?', (client_id,)).fetchone()
    conn.close()

    if client and client['email']:
        send_notification_email(
            f'[TNTMom] Nouveau message de Naomie — {sujet}',
            f'Bonjour {client["nom"]},\n\nNaomie t\'a envoyé un message : « {sujet} ».',
            to=client['email'],
            html=email_message_naomie(client['nom'], sujet)
        )
    flash('Message envoyé au client.', 'success')
    return redirect(f'/clients/{client_id}')