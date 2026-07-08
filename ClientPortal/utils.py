import os
import resend
import datetime
import threading
from functools import wraps
import json
from flask import session, redirect

def _send_email_thread(subject, body, to, html):
    """Fonction interne exécutée par le thread en arrière-plan."""
    resend.api_key = os.getenv('RESEND_API_KEY')
    if not resend.api_key:
        import sys
        print('[EMAIL ERROR] RESEND_API_KEY manquant dans le .env', file=sys.stderr)
        return

    try:
        resend.Emails.send({
            "from": "Naomie | TNTMom <naomiemt@tntm.ca>",
            "to": [to or 'naomiemt@tntm.ca'],
            "reply_to": "naomiemt@tntm.ca",
            "subject": subject,
            "text": body,
            # Resend accepte html=None si t'as juste du texte brut à envoyer
            "html": html or None,
        })
    except Exception as e:
        import sys
        print(f'[EMAIL ERROR] {subject} → {to}: {e}', file=sys.stderr)


def send_notification_email(subject, body, to=None, html=None):
    """Lance l'envoi d'e-mail en arrière-plan sans bloquer l'interface Flask."""
    thread = threading.Thread(
        target=_send_email_thread,
        args=(subject, body, to, html)
    )
    thread.start()
    return True

def _compute_deadlines(milestones):
    """Calcule deadline[i] = milieu entre date[i] et date[i+1]. Modifie la liste en place."""
    for i, m in enumerate(milestones):
        if i < len(milestones) - 1:
            d1 = m.get('date', '')
            d2 = milestones[i + 1].get('date', '')
            if d1 and d2:
                try:
                    dt1 = datetime.datetime.strptime(d1, '%Y-%m-%d')
                    dt2 = datetime.datetime.strptime(d2, '%Y-%m-%d')
                    mid = dt1 + (dt2 - dt1) / 2
                    m['deadline'] = mid.strftime('%Y-%m-%d')
                except Exception:
                    m['deadline'] = ''
            else:
                m['deadline'] = ''
        else:
            m['deadline'] = ''
    return milestones

def group_messages(messages):
    """Regroupe les messages en fils de conversation par sujet de base (ignore les Re:)."""
    from collections import OrderedDict
    def base_subject(s):
        s = (s or '').strip()
        while s.lower().startswith('re: '):
            s = s[4:].strip()
        return s or 'Sans sujet'
    threads = OrderedDict()
    for msg in messages:
        key = base_subject(msg['sujet'])
        if key not in threads:
            threads[key] = []
        threads[key].append(dict(msg))
    return list(threads.items())

def safe_json_loads(data, default=None):
    """Sécurise la lecture JSON pour éviter les crashs (erreur 500)."""
    if not data:
        return default if default is not None else {}
    try:
        return json.loads(data)
    except Exception:
        return default if default is not None else {}

def _now():
    """Heure actuelle en UTC — to_local convertit à l'affichage."""
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

def login_required(f):
    @wraps(f)
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