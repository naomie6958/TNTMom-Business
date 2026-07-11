import datetime
from collections import OrderedDict
import json
import io
import csv
import os
import uuid
from zoneinfo import ZoneInfo
from flask import Blueprint, render_template, request, redirect, session, flash, jsonify, url_for, Response, send_from_directory
from werkzeug.utils import secure_filename
from database import get_db
from utils import login_required, safe_json_loads
from compta_logic import verifier_et_mettre_retards, calculer_tax_tracker, calculer_provision_fiscale

admin_compta_bp = Blueprint('admin_compta', __name__)

_EASTERN = ZoneInfo('America/Montreal')

if os.getenv('RAILWAY_VOLUME_MOUNT_PATH'):
    UPLOAD_ROOT = os.path.join(os.getenv('RAILWAY_VOLUME_MOUNT_PATH'), 'uploads')
else:
    UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), 'uploads')

ALLOWED_EXTENSIONS = {
    '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg',
    '.zip', '.doc', '.docx', '.xls', '.xlsx', '.mp4', '.mov', '.txt', '.fig',
}

# ── COMPTABILITÉ & DÉPENSES ───────────────────────────────────────────────────

@admin_compta_bp.route('/comptabilite')
@login_required
def comptabilite():
    inclure_demo = request.args.get('demo', '0') == '1'
    alertes_retard = verifier_et_mettre_retards(inclure_demo=inclure_demo)

    conn = get_db()
    filtre_demo_sql = '' if inclure_demo else 'AND c.demo = 0'
    factures = conn.execute(f'''
        SELECT f.*, c.nom as client_nom
        FROM factures f
        JOIN clients c ON c.id = f.client_id
        WHERE 1=1 {filtre_demo_sql}
        ORDER BY f.date_emission DESC
    ''').fetchall()
    conn.close()

    mois = OrderedDict()
    total_realise = 0
    total_attente = 0

    for f in factures:
        key = (f['date_emission'] or '')[:7] or 'Sans date'
        if key not in mois:
            mois[key] = {'factures': [], 'total_payee': 0, 'total_attente': 0}
        mois[key]['factures'].append(dict(f))
        montant = float(f['montant'] or 0)
        if f['statut'] == 'payée':
            mois[key]['total_payee'] += montant
            total_realise += montant
        else:
            mois[key]['total_attente'] += montant
            total_attente += montant

    tracker  = calculer_tax_tracker(inclure_demo=inclure_demo)
    provision = calculer_provision_fiscale(inclure_demo=inclure_demo)

    conn = get_db()
    depenses = conn.execute('SELECT * FROM depenses ORDER BY date DESC').fetchall()
    conn.close()

    return render_template('comptabilite.html',
                           mois=mois, total_realise=total_realise, total_attente=total_attente,
                           alertes_retard=alertes_retard, tracker=tracker, provision=provision,
                           depenses=depenses, today=datetime.date.today().isoformat(),
                           inclure_demo=inclure_demo)

@admin_compta_bp.route('/admin/fiscal-summary')
@login_required
def fiscal_summary():
    conn = get_db()
    factures_2026 = conn.execute("""
        SELECT SUM(f.montant) as brut FROM factures f
        JOIN clients c ON c.id = f.client_id
        WHERE f.statut = 'payée' AND strftime('%Y', f.date_emission) = '2026'
        AND c.demo = 0
    """).fetchone()
    business_brut = float(factures_2026['brut'] or 0)
    provision_fiscale = business_brut * 0.25
    business_net = business_brut * 0.75

    revenus_menage = conn.execute('''
        SELECT SUM(CASE WHEN is_taxable = 1 THEN amount ELSE 0 END) as imposables,
               SUM(CASE WHEN is_taxable = 0 THEN amount ELSE 0 END) as non_imposables,
               SUM(amount) as total
        FROM household_revenues WHERE strftime('%Y', date_received) = '2026'
    ''').fetchone()

    revenus_imposables = float(revenus_menage['imposables'] or 0)
    revenus_non_imposables = float(revenus_menage['non_imposables'] or 0)
    revenus_list = conn.execute('SELECT * FROM household_revenues WHERE strftime("%Y", date_received) = "2026" ORDER BY date_received DESC').fetchall()
    revenu_global = business_net + revenus_imposables + revenus_non_imposables
    conn.close()

    return render_template('admin/fiscal.html', business_brut=business_brut, provision_fiscale=provision_fiscale,
                           business_net=business_net, revenus_imposables=revenus_imposables,
                           revenus_non_imposables=revenus_non_imposables, revenu_global=revenu_global, revenus_list=revenus_list)

@admin_compta_bp.route('/depenses/new', methods=['POST'])
@login_required
def depense_new():
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def erreur(msg):
        if is_ajax:
            return jsonify({'success': False, 'error': msg})
        flash(msg, 'error')
        return redirect('/comptabilite')

    date_dep, description, montant_str = request.form.get('date', '').strip(), request.form.get('description', '').strip(), request.form.get('montant', '0').strip()
    if not date_dep or not description or not montant_str:
        return erreur('Tous les champs sont requis.')
    try: montant = float(montant_str)
    except ValueError:
        return erreur('Montant invalide.')

    # Fichier joint optionnel (facture, reçu...)
    fichier_nom_original = fichier_nom_stocke = None
    fichier_taille = None
    fichier = request.files.get('fichier')
    if fichier and fichier.filename:
        nom_secure = secure_filename(fichier.filename)
        ext = os.path.splitext(nom_secure)[1].lower()
        if not nom_secure or ext not in ALLOWED_EXTENSIONS:
            return erreur(f'Type de fichier non autorisé ({ext or "sans extension"}).')
        fichier_nom_original = fichier.filename
        fichier_nom_stocke = f"{uuid.uuid4().hex}_{nom_secure}"
        dossier = os.path.join(UPLOAD_ROOT, 'depenses')
        os.makedirs(dossier, exist_ok=True)
        chemin = os.path.join(dossier, fichier_nom_stocke)
        fichier.save(chemin)
        fichier_taille = os.path.getsize(chemin)

    conn = get_db()
    conn.execute(
        '''INSERT INTO depenses (date, description, montant, categorie, fichier_nom_original, fichier_nom_stocke, fichier_taille)
           VALUES (?,?,?,?,?,?,?)''',
        (date_dep, description, montant, request.form.get('categorie', 'Autre'),
         fichier_nom_original, fichier_nom_stocke, fichier_taille)
    )
    conn.commit()
    conn.close()

    if is_ajax:
        return jsonify({'success': True})
    flash('Dépense ajoutée.', 'success')
    return redirect('/comptabilite')

@admin_compta_bp.route('/depenses/<int:dep_id>/fichier')
@login_required
def depense_fichier(dep_id):
    conn = get_db()
    d = conn.execute('SELECT * FROM depenses WHERE id = ?', (dep_id,)).fetchone()
    conn.close()
    if not d or not d['fichier_nom_stocke']:
        return redirect('/comptabilite')
    dossier = os.path.join(UPLOAD_ROOT, 'depenses')
    return send_from_directory(dossier, d['fichier_nom_stocke'], as_attachment=True, download_name=d['fichier_nom_original'])

@admin_compta_bp.route('/depenses/<int:dep_id>/delete', methods=['POST'])
@login_required
def depense_delete(dep_id):
    conn = get_db()
    d = conn.execute('SELECT fichier_nom_stocke FROM depenses WHERE id = ?', (dep_id,)).fetchone()
    conn.execute('DELETE FROM depenses WHERE id = ?', (dep_id,))
    conn.commit()
    conn.close()
    if d and d['fichier_nom_stocke']:
        chemin = os.path.join(UPLOAD_ROOT, 'depenses', d['fichier_nom_stocke'])
        try: os.remove(chemin)
        except OSError: pass
    flash('Dépense supprimée.', 'success')
    return redirect('/comptabilite')

@admin_compta_bp.route('/admin/export/csv')
@login_required
def export_csv():
    conn = get_db()
    # 1. On récupère les factures PAYÉES (vrais revenus)
    factures = conn.execute('''
        SELECT f.date_paiement as date, f.description, f.milestone_titre, f.montant, c.nom as client_nom
        FROM factures f
        JOIN clients c ON c.id = f.client_id
        WHERE f.statut = 'payée' AND c.demo = 0
    ''').fetchall()

    # 2. On récupère les dépenses
    depenses = conn.execute('SELECT date, description, categorie, montant FROM depenses').fetchall()
    conn.close()

    # 3. Création du fichier CSV en mémoire (sans créer de vrai fichier sur le serveur)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';') # Le point-virgule évite les bugs dans Excel FR
    writer.writerow(['Date', 'Type', 'Description', 'Catégorie / Client', 'Revenu (+)', 'Dépense (-)'])

    lignes = []
    for f in factures:
        desc = f['description'] or f['milestone_titre'] or 'Facture'
        lignes.append([f['date'] or '', 'Revenu', desc, f['client_nom'], f['montant'], 0.0])

    for d in depenses:
        lignes.append([d['date'] or '', 'Dépense', d['description'], d['categorie'], 0.0, d['montant']])

    # 4. On trie tout par date chronologique !
    lignes.sort(key=lambda x: x[0])
    for ligne in lignes:
        writer.writerow(ligne)

    # 5. La fameuse réponse avec le Content-Disposition !
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers["Content-Disposition"] = f"attachment; filename=Comptabilite_TNTMom_{datetime.date.today().year}.csv"
    return response

# ── BUDGET FAMILIAL (BILL) ────────────────────────────────────────────────────

@admin_compta_bp.route('/api/household-revenues', methods=['POST'])
@login_required
def add_household_revenue():
    if session.get('user_role') not in ('staff', 'admin'):
        return jsonify({'success': False, 'error': 'Accès refusé'}), 403
    try:
        label, amount_str, date_received = (request.form.get('label') or '').strip(), (request.form.get('amount') or '').strip(), (request.form.get('date_received') or '').strip()
        if not label or not amount_str or not date_received: return jsonify({'success': False, 'error': 'Champs obligatoires'}), 400
        conn = get_db()
        conn.execute('INSERT INTO household_revenues (label, amount, date_received, is_taxable, added_by) VALUES (?,?,?,?,?)',
                     (label, float(amount_str), date_received, 1 if request.form.get('is_taxable') == 'on' else 0, session.get('username', 'Naomie')))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Revenu ajouté'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_compta_bp.route('/api/household-revenues/<int:rev_id>', methods=['DELETE'])
@login_required
def delete_household_revenue(rev_id):
    if session.get('user_role') not in ('staff', 'admin'):
        return jsonify({'success': False, 'error': 'Accès refusé'}), 403
    try:
        conn = get_db()
        conn.execute('DELETE FROM household_revenues WHERE id = ?', (rev_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_compta_bp.route('/bill/budget')
@login_required
def bill_budget():
    if session.get('user_role') != 'staff': return redirect(url_for('auth.login'))

    mois = request.args.get('mois') or datetime.datetime.now().strftime('%Y-%m')

    conn          = get_db()
    business_brut = conn.execute("SELECT SUM(montant) FROM factures WHERE statut = 'payée' AND strftime('%Y', date_emission) = '2026'").fetchone()[0] or 0
    revenus_mois  = conn.execute(
        "SELECT * FROM household_revenues WHERE strftime('%Y-%m', date_received) = ? ORDER BY date_received DESC",
        (mois,)
    ).fetchall()
    autres_revenus = sum(r['amount'] for r in revenus_mois)
    business_net    = business_brut * 0.75

    categories      = conn.execute("SELECT * FROM budget_categories ORDER BY ordre").fetchall()
    categories_list = []
    for cat in categories:
        spent = conn.execute(
            "SELECT SUM(montant) FROM budget_expenses WHERE category_id = ? AND strftime('%Y-%m', date) = ?",
            (cat['id'], mois)
        ).fetchone()[0] or 0
        cat_dict = dict(cat)
        cat_dict['spent'] = spent
        categories_list.append(cat_dict)

    expenses = conn.execute(
        "SELECT e.*, c.nom as category_nom FROM budget_expenses e JOIN budget_categories c ON e.category_id = c.id WHERE strftime('%Y-%m', e.date) = ? ORDER BY e.date DESC",
        (mois,)
    ).fetchall()
    conn.close()
    return render_template('bill/budget.html', revenu_global=business_net + autres_revenus,
                           business_net=business_net, autres_revenus=autres_revenus,
                           categories=categories_list, expenses=expenses, mois_actif=mois,
                           revenus=revenus_mois)



@admin_compta_bp.route('/api/budget-expense', methods=['POST'])
@login_required
def add_budget_expense():
    if session.get('user_role') != 'staff': return jsonify({'success': False, 'error': 'Accès refusé'}), 403
    try:
        conn = get_db()
        conn.execute("INSERT INTO budget_expenses (category_id, montant, date, description) VALUES (?, ?, ?, ?)", 
                     (request.form.get('category_id'), float(request.form.get('montant')), request.form.get('date'), request.form.get('description', '')))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'error': str(e)})

@admin_compta_bp.route('/api/budget-expense/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_budget_expense(expense_id):
    if session.get('user_role') != 'staff':
        return jsonify({'success': False, 'error': 'Accès refusé'}), 403
    try:
        conn = get_db()
        conn.execute("DELETE FROM budget_expenses WHERE id = ?", (expense_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    

# ─── HEURES ───────────────────────────────────────────────────────────────────

@admin_compta_bp.route('/heures')
@login_required
def heures():
    conn = get_db()
    categories = conn.execute(
        'SELECT * FROM categories_temps WHERE actif=1 ORDER BY ordre, id'
    ).fetchall()
    clients = conn.execute(
        "SELECT id, nom FROM clients WHERE statut != 'archivé' AND deleted = 0 ORDER BY nom"
    ).fetchall()
    contrats = conn.execute('''
        SELECT co.id, co.nom, co.client_id, cl.nom as client_nom
        FROM contrats co JOIN clients cl ON cl.id = co.client_id
        WHERE cl.statut != 'archivé' AND cl.deleted = 0
        ORDER BY cl.nom, co.nom
    ''').fetchall()
    timer_actif = conn.execute('''
        SELECT e.*, c.nom as cat_nom, c.couleur as cat_couleur,
               cl.nom as client_nom, co.nom as contrat_nom
        FROM entrees_temps e
        JOIN categories_temps c ON c.id = e.categorie_id
        LEFT JOIN clients cl ON cl.id = e.client_id
        LEFT JOIN contrats co ON co.id = e.contrat_id
        WHERE e.heure_fin IS NULL AND e.mode = 'timer'
        ORDER BY e.created_at DESC LIMIT 1
    ''').fetchone()
    entrees = conn.execute('''
        SELECT e.*, c.nom as cat_nom, c.couleur as cat_couleur,
               cl.nom as client_nom, co.nom as contrat_nom
        FROM entrees_temps e
        JOIN categories_temps c ON c.id = e.categorie_id
        LEFT JOIN clients cl ON cl.id = e.client_id
        LEFT JOIN contrats co ON co.id = e.contrat_id
        WHERE e.heure_fin IS NOT NULL OR e.mode = 'manuel'
        ORDER BY e.date DESC, e.created_at DESC
        LIMIT 50
    ''').fetchall()

    week_start  = (datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())).isoformat()
    month_start = datetime.date.today().replace(day=1).isoformat()

    stats_semaine = conn.execute('''
        SELECT COALESCE(SUM(duree_minutes), 0) as total_min,
               COALESCE(SUM(CASE WHEN type_facturation='horaire' AND taux_applique IS NOT NULL
                    THEN (duree_minutes / 60.0) * taux_applique ELSE 0 END), 0) as montant
        FROM entrees_temps
        WHERE date >= ? AND (heure_fin IS NOT NULL OR mode = 'manuel')
    ''', (week_start,)).fetchone()

    stats_mois = conn.execute('''
        SELECT COALESCE(SUM(duree_minutes), 0) as total_min,
               COALESCE(SUM(CASE WHEN type_facturation='horaire' AND taux_applique IS NOT NULL
                    THEN (duree_minutes / 60.0) * taux_applique ELSE 0 END), 0) as montant
        FROM entrees_temps
        WHERE date >= ? AND (heure_fin IS NOT NULL OR mode = 'manuel')
    ''', (month_start,)).fetchone()

    conn.close()
    return render_template('heures.html',
        categories=categories,
        clients=clients,
        contrats=contrats,
        timer_actif=timer_actif,
        entrees=entrees,
        stats_semaine=stats_semaine,
        stats_mois=stats_mois,
        today=datetime.date.today().isoformat()
    )

@admin_compta_bp.route('/heures/start', methods=['POST'])
@login_required
def heures_start():
    conn = get_db()
    if conn.execute("SELECT id FROM entrees_temps WHERE heure_fin IS NULL AND mode='timer'").fetchone():
        conn.close()
        return jsonify({'error': 'Un timer est déjà en cours.'}), 400

    data       = request.json or {}
    now_local  = datetime.datetime.now(_EASTERN)

    conn.execute('''
        INSERT INTO entrees_temps
        (client_id, contrat_id, milestone_titre, categorie_id,
         description, date, heure_debut, mode, type_facturation, taux_applique)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    ''', (
        data.get('client_id') or None,
        data.get('contrat_id') or None,
        data.get('milestone_titre') or None,
        data['categorie_id'],
        data.get('description') or None,
        now_local.strftime('%Y-%m-%d'),
        data.get('heure_debut') or now_local.strftime('%H:%M'),
        'timer',
        data.get('type_facturation', 'horaire'),
        data.get('taux_applique') or None,
    ))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@admin_compta_bp.route('/heures/stop', methods=['POST'])
@login_required
def heures_stop():
    conn = get_db()
    entree = conn.execute(
        "SELECT * FROM entrees_temps WHERE heure_fin IS NULL AND mode='timer' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if not entree:
        conn.close()
        return jsonify({'error': 'Aucun timer actif.'}), 404

    now_local  = datetime.datetime.now(_EASTERN)
    heure_fin  = now_local.strftime('%H:%M')
    try:
        debut_dt = datetime.datetime.strptime(entree['date'] + ' ' + entree['heure_debut'], '%Y-%m-%d %H:%M')
        fin_dt   = datetime.datetime.strptime(entree['date'] + ' ' + heure_fin, '%Y-%m-%d %H:%M')
        duree    = max(0, int((fin_dt - debut_dt).total_seconds() / 60))
    except Exception:
        duree = 0

    conn.execute('UPDATE entrees_temps SET heure_fin=?, duree_minutes=? WHERE id=?',
                 (heure_fin, duree, entree['id']))
    if entree['client_id'] and duree:
        banque = conn.execute(
            "SELECT id FROM banque_heures WHERE client_id=? AND statut='actif' ORDER BY date_achat DESC LIMIT 1",
            (entree['client_id'],)
        ).fetchone()
        if banque:
            conn.execute(
                "UPDATE banque_heures SET minutes_utilisees = minutes_utilisees + ? WHERE id=?",
                (duree, banque['id'])
            )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'duree_minutes': duree})

@admin_compta_bp.route('/heures/manuel', methods=['POST'])
@login_required
def heures_manuel():
    f = request.form
    try:
        duree = int(f.get('duree_minutes') or 0)
        hd, hf = f.get('heure_debut') or None, f.get('heure_fin') or None
        if hd and hf and not duree:
            date_s   = f.get('date') or datetime.date.today().isoformat()
            debut_dt = datetime.datetime.strptime(date_s + ' ' + hd, '%Y-%m-%d %H:%M')
            fin_dt   = datetime.datetime.strptime(date_s + ' ' + hf, '%Y-%m-%d %H:%M')
            duree    = max(0, int((fin_dt - debut_dt).total_seconds() / 60))
    except Exception:
        duree = 0

    taux = None
    try:
        v = f.get('taux_applique')
        if v:
            taux = float(v) or None
    except Exception:
        pass

    conn = get_db()
    conn.execute('''
        INSERT INTO entrees_temps
        (client_id, contrat_id, milestone_titre, categorie_id,
         description, date, heure_debut, heure_fin, duree_minutes,
         mode, type_facturation, taux_applique)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        f.get('client_id') or None,
        f.get('contrat_id') or None,
        f.get('milestone_titre') or None,
        f.get('categorie_id'),
        f.get('description') or None,
        f.get('date') or datetime.date.today().isoformat(),
        f.get('heure_debut') or None,
        f.get('heure_fin') or None,
        duree,
        'manuel',
        f.get('type_facturation', 'horaire'),
        taux,
    ))
    client_id_val = f.get('client_id') or None
    if client_id_val and duree:
        banque = conn.execute(
            "SELECT id FROM banque_heures WHERE client_id=? AND statut='actif' ORDER BY date_achat DESC LIMIT 1",
            (client_id_val,)
        ).fetchone()
        if banque:
            conn.execute(
                "UPDATE banque_heures SET minutes_utilisees = minutes_utilisees + ? WHERE id=?",
                (duree, banque['id'])
            )
    conn.commit()
    conn.close()

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        return jsonify({'success': True})

    flash('Entrée ajoutée.', 'success')
    return redirect('/heures')

@admin_compta_bp.route('/heures/supprimer/<int:eid>', methods=['POST'])
@login_required
def heures_supprimer(eid):
    conn = get_db()
    conn.execute('DELETE FROM entrees_temps WHERE id=?', (eid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@admin_compta_bp.route('/heures/<int:eid>/edit', methods=['POST'])
@login_required
def heures_edit(eid):
    """Modifie une entrée existante dans l'historique."""
    f = request.form

    # Recalcul de la durée si les heures sont fournies
    hd = f.get('heure_debut') or None
    hf = f.get('heure_fin') or None
    try:
        duree = int(f.get('duree_minutes') or 0)
        if hd and hf and not duree:
            date_s   = f.get('date') or datetime.date.today().isoformat()
            debut_dt = datetime.datetime.strptime(date_s + ' ' + hd, '%Y-%m-%d %H:%M')
            fin_dt   = datetime.datetime.strptime(date_s + ' ' + hf, '%Y-%m-%d %H:%M')
            duree    = max(0, int((fin_dt - debut_dt).total_seconds() / 60))
    except Exception:
        duree = 0

    taux = None
    try:
        v = f.get('taux_applique')
        if v:
            taux = float(v) or None
    except Exception:
        pass

    conn = get_db()
    conn.execute('''
        UPDATE entrees_temps
        SET date=?, heure_debut=?, heure_fin=?, duree_minutes=?,
            description=?, type_facturation=?, taux_applique=?, categorie_id=?
        WHERE id=?
    ''', (
        f.get('date') or datetime.date.today().isoformat(),
        hd, hf, duree,
        f.get('description') or None,
        f.get('type_facturation', 'horaire'),
        taux,
        f.get('categorie_id') or None,
        eid,
    ))
    conn.commit()
    conn.close()
    flash('Entrée mise à jour.', 'success')
    return redirect('/heures')

@admin_compta_bp.route('/heures/timer/start-time', methods=['POST'])
@login_required
def heures_timer_start_time():
    """Ajuste l'heure de départ du timer en cours sans arrêter le timer."""
    nouvelle_heure = (request.json or {}).get('heure_debut', '')
    if not nouvelle_heure:
        return jsonify({'error': 'Heure manquante.'}), 400

    conn = get_db()
    entree = conn.execute(
        "SELECT * FROM entrees_temps WHERE heure_fin IS NULL AND mode='timer' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if not entree:
        conn.close()
        return jsonify({'error': 'Aucun timer actif.'}), 404

    # Reconstruire le datetime de départ avec la nouvelle heure (même date)
    try:
        debut_dt = datetime.datetime.strptime(entree['date'] + ' ' + nouvelle_heure, '%Y-%m-%d %H:%M')
    except ValueError:
        conn.close()
        return jsonify({'error': 'Format invalide (HH:MM attendu).'}), 400

    conn.execute(
        'UPDATE entrees_temps SET heure_debut=?, created_at=? WHERE id=?',
        (nouvelle_heure, debut_dt.strftime('%Y-%m-%d %H:%M:%S'), entree['id'])
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'new_start': debut_dt.isoformat()})

@admin_compta_bp.route('/heures/categories', methods=['POST'])
@login_required
def heures_categories():
    nom = request.form.get('nom', '').strip()
    if not nom:
        flash('Le nom est requis.', 'error')
        return redirect('/heures')
    conn = get_db()
    max_ordre = conn.execute('SELECT COALESCE(MAX(ordre), 0) FROM categories_temps').fetchone()[0]
    taux_min = None
    taux_max = None
    try:
        v = request.form.get('taux_min')
        if v:
            taux_min = float(v) or None
    except Exception:
        pass
    try:
        v = request.form.get('taux_max')
        if v:
            taux_max = float(v) or None
    except Exception:
        pass
    conn.execute(
        'INSERT INTO categories_temps (nom, description, taux_min, taux_max, couleur, ordre) VALUES (?,?,?,?,?,?)',
        (nom, request.form.get('description', '').strip() or None,
         taux_min, taux_max, request.form.get('couleur', '#d94fbd'), max_ordre + 1)
    )
    conn.commit()
    conn.close()
    flash('Catégorie ajoutée.', 'success')
    return redirect('/heures')

@admin_compta_bp.route('/heures/rapports')
@login_required
def heures_rapports():
    debut = request.args.get('debut', '').strip()
    fin = request.args.get('fin', '').strip()

    filtre_dates = ''
    params = []
    if debut:
        filtre_dates += ' AND e.date >= ?'
        params.append(debut)
    if fin:
        filtre_dates += ' AND e.date <= ?'
        params.append(fin)

    conn = get_db()
    par_categorie = conn.execute(f'''
        SELECT c.nom as cat_nom, c.couleur,
               COALESCE(SUM(e.duree_minutes), 0) as total_min,
               COALESCE(SUM(CASE WHEN e.type_facturation='horaire' AND e.taux_applique IS NOT NULL
                    THEN (e.duree_minutes / 60.0) * e.taux_applique ELSE 0 END), 0) as montant,
               COUNT(*) as nb_entrees
        FROM entrees_temps e
        JOIN categories_temps c ON c.id = e.categorie_id
        WHERE (e.heure_fin IS NOT NULL OR e.mode = 'manuel'){filtre_dates}
        GROUP BY e.categorie_id
        ORDER BY total_min DESC
    ''', params).fetchall()

    par_projet = conn.execute(f'''
        SELECT cl.nom as client_nom, co.nom as projet_nom,
               COALESCE(cl.rnd, 0) as rnd,
               COALESCE(SUM(e.duree_minutes), 0) as total_min,
               COALESCE(SUM(CASE WHEN e.type_facturation='horaire' AND e.taux_applique IS NOT NULL
                    THEN (e.duree_minutes / 60.0) * e.taux_applique ELSE 0 END), 0) as montant_facturable,
               COALESCE(SUM(CASE WHEN cl.id IS NOT NULL AND COALESCE(cl.rnd, 0) = 0
                    THEN (e.duree_minutes / 60.0) * COALESCE(e.taux_applique, cat.taux_max, 0)
                    ELSE 0 END), 0) as valeur_accumulee
        FROM entrees_temps e
        JOIN categories_temps cat ON cat.id = e.categorie_id
        LEFT JOIN clients cl ON cl.id = e.client_id
        LEFT JOIN contrats co ON co.id = e.contrat_id
        WHERE (e.heure_fin IS NOT NULL OR e.mode = 'manuel'){filtre_dates}
        GROUP BY e.contrat_id, e.client_id
        ORDER BY total_min DESC
    ''', params).fetchall()

    par_semaine = conn.execute(f'''
        SELECT strftime('%Y — sem. %W', e.date) as semaine,
               strftime('%Y%W', e.date) as semaine_sort,
               COALESCE(SUM(e.duree_minutes), 0) as total_min,
               COALESCE(SUM(CASE WHEN e.type_facturation='horaire' AND e.taux_applique IS NOT NULL
                    THEN (e.duree_minutes / 60.0) * e.taux_applique ELSE 0 END), 0) as montant
        FROM entrees_temps e
        WHERE (e.heure_fin IS NOT NULL OR e.mode = 'manuel'){filtre_dates}
        GROUP BY semaine_sort
        ORDER BY semaine_sort DESC
        LIMIT 8
    ''', params).fetchall()

    conn.close()
    return render_template('heures_rapports.html',
        par_categorie=par_categorie,
        par_projet=par_projet,
        par_semaine=par_semaine,
        debut=debut,
        fin=fin,
    )

@admin_compta_bp.route('/api/heures/milestones/<int:contrat_id>')
@login_required
def api_heures_milestones(contrat_id):
    conn = get_db()
    contrat = conn.execute('SELECT milestones FROM contrats WHERE id=?', (contrat_id,)).fetchone()
    conn.close()
    if not contrat or not contrat['milestones']:
        return jsonify([])
    ms = safe_json_loads(contrat['milestones'], default=[])
    return jsonify([{'titre': m.get('titre', ''), 'statut': m.get('statut', '')} for m in ms])

@admin_compta_bp.route('/api/budget-categories', methods=['POST'])
@login_required
def create_budget_category():
    if session.get('user_role') != 'staff': return jsonify({'success': False}), 403
    try:
        conn = get_db()
        max_ordre = conn.execute("SELECT MAX(ordre) FROM budget_categories").fetchone()[0] or 0
        conn.execute("INSERT INTO budget_categories (nom, type, budget_mensuel, couleur, ordre) VALUES (?, ?, ?, ?, ?)", 
                     (request.form.get('nom'), request.form.get('type'), float(request.form.get('budget_mensuel')), request.form.get('couleur'), max_ordre + 1))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'error': str(e)})

@admin_compta_bp.route('/api/budget-categories/<int:cat_id>', methods=['PUT', 'DELETE'])
@login_required
def manage_budget_category(cat_id):
    if session.get('user_role') != 'staff': return jsonify({'success': False}), 403
    try:
        conn = get_db()
        if request.method == 'DELETE':
            conn.execute("DELETE FROM budget_categories WHERE id = ?", (cat_id,))
        else:
            conn.execute("UPDATE budget_categories SET nom = ?, type = ?, budget_mensuel = ?, couleur = ? WHERE id = ?", 
                         (request.form.get('nom'), request.form.get('type'), float(request.form.get('budget_mensuel')), request.form.get('couleur'), cat_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'error': str(e)})