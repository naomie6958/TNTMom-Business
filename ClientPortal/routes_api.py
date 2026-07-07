import datetime
import secrets
import json
from flask import Blueprint, request, jsonify, current_app
from database import get_db
from utils import send_notification_email
from email_templates import (
    email_lead_naomie, email_lead_confirmation,
    email_form_submission_client, email_form_submission_underground_motorsport
)
from client_form_config import CLIENT_SITES

# Gabarits brandés par client — sinon fallback sur le gabarit générique TNTMom
CUSTOM_EMAIL_TEMPLATES = {
    'underground-motorsport': lambda nom_site, champs: email_form_submission_underground_motorsport(champs),
}

# Création du Blueprint avec le préfixe /api
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/public/contact', methods=['POST', 'OPTIONS'])
def api_public_contact():
    # Preflight CORS
    if request.method == 'OPTIONS':
        resp = current_app.make_response('')
        resp.headers['Access-Control-Allow-Origin']  = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp, 204

    data    = request.get_json(silent=True) or request.form
    nom     = (data.get('nom') or '').strip()
    email   = (data.get('email') or data.get('courriel') or '').strip()
    message = (data.get('message') or '').strip()

    if not nom or not message:
        resp = jsonify({'error': 'Nom et message requis.'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    conn = get_db()
    token        = secrets.token_urlsafe(32)
    token_expiry = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

    conn.execute(
        'INSERT INTO leads (nom, email, message, access_token, token_expiry) VALUES (?, ?, ?, ?, ?)',
        (nom, email, message, token, token_expiry)
    )
    conn.commit()
    conn.close()

    send_notification_email(
        f'[TNTMom] Nouveau message de {nom}',
        f'Nom : {nom}\nCourriel : {email or "(non fourni)"}\n\n{message}',
        html=email_lead_naomie(nom, email, message)
    )

    if email:
        send_notification_email(
            'Merci pour ton message — TNTMom',
            f'Bonjour {nom},\n\nMerci pour ton message ! Je l\'ai bien reçu et je te répondrai dans les 24-48h.',
            to=email,
            html=email_lead_confirmation(nom)
        )

    resp = jsonify({'ok': True})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@api_bp.route('/public/form-submit', methods=['POST', 'OPTIONS'])
def api_public_form_submit():
    # Preflight CORS
    if request.method == 'OPTIONS':
        resp = current_app.make_response('')
        resp.headers['Access-Control-Allow-Origin']  = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp, 204

    data = request.get_json(silent=True) or request.form
    client_slug = (data.get('client') or request.args.get('client') or '').strip()

    site = CLIENT_SITES.get(client_slug)
    if not site:
        resp = jsonify({'error': 'Site client inconnu.'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    # Honeypot anti-spam : champ caché "_honeypot" — un humain ne le remplit jamais.
    # On répond succès sans rien envoyer ni stocker, pour ne pas alerter le bot.
    if (data.get('_honeypot') or '').strip():
        resp = jsonify({'ok': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

    champs = {
        k: v for k, v in data.items()
        if k not in ('client', '_honeypot') and str(v).strip()
    }

    if not champs:
        resp = jsonify({'error': 'Formulaire vide.'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    conn = get_db()
    conn.execute(
        'INSERT INTO client_form_submissions (client_site, data) VALUES (?, ?)',
        (client_slug, json.dumps(champs, ensure_ascii=False))
    )
    conn.commit()
    conn.close()

    render_html = CUSTOM_EMAIL_TEMPLATES.get(client_slug, email_form_submission_client)
    send_notification_email(
        f"Nouvelle demande — {site['nom']}",
        "\n".join(f"{k} : {v}" for k, v in champs.items()),
        to=site['email'],
        html=render_html(site['nom'], champs)
    )

    resp = jsonify({'ok': True})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@api_bp.route('/public/tarifs')
def api_public_tarifs():
    conn = get_db()
    rows = conn.execute(
        'SELECT titre, description, prix, unite, inclus, non_inclus FROM tarifs WHERE actif = 1 ORDER BY ordre, id'
    ).fetchall()
    conn.close()
    resp = jsonify([dict(r) for r in rows])
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@api_bp.route('/public/projets')
def api_public_projets():
    conn = get_db()
    rows = conn.execute(
        'SELECT nom, tagline, description, tags, statut, couleur, image_url, link FROM portfolio_projets WHERE actif = 1 ORDER BY ordre, id'
    ).fetchall()
    conn.close()

    projets = []
    for r in rows:
        projets.append({
            'nom':          r['nom'],
            'tagline':      r['tagline'],
            'description':  r['description'],
            'tags':         json.loads(r['tags'] or '[]'),
            'statut':       r['statut'],
            'couleur':      r['couleur'],
            'image':        r['image_url'],
            'link':         r['link'],
        })

    resp = jsonify(projets)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp