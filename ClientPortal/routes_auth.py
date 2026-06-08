from flask import Blueprint, render_template, request, redirect, session
from werkzeug.security import check_password_hash
from database import get_db

# 1. Déclaration de notre Blueprint
auth_bp = Blueprint('auth', __name__)

# 2. On attache nos routes au Blueprint avec @auth_bp.route
@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

@auth_bp.route('/login', methods=['GET', 'POST'])
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

        if user and check_password_hash(user['password'], password):
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            if user['role'] == 'staff':
                return redirect('/bill/budget')
            return redirect('/dashboard')
        error = 'Identifiants incorrects.'
    return render_template('login.html', error=error)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')