import json
import os

from flask import (Blueprint, flash, redirect, render_template, request,
                   send_from_directory, session)
from werkzeug.security import check_password_hash

from database import get_db
from email_templates import (email_contrat_signe_naomie,
                             email_message_recu_naomie,
                             email_milestone_approuve_naomie,
                             email_formulaire_naomie,
                             email_commentaire_fichier_client)
from utils import (_compute_deadlines, _now, client_login_required,
                   group_messages, send_notification_email)

client_bp = Blueprint('client', __name__)

if os.getenv('RAILWAY_VOLUME_MOUNT_PATH'):
    UPLOAD_ROOT = os.path.join(os.getenv('RAILWAY_VOLUME_MOUNT_PATH'), 'uploads')
else:
    UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), 'uploads')

#--- login/logout ---#

@client_bp.route('/portail/login', methods=['GET', 'POST'])
def portail_login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        client = conn.execute(
            'SELECT * FROM clients WHERE email = ? AND deleted = 0', (email,)
        ).fetchone()
        conn.close()

        if client and client['password'] and check_password_hash(client['password'], password):
            session['client_id']   = client['id']
            session['client_nom'] = client['nom']

            # --- Tracker de connexion ---
            conn2 = get_db()
            conn2.execute('UPDATE clients SET last_login_at = ? WHERE id = ?', (_now(), client['id']))
            conn2.execute('INSERT INTO client_activity (client_id, action, details) VALUES (?, ?, ?)',
                          (client['id'], 'Connexion', 'Connexion au portail client'))
            conn2.commit()
            conn2.close()

            return redirect('/portail/dashboard')

        error = 'Courriel ou mot de passe incorrect.'

    return render_template('portail_login.html', error=error)


@client_bp.route('/portail/logout')
def portail_logout():
    if session.get('admin_impersonating'):
        return redirect('/admin/exit-client')
    session.pop('client_id', None)
    session.pop('client_nom', None)
    return redirect('/portail/login')


@client_bp.route('/portail/dashboard')
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

    fichiers_raw = conn.execute(
        'SELECT * FROM fichiers WHERE client_id = ? AND milestone_index IS NULL ORDER BY uploaded_at DESC',
        (session['client_id'],)
    ).fetchall()

    livrables_raw = conn.execute(
        'SELECT * FROM fichiers WHERE client_id = ? AND milestone_index IS NOT NULL ORDER BY uploaded_at DESC',
        (session['client_id'],)
    ).fetchall()

    comments_raw = conn.execute(
        '''SELECT fc.* FROM fichier_commentaires fc
           JOIN fichiers f ON f.id = fc.fichier_id
           WHERE f.client_id = ? ORDER BY fc.created_at ASC''',
        (session['client_id'],)
    ).fetchall()

    comments_by_file = {}
    for c in comments_raw:
        comments_by_file.setdefault(c['fichier_id'], []).append(dict(c))

    fichiers = [dict(f, commentaires=comments_by_file.get(f['id'], [])) for f in fichiers_raw]
    livrables = [dict(f, commentaires=comments_by_file.get(f['id'], [])) for f in livrables_raw]

    formulaire_pending = conn.execute('''
        SELECT f.id, f.titre FROM formulaires f
        JOIN client_formulaires cf ON f.id = cf.formulaire_id
        WHERE cf.client_id = ? AND f.actif = 1
          AND f.id NOT IN (
              SELECT formulaire_id FROM formulaire_reponses WHERE client_id = ?
          )
        ORDER BY cf.assigned_at ASC LIMIT 1
    ''', (session['client_id'], session['client_id'])).fetchone()

    facture_pending = conn.execute(
        "SELECT * FROM factures WHERE client_id = ? AND statut != 'payée' ORDER BY date_emission ASC LIMIT 1",
        (session['client_id'],)
    ).fetchone()

    conn.close()

    projets = []
    for c in contrats_all:
        m = _compute_deadlines(json.loads(c['milestones']) if c['milestones'] else [])
        total = sum(float(x.get('prix', 0) or 0) for x in m)
        faits = sum(1 for x in m if x.get('statut') in ['livré', 'approuvé', 'payé'])
        projets.append({
            'contrat': dict(c),
            'milestones': m,
            'total': total,
            'faits': faits,
        })

    next_action = None

    for p in projets:
        if p['contrat']['statut'] == 'envoyé':
            next_action = {
                'type': 'contrat',
                'icon': '✍',
                'label': f'Ton contrat pour « {p["contrat"]["nom"] or "ton projet"} » est prêt à signer.',
                'cta': 'Signer maintenant',
                'url': '#dashboard-projets',
            }
            break

    if not next_action and formulaire_pending:
        next_action = {
            'type': 'formulaire',
            'icon': '📋',
            'label': f'Naomie attend que tu remplisses : « {formulaire_pending["titre"]} ».',
            'cta': 'Remplir maintenant',
            'url': f'/portail/formulaires/{formulaire_pending["id"]}',
        }

    if not next_action:
        for p in projets:
            for i, m in enumerate(p['milestones']):
                if m.get('statut') == 'livré':
                    next_action = {
                        'type': 'approuver',
                        'icon': '✅',
                        'label': f'« {m["titre"]} » est livré — approuve-le pour confirmer la réception.',
                        'cta': 'Approuver',
                        'url': f'/portail/contrat/{p["contrat"]["id"]}/milestone/{i}/approuver',
                    }
                    break
            if next_action:
                break

    if not next_action and facture_pending:
        try:
            montant_str = f'{int(float(facture_pending["montant"]))}$'
        except Exception:
            montant_str = ''
        next_action = {
            'type': 'facture',
            'icon': '💳',
            'label': f'Une facture est en attente de paiement{" — " + montant_str if montant_str else ""}.',
            'cta': 'Voir mes factures',
            'url': '/portail/factures',
        }

    if not next_action:
        for p in projets:
            for m in p['milestones']:
                if m.get('statut') == 'en cours':
                    next_action = {
                        'type': 'en_cours',
                        'icon': '⚙',
                        'label': f'En cours de développement : « {m["titre"]} ».',
                        'cta': None,
                        'url': None,
                    }
                    break
            if next_action:
                break

    return render_template('portail_dashboard.html',
                            client=client,
                            projets=projets,
                            fichiers=fichiers,
                            livrables=livrables,
                            next_action=next_action)


def projet_est_clos(client_id, conn):
    # On vérifie le dernier contrat du client — le dernier milestone payé = projet clos
    contrat = conn.execute(
        'SELECT milestones FROM contrats WHERE client_id = ? ORDER BY created_at DESC LIMIT 1',
        (client_id,)
    ).fetchone()
    if not contrat or not contrat['milestones']:
        return False
    milestones = json.loads(contrat['milestones'])
    return bool(milestones) and milestones[-1].get('statut') == 'payé'


def get_banque_active(client_id, conn):
    # Retourne la banque active avec minutes restantes, ou None
    return conn.execute(
        """SELECT * FROM banque_heures
           WHERE client_id = ? AND statut = 'actif'
           AND (minutes_total - minutes_utilisees) > 0
           ORDER BY date_achat DESC LIMIT 1""",
        (client_id,)
    ).fetchone()


@client_bp.route('/portail/contact', methods=['GET', 'POST'])
@client_login_required
def portail_contact():
    conn = get_db()
    client = conn.execute(
        'SELECT * FROM clients WHERE id = ?', (session['client_id'],)
    ).fetchone()

    if request.method == 'POST':
        sujet   = request.form.get('sujet', '').strip()
        message = request.form.get('message', '').strip()

        if not message:
            conn.close()
            flash('Le message ne peut pas être vide.', 'error')
            return redirect('/portail/contact')

        # Si projet terminé, vérifier que le client a une banque d'heures active
        if projet_est_clos(session['client_id'], conn):
            banque = get_banque_active(session['client_id'], conn)
            if not banque:
                conn.close()
                flash('Ton projet est terminé 🎉 Pour toute nouvelle demande, tu dois acheter un bloc de maintenance. Contacte Naomie !', 'info')
                return redirect('/portail/contact')

        conn.execute(
            'INSERT INTO messages_client (client_id, sujet, message) VALUES (?,?,?)',
            (session['client_id'], sujet, message)
        )
        conn.commit()
        conn.close()
        send_notification_email(
            f'[ClientPortal] Nouveau message de {session["client_nom"]}',
            f'Client : {session["client_nom"]}\nSujet : {sujet or "(aucun)"}\n\n{message}',
            html=email_message_recu_naomie(session['client_nom'], sujet, message)
        )
        flash('Message envoyé. Naomie te reviendra sous peu !', 'success')
        return redirect('/portail/contact')

    conn.execute(
        "UPDATE messages_client SET lu_client=1 WHERE client_id=? AND lu_client=0",
        (session['client_id'],)
    )

    conn.commit()
    historique = conn.execute(
        'SELECT * FROM messages_client WHERE client_id = ? ORDER BY created_at ASC',
        (session['client_id'],)
    ).fetchall()
    conn.close()
    return render_template('portail_contact.html', client=client,
                           threads=group_messages(historique))


@client_bp.route('/portail/fichiers/<int:fichier_id>')
@client_login_required
def telecharger_fichier_client(fichier_id):
    conn = get_db()
    # On vérifie que le fichier appartient bien AU client connecté — un client
    # ne peut pas deviner l'id d'un fichier d'un autre client et le télécharger
    f = conn.execute(
        'SELECT * FROM fichiers WHERE id = ? AND client_id = ?',
        (fichier_id, session['client_id'])
    ).fetchone()

    if not f:
        conn.close()
        return redirect('/portail/dashboard')

    # --- Tracker de téléchargement ---
    conn.execute('INSERT INTO client_activity (client_id, action, details) VALUES (?, ?, ?)',
                 (session['client_id'], 'Téléchargement', f"Fichier : {f['nom_original']}"))
    conn.commit()
    conn.close()

    dossier = os.path.join(UPLOAD_ROOT, str(session['client_id']))
    return send_from_directory(dossier, f['nom_fichier'],
                               as_attachment=True, download_name=f['nom_original'])


@client_bp.route('/portail/fichiers/<int:fichier_id>/commenter', methods=['POST'])
@client_login_required
def commenter_fichier_client(fichier_id):
    commentaire = request.form.get('commentaire', '').strip()
    if commentaire:
        conn = get_db()
        f = conn.execute('SELECT * FROM fichiers WHERE id = ? AND client_id = ?', (fichier_id, session['client_id'])).fetchone()
        if f:
            conn.execute(
                'INSERT INTO fichier_commentaires (fichier_id, auteur_type, auteur_nom, commentaire) VALUES (?, ?, ?, ?)',
                (fichier_id, 'client', session.get('client_nom', 'Client'), commentaire)
            )
            conn.execute('INSERT INTO client_activity (client_id, action, details) VALUES (?, ?, ?)',
                         (session['client_id'], 'Commentaire', f'Sur le fichier : {f["nom_original"]}'))
            conn.commit()
            send_notification_email(
                f'[ClientPortal] Nouveau commentaire de {session.get("client_nom")}',
                f'Client : {session.get("client_nom")}\nFichier : {f["nom_original"]}\n\n"{commentaire}"',
                html=email_commentaire_fichier_client(session.get("client_nom"), f["nom_original"], commentaire)
            )
        conn.close()
        flash('Commentaire ajouté.', 'success')
    return redirect('/portail/dashboard')

@client_bp.route('/portail/contrat/<int:contrat_id>/print')
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
    total = sum(float(m.get('prix', 0) or 0) for m in milestones)
    return render_template('contrat_print.html', client=client, contrat=contrat,
                           milestones=milestones, total=total)


@client_bp.route('/portail/contrat/<int:contrat_id>/signer', methods=['POST'])
@client_login_required
def portail_signer(contrat_id):
    conn = get_db()
    contrat = conn.execute(
        'SELECT * FROM contrats WHERE id = ? AND client_id = ?',
        (contrat_id, session['client_id'])
    ).fetchone()

    if contrat and contrat['statut'] == 'envoyé':
        now = _now()
        conn.execute(
            "UPDATE contrats SET statut='signé', signed_at=? WHERE id=?",
            (now, contrat_id)
        )
        conn.commit()
        client_notif = conn.execute('SELECT nom FROM clients WHERE id = ?', (session['client_id'],)).fetchone()
        nom_projet = contrat['nom'] or 'Projet sans titre'
        send_notification_email(
            f'[ClientPortal] ✍ Contrat signé — {nom_projet}',
            f'{client_notif["nom"] if client_notif else "Ton client"} vient de signer le contrat « {nom_projet} ».',
            html=email_contrat_signe_naomie(client_notif['nom'] if client_notif else 'Client', nom_projet)
        )
        flash('Contrat signé. Merci !', 'success')
    conn.close()
    return redirect('/portail/dashboard')


@client_bp.route('/portail/contrat/<int:contrat_id>/milestone/<int:index>/approuver', methods=['POST'])
@client_login_required
def portail_approuver_milestone(contrat_id, index):
    conn = get_db()
    contrat = conn.execute(
        'SELECT * FROM contrats WHERE id = ? AND client_id = ?',
        (contrat_id, session['client_id'])
    ).fetchone()

    if contrat and contrat['milestones']:
        milestones = json.loads(contrat['milestones'])
        if 0 <= index < len(milestones) and milestones[index].get('statut') == 'livré':
            milestones[index]['statut'] = 'approuvé'
            milestones[index]['approuve_at'] = _now()
            hist = milestones[index].get('historique', [])
            hist.append({'statut': 'approuvé', 'at': _now()[:10]})
            milestones[index]['historique'] = hist
            conn.execute(
                'UPDATE contrats SET milestones = ? WHERE id = ?',
                (json.dumps(milestones, ensure_ascii=False), contrat_id)
            )
            conn.commit()
            titre = milestones[index]['titre']
            client_notif = conn.execute('SELECT nom FROM clients WHERE id = ?', (session['client_id'],)).fetchone()
            send_notification_email(
                f'[ClientPortal] ✅ Milestone approuvé — {titre}',
                f'{client_notif["nom"] if client_notif else "Ton client"} vient d\'approuver : « {titre} ».',
                html=email_milestone_approuve_naomie(client_notif['nom'] if client_notif else 'Client', titre)
            )
            flash(f'✅ « {titre} » approuvé. Merci !', 'success')

    conn.close()
    return redirect('/portail/dashboard')


# ─── FACTURES PORTAIL CLIENT ──────────────────────────────────────────────────

@client_bp.route('/portail/factures')
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


@client_bp.route('/portail/factures/<int:facture_id>/print')
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


# ── FORMULAIRES PORTAIL CLIENT ────────────────────────────────────────────────

@client_bp.route('/portail/formulaires')
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


@client_bp.route('/portail/formulaires/<int:fid>')
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

    # Build prefill dict from existing client data
    prefill = {
        'client.nom':        client['nom'] or '',
        'client.email':      client['email'] or '',
        'client.entreprise': client['entreprise'] or '',
        'client.secteur':    client['secteur'] or '',
    }
    q_row = conn.execute(
        'SELECT reponses FROM questionnaires_client WHERE client_id = ?', (session['client_id'],)
    ).fetchone()
    if q_row and q_row['reponses']:
        try:
            for k, v in json.loads(q_row['reponses']).items():
                prefill[f'questionnaire.{k}'] = v or ''
        except Exception:
            pass
    c_row = conn.execute(
        'SELECT reponses FROM consultations WHERE client_id = ? ORDER BY created_at DESC LIMIT 1',
        (session['client_id'],)
    ).fetchone()
    if c_row and c_row['reponses']:
        try:
            for k, v in json.loads(c_row['reponses']).items():
                prefill[f'consultation.{k}'] = v or ''
        except Exception:
            pass

    conn.close()
    if deja:
        flash('Tu as déjà rempli ce formulaire.', 'success')
        return redirect('/portail/formulaires')
    return render_template('portail_formulaire_fill.html',
                           client=client, formulaire=f, questions=questions, prefill=prefill)


@client_bp.route('/portail/formulaires/<int:fid>/submit', methods=['POST'])
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
                f'{client["nom"]} a rempli le formulaire : {formulaire["titre"]}',
                html=email_formulaire_naomie(client['nom'], formulaire['titre'])
            )
    conn.close()
    flash('Formulaire envoyé, merci !', 'success')
    return redirect('/portail/formulaires')


# ─── QUESTIONNAIRE CLIENT (accès public, pas de login) ───────────────────────

@client_bp.route('/q/<token>', methods=['GET', 'POST'])
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
