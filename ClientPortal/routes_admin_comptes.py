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