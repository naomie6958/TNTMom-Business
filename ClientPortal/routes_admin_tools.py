import json
import datetime
from flask import Blueprint, render_template, request, redirect, flash
from database import get_db
from utils import login_required
from analytics_config import ANALYTICS_SITES
from cloudflare_analytics import get_site_stats
from client_form_config import CLIENT_SITES

admin_tools_bp = Blueprint('admin_tools', __name__)

# ── SOUMISSIONS (formulaires des sites clients statiques, via /api/public/form-submit) ──

@admin_tools_bp.route('/soumissions')
@login_required
def soumissions_list():
    conn = get_db()
    rows = conn.execute('SELECT * FROM client_form_submissions ORDER BY created_at DESC').fetchall()
    conn.execute('UPDATE client_form_submissions SET lu = 1 WHERE lu = 0')
    conn.commit()
    conn.close()

    soumissions = []
    for row in rows:
        soumissions.append({
            'id': row['id'],
            'client_nom': CLIENT_SITES.get(row['client_site'], {}).get('nom', row['client_site']),
            'champs': json.loads(row['data']),
            'lu': row['lu'],
            'created_at': row['created_at'],
            'notif_owner_statut': row['notif_owner_statut'],
            'confirmation_client_statut': row['confirmation_client_statut'],
        })

    return render_template('soumissions.html', soumissions=soumissions)

@admin_tools_bp.route('/soumissions/<int:sid>/delete', methods=['POST'])
@login_required
def soumission_delete(sid):
    conn = get_db()
    conn.execute('DELETE FROM client_form_submissions WHERE id = ?', (sid,))
    conn.commit()
    conn.close()
    return redirect('/soumissions')

# ── LEADS (formulaire de contact public tntm.ca) ──────────────────────────────

@admin_tools_bp.route('/leads')
@login_required
def leads_list():
    conn = get_db()
    leads = conn.execute('SELECT * FROM leads ORDER BY created_at DESC').fetchall()
    conn.execute('UPDATE leads SET lu = 1 WHERE lu = 0')
    conn.commit()
    conn.close()
    return render_template('leads.html', leads=leads)

@admin_tools_bp.route('/leads/<int:lead_id>/delete', methods=['POST'])
@login_required
def lead_delete(lead_id):
    conn = get_db()
    conn.execute('DELETE FROM leads WHERE id = ?', (lead_id,))
    conn.commit()
    conn.close()
    return redirect('/leads')

# ── FORMULAIRES CUSTOM ────────────────────────────────────────────────────────

@admin_tools_bp.route('/formulaires')
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

@admin_tools_bp.route('/formulaires/new', methods=['POST'])
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

@admin_tools_bp.route('/formulaires/<int:fid>')
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

@admin_tools_bp.route('/formulaires/<int:fid>/edit', methods=['POST'])
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

@admin_tools_bp.route('/formulaires/<int:fid>/delete', methods=['POST'])
@login_required
def formulaire_delete(fid):
    conn = get_db()
    conn.execute('DELETE FROM formulaires WHERE id = ?', (fid,))
    conn.commit()
    conn.close()
    flash('Formulaire supprimé.', 'success')
    return redirect('/formulaires')

@admin_tools_bp.route('/formulaires/<int:fid>/questions/add', methods=['POST'])
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

@admin_tools_bp.route('/formulaires/<int:fid>/questions/<int:qid>/edit', methods=['POST'])
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

@admin_tools_bp.route('/formulaires/<int:fid>/questions/<int:qid>/delete', methods=['POST'])
@login_required
def formulaire_question_delete(fid, qid):
    conn = get_db()
    conn.execute('DELETE FROM formulaire_questions WHERE id = ? AND formulaire_id = ?', (qid, fid))
    conn.commit()
    conn.close()
    return redirect(f'/formulaires/{fid}')

@admin_tools_bp.route('/formulaires/<int:fid>/questions/reorder', methods=['POST'])
@login_required
def formulaire_questions_reorder(fid):
    data  = request.get_json(silent=True) or {}
    ordre = data.get('ordre', [])
    conn  = get_db()
    for i, qid in enumerate(ordre):
        conn.execute('UPDATE formulaire_questions SET ordre = ? WHERE id = ? AND formulaire_id = ?', (i, qid, fid))
    conn.commit()
    conn.close()
    return {'ok': True}

# ── TARIFS ────────────────────────────────────────────────────────────────────

@admin_tools_bp.route('/tarifs')
@login_required
def tarifs():
    conn = get_db()
    rows = conn.execute('SELECT * FROM tarifs ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('tarifs_admin.html', tarifs=rows)

@admin_tools_bp.route('/tarifs/new', methods=['POST'])
@login_required
def tarif_new():
    conn = get_db()
    max_ordre = conn.execute('SELECT COALESCE(MAX(ordre), -1) FROM tarifs').fetchone()[0]
    conn.execute(
        'INSERT INTO tarifs (titre, description, prix, unite, inclus, non_inclus, actif, ordre) VALUES (?,?,?,?,?,?,?,?)',
        (
            request.form.get('titre', '').strip(), request.form.get('description', '').strip() or None,
            float(request.form.get('prix') or 0) or None, request.form.get('unite', '/ projet').strip(),
            request.form.get('inclus', '').strip() or None, request.form.get('non_inclus', '').strip() or None,
            1 if request.form.get('actif') else 0, max_ordre + 1,
        )
    )
    conn.commit()
    conn.close()
    flash('Tarif ajouté.', 'success')
    return redirect('/tarifs')

@admin_tools_bp.route('/tarifs/<int:tid>/edit', methods=['POST'])
@login_required
def tarif_edit(tid):
    conn = get_db()
    conn.execute(
        'UPDATE tarifs SET titre=?, description=?, prix=?, unite=?, inclus=?, non_inclus=?, actif=?, ordre=? WHERE id=?',
        (
            request.form.get('titre', '').strip(), request.form.get('description', '').strip() or None,
            float(request.form.get('prix') or 0) or None, request.form.get('unite', '/ projet').strip(),
            request.form.get('inclus', '').strip() or None, request.form.get('non_inclus', '').strip() or None,
            1 if request.form.get('actif') else 0, int(request.form.get('ordre', 0)), tid,
        )
    )
    conn.commit()
    conn.close()
    flash('Tarif mis à jour.', 'success')
    return redirect('/tarifs')

@admin_tools_bp.route('/tarifs/<int:tid>/delete', methods=['POST'])
@login_required
def tarif_delete(tid):
    conn = get_db()
    conn.execute('DELETE FROM tarifs WHERE id = ?', (tid,))
    conn.commit()
    conn.close()
    flash('Tarif supprimé.', 'success')
    return redirect('/tarifs')

# ── PACKAGES ──────────────────────────────────────────────────────────────────

@admin_tools_bp.route('/packages', methods=['GET', 'POST'])
@login_required
def packages():
    conn = get_db()
    clients = conn.execute("SELECT id, nom FROM clients WHERE demo = 0 AND deleted = 0 ORDER BY nom").fetchall()

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
            if montant <= 0: return 0
            centaine = int(montant // 100) * 100
            for candidat in (centaine + 50, centaine + 99, centaine + 150):
                if candidat >= montant: return candidat
            return centaine + 199

        prix_final = _arrondir(avec_marge)

        conn.execute('''
            INSERT INTO packages (nom, client_id, heures_dev, heures_design, heures_integration, heures_admin, marge, prix_final)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nom, client_id, h_dev, h_design, h_integration, h_admin, marge, prix_final))
        conn.commit()
        flash(f'Forfait "{nom}" enregistré — {prix_final:.0f}$', 'success')
        conn.close()
        return redirect('/packages')

    packages_list = conn.execute('''
        SELECT p.*, c.nom as client_nom
        FROM packages p JOIN clients c ON p.client_id = c.id
        ORDER BY p.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('packages.html', clients=clients, packages=packages_list)

@admin_tools_bp.route('/packages/<int:pkg_id>/delete', methods=['POST'])
@login_required
def package_delete(pkg_id):
    conn = get_db()
    conn.execute('DELETE FROM packages WHERE id = ?', (pkg_id,))
    conn.commit()
    conn.close()
    flash('Forfait supprimé.', 'success')
    return redirect('/packages')

@admin_tools_bp.route('/packages/<int:pkg_id>/creer-contrat', methods=['POST'])
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

    milestones = [
        {'titre': 'M1 — Démarrage & Contrat',  'livrable': 'Acompte initial — lancement du projet',      'prix': str(round(prix * 0.25)), 'date': '', 'statut': 'en attente', 'lien_preview': '', 'preview_visible': False},
        {'titre': 'M2 — Design & Maquettes',    'livrable': 'Maquettes approuvées par le client',         'prix': str(round(prix * 0.25)), 'date': '', 'statut': 'en attente', 'lien_preview': '', 'preview_visible': False},
        {'titre': 'M3 — Développement',         'livrable': 'Site fonctionnel livré en prévisualisation', 'prix': str(round(prix * 0.35)), 'date': '', 'statut': 'en attente', 'lien_preview': '', 'preview_visible': False},
        {'titre': 'M4 — Livraison finale',      'livrable': 'Mise en ligne + passation de dossier',       'prix': str(round(prix * 0.15)), 'date': '', 'statut': 'en attente', 'lien_preview': '', 'preview_visible': False},
    ]

    snapshot = {
        'nom': pkg['nom'], 'heures_dev': pkg['heures_dev'], 'heures_design': pkg['heures_design'],
        'heures_integration': pkg['heures_integration'], 'heures_admin': pkg['heures_admin'],
        'marge': pkg['marge'], 'prix_final': pkg['prix_final'],
    }

    titre_scope = "Migration / Copie Conforme" if pkg['heures_design'] == 0 else "Développement web complet"
    scope_auto  = f"{titre_scope} — {pkg['nom']}\n\n• Développement : {pkg['heures_dev']}h\n"
    if pkg['heures_design'] > 0:
        scope_auto += f"• Design UI/UX : {pkg['heures_design']}h\n"
    scope_auto += f"• Intégration & Maintenance : {pkg['heures_integration']}h\n"
    scope_auto += f"• Admin & Gestion : {pkg['heures_admin']}h"

    cursor = conn.execute(
        'INSERT INTO contrats (client_id, nom, scope, milestones, statut, package_snapshot) VALUES (?,?,?,?,?,?)',
        (pkg['client_id'], pkg['nom'], scope_auto, json.dumps(milestones, ensure_ascii=False), 'draft', json.dumps(snapshot, ensure_ascii=False))
    )
    contrat_id = cursor.lastrowid
    conn.commit()
    conn.close()

    flash(f'Contrat créé depuis le forfait « {pkg["nom"]} ». Révise et envoie au client !', 'success')
    return redirect(f'/clients/{pkg["client_id"]}/contrat/{contrat_id}')

@admin_tools_bp.route('/portfolio')
@login_required
def portfolio_list():
    conn = get_db()
    projets = conn.execute('SELECT * FROM portfolio_projets ORDER BY ordre, id').fetchall()
    conn.close()
    return render_template('admin/portfolio.html', projets=projets)

@admin_tools_bp.route('/portfolio/<int:pid>/toggle', methods=['POST'])
@login_required
def portfolio_toggle(pid):
    conn = get_db()
    conn.execute('UPDATE portfolio_projets SET actif = CASE WHEN actif = 1 THEN 0 ELSE 1 END WHERE id = ?', (pid,))
    conn.commit()
    conn.close()
    return redirect('/portfolio')

@admin_tools_bp.route('/portfolio/new', methods=['GET', 'POST'])
@login_required
def portfolio_new():
    if request.method == 'POST':
        conn = get_db()
        conn.execute('''
            INSERT INTO portfolio_projets (nom, tagline, description, tags, statut, couleur, image_url, link, ordre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form.get('nom', '').strip(),
            request.form.get('tagline', '').strip(),
            request.form.get('description', '').strip(),
            request.form.get('tags', '').strip(),
            request.form.get('statut', '').strip(),
            request.form.get('couleur', '').strip(),
            request.form.get('image_url', '').strip(),
            request.form.get('link', '').strip(),
            int(request.form.get('ordre') or 99),
        ))
        conn.commit()
        conn.close()
        flash('Projet ajouté au portfolio ✅', 'success')
        return redirect('/portfolio')

    return render_template('admin/portfolio_form.html', projet=None, action='/portfolio/new')

@admin_tools_bp.route('/portfolio/<int:pid>/edit', methods=['GET', 'POST'])
@login_required
def portfolio_edit(pid):
    conn = get_db()
    if request.method == 'POST':
        conn.execute('''
            UPDATE portfolio_projets
            SET nom=?, tagline=?, description=?, tags=?, statut=?, couleur=?, image_url=?, link=?, ordre=?
            WHERE id=?
        ''', (
            request.form.get('nom', '').strip(),
            request.form.get('tagline', '').strip(),
            request.form.get('description', '').strip(),
            request.form.get('tags', '').strip(),
            request.form.get('statut', 'live'),
            request.form.get('couleur', 'magenta'),
            request.form.get('image_url', '').strip(),
            request.form.get('link', '').strip(),
            int(request.form.get('ordre') or 99),
            pid,
        ))
        conn.commit()
        conn.close()
        flash('Projet mis à jour✅', 'success')
        return redirect('/portfolio')

    projet = conn.execute('SELECT * FROM portfolio_projets WHERE id = ?', (pid,)).fetchone()
    conn.close()
    return render_template('admin/portfolio_form.html', projet=projet, action=f'/portfolio/{pid}/edit')

@admin_tools_bp.route('/portfolio/reorder', methods=['POST'])
@login_required
def portfolio_reorder():
    data  = request.get_json(silent=True) or {}
    ordre = data.get('ordre', [])
    conn  = get_db()
    for i, pid in enumerate(ordre):
        conn.execute('UPDATE portfolio_projets SET ordre = ? WHERE id = ?', (i, pid))
    conn.commit()
    conn.close()
    return '', 204

@admin_tools_bp.route('/portfolio/<int:pid>/delete', methods=['POST'])
@login_required
def portfolio_delete(pid):
    conn = get_db()
    conn.execute('DELETE FROM portfolio_projets WHERE id = ?', (pid,))
    conn.commit()
    conn.close()
    flash('Projet supprimé ✅', 'success')
    return redirect('/portfolio')

# ── ANALYTICS (stats de visites via Cloudflare Web Analytics) ────────────────

@admin_tools_bp.route('/analytics')
@login_required
def analytics_dashboard():
    sites = []
    for slug, cfg in ANALYTICS_SITES.items():
        entry = {'slug': slug, 'nom': cfg['nom'], 'domain': cfg['domain'], 'error': None, 'stats': None}
        if not cfg.get('site_tag'):
            entry['error'] = 'Script Cloudflare pas encore installé sur ce site'
        else:
            try:
                entry['stats'] = get_site_stats(cfg['site_tag'], days=30)
            except Exception as e:
                entry['error'] = str(e)
        sites.append(entry)

    return render_template('admin/analytics.html', sites=sites)