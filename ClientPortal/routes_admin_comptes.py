from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash
from database import get_db
from utils import login_required

admin_comptes_bp = Blueprint('admin_comptes', __name__)


@admin_comptes_bp.route('/admin/comptes')
@login_required
def liste_comptes():
    if session.get('user_role') != 'admin':
        return redirect('/dashboard')

    conn = get_db()
    comptes = conn.execute('SELECT id, username, name, role FROM users ORDER BY name').fetchall()
    conn.close()

    return render_template('admin_comptes.html', comptes=comptes)


@admin_comptes_bp.route('/admin/comptes/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_password(user_id):
    if session.get('user_role') != 'admin':
        return redirect('/dashboard')

    nouveau_mdp = request.form.get('nouveau_mot_de_passe', '').strip()
    if not nouveau_mdp:
        flash("Le mot de passe ne peut pas être vide.")
        return redirect('/admin/comptes')

    conn = get_db()
    conn.execute('UPDATE users SET password = ? WHERE id = ?', (generate_password_hash(nouveau_mdp), user_id))
    conn.commit()
    conn.close()

    flash("Mot de passe mis à jour.")
    return redirect('/admin/comptes')


@admin_comptes_bp.route('/admin/comptes/creer', methods=['POST'])
@login_required
def creer_compte():
    if session.get('user_role') != 'admin':
        return redirect('/dashboard')

    username = request.form.get('username', '').strip().lower()
    name = request.form.get('name', '').strip()
    role = request.form.get('role', 'staff')
    password = request.form.get('password', '').strip()

    if not username or not name or not password:
        flash("Tous les champs sont requis pour créer un compte.")
        return redirect('/admin/comptes')

    if role not in ('admin', 'staff'):
        role = 'staff'

    conn = get_db()
    existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if existing:
        flash(f"Le nom d'utilisateur '{username}' existe déjà.")
        conn.close()
        return redirect('/admin/comptes')

    conn.execute(
        'INSERT INTO users (username, password, name, role) VALUES (?, ?, ?, ?)',
        (username, generate_password_hash(password), name, role)
    )
    conn.commit()
    conn.close()

    flash(f"Compte '{name}' créé avec succès.")
    return redirect('/admin/comptes')