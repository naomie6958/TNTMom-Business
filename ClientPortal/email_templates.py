def base_email(contenu_html):
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#1a1a1a;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#1a1a1a;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#242424;border-radius:8px;overflow:hidden;max-width:600px;width:100%;">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#111111;padding:20px 24px;border-bottom:2px solid #FF0090;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="80" style="vertical-align:middle;">
                    <img src="https://tntm.ca/images/Logo_gem.png" alt="TNTMom" height="160" style="display:block;">
                  </td>
                  <td style="vertical-align:middle;text-align:center;">
                    <p style="margin:0;font-size:26px;font-weight:bold;letter-spacing:2px;color:#D4AF37;">TNTMom</p>
                    <p style="margin:4px 0 0;font-size:11px;letter-spacing:1px;">
                      <span style="color:#ffffff;">Gestionnaire du </span><span style="color:#FF0090;">chaos</span><span style="color:#ffffff;">, par le </span><span style="color:#00CED1;">chaos</span>
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CONTENU -->
          <tr>
            <td style="padding:36px 40px;color:#f0f0f0;font-size:15px;line-height:1.7;">
              {contenu_html}
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:24px 40px;border-top:1px solid #333333;text-align:center;">
              <p style="margin:0;color:#00CED1;font-size:13px;font-weight:bold;">Naomie</p>
              <p style="margin:4px 0 0;color:#888888;font-size:12px;">Développeure web freelance</p>
              <p style="margin:4px 0 0;font-size:12px;">
                <a href="https://tntm.ca" style="color:#FF0090;text-decoration:none;">tntm.ca</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _base_email_interne(titre, contenu_html):
    contenu_avec_header = f"""
      <p style="margin:0 0 20px 0;"><span style="display:inline-block;padding:4px 12px;background-color:#00CED1;color:#111111;font-size:11px;font-weight:bold;border-radius:4px;letter-spacing:1px;">NOTIFICATION INTERNE</span></p>
      <p style="margin:0 0 24px;font-size:20px;font-weight:bold;color:#00CED1;">{titre}</p>
      {contenu_html}
    """
    return base_email(contenu_avec_header)


# ─── COURRIELS CLIENT ────────────────────────────────────────────────────────

def email_bienvenue(nom_client, lien_acces):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#FF0090;">Bienvenue, {nom_client} ! ✨</p>
      <p style="margin:0 0 24px;color:#aaaaaa;font-size:13px;">Ton portail client TNTMom est prêt.</p>

      <p style="margin:0 0 16px;">Ton espace personnel est maintenant créé. Tu peux y suivre l'avancement de ton projet, approuver les étapes, consulter tes contrats et me laisser des messages.</p>

      <p style="margin:0 0 24px;">Connecte-toi à ton portail pour suivre ton projet :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#FF0090;border-radius:6px;padding:14px 32px;text-align:center;">
            <a href="{lien_acces}" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:15px;">Accéder à mon portail</a>
          </td>
        </tr>
      </table>

      <p style="margin:0 0 4px;color:#888888;font-size:12px;">Conserve ce courriel — il contient ton lien d'accès direct au portail.</p>
      <p style="margin:0;color:#888888;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)


def email_contrat_envoye(nom_client, nom_projet):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#FF0090;">Ton contrat est prêt, {nom_client} ! ✍</p>
      <p style="margin:0 0 24px;color:#aaaaaa;font-size:13px;">Une nouvelle étape dans ton projet TNTMom.</p>

      <p style="margin:0 0 8px;">J'ai préparé un contrat pour ton projet :</p>
      <p style="margin:0 0 24px;padding:12px 20px;background-color:#1a1a1a;border-left:3px solid #FF0090;font-weight:bold;color:#ffffff;">{nom_projet}</p>

      <p style="margin:0 0 24px;">Connecte-toi à ton portail pour le lire et le signer :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#FF0090;border-radius:6px;padding:14px 32px;text-align:center;">
            <a href="https://tntmom.pythonanywhere.com/portail/login" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:15px;">Lire et signer mon contrat</a>
          </td>
        </tr>
      </table>

      <p style="margin:0;color:#888888;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)


def email_milestone_livre(nom_client, titre_milestone):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#FF0090;">Bonne nouvelle, {nom_client} ! 🎉</p>
      <p style="margin:0 0 24px;color:#aaaaaa;font-size:13px;">Une étape de ton projet est prête pour ta révision.</p>

      <p style="margin:0 0 8px;">L'étape suivante est maintenant complétée :</p>
      <p style="margin:0 0 24px;padding:12px 20px;background-color:#1a1a1a;border-left:3px solid #FF0090;font-weight:bold;color:#ffffff;">{titre_milestone}</p>

      <p style="margin:0 0 24px;">Connecte-toi à ton portail pour consulter les livrables et approuver l'étape :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#FF0090;border-radius:6px;padding:14px 32px;text-align:center;">
            <a href="https://tntmom.pythonanywhere.com/portail/login" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:15px;">Voir mon livrable</a>
          </td>
        </tr>
      </table>

      <p style="margin:0;color:#888888;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)


def email_reponse_message(nom_client, sujet):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#FF0090;">Naomie t'a répondu 💬</p>
      <p style="margin:0 0 24px;color:#aaaaaa;font-size:13px;">Tu as reçu une réponse dans ton portail.</p>

      <p style="margin:0 0 8px;">Réponse à ton message :</p>
      <p style="margin:0 0 24px;padding:12px 20px;background-color:#1a1a1a;border-left:3px solid #00CED1;color:#ffffff;">« {sujet} »</p>

      <p style="margin:0 0 24px;">Connecte-toi à ton portail pour lire la réponse :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#FF0090;border-radius:6px;padding:14px 32px;text-align:center;">
            <a href="https://tntmom.pythonanywhere.com/portail/login" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:15px;">Lire la réponse</a>
          </td>
        </tr>
      </table>

      <p style="margin:0;color:#888888;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)


def email_message_naomie(nom_client, sujet):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#FF0090;">Tu as un nouveau message 📩</p>
      <p style="margin:0 0 24px;color:#aaaaaa;font-size:13px;">Naomie t'a envoyé un message dans ton portail.</p>

      <p style="margin:0 0 8px;">Sujet :</p>
      <p style="margin:0 0 24px;padding:12px 20px;background-color:#1a1a1a;border-left:3px solid #00CED1;color:#ffffff;">« {sujet} »</p>

      <p style="margin:0 0 24px;">Connecte-toi à ton portail pour le lire :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#FF0090;border-radius:6px;padding:14px 32px;text-align:center;">
            <a href="https://tntmom.pythonanywhere.com/portail/login" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:15px;">Lire mon message</a>
          </td>
        </tr>
      </table>

      <p style="margin:0;color:#888888;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)


def email_lead_confirmation(nom):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#FF0090;">Merci pour ton message, {nom} ! 🙌</p>
      <p style="margin:0 0 24px;color:#aaaaaa;font-size:13px;">Je l'ai bien reçu.</p>

      <p style="margin:0 0 24px;">Je lis tous mes messages et je te reviens personnellement dans les <strong style="color:#ffffff;">24 à 48h</strong>.</p>

      <p style="margin:0 0 24px;">En attendant, jette un œil à mes services :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#FF0090;border-radius:6px;padding:14px 32px;text-align:center;">
            <a href="https://tntm.ca" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:15px;">Visiter tntm.ca</a>
          </td>
        </tr>
      </table>

      <p style="margin:0;color:#888888;font-size:12px;">À très bientôt !</p>
    """
    return base_email(contenu)


# ─── NOTIFICATIONS INTERNES (NAOMIE) ─────────────────────────────────────────

def email_contrat_signe_naomie(nom_client, nom_projet):
    contenu = f"""
      <p style="margin:0 0 8px;"><strong style="color:#ffffff;">{nom_client}</strong> vient de signer son contrat.</p>
      <p style="margin:0 0 24px;padding:12px 20px;background-color:#1a1a1a;border-left:3px solid #00CED1;color:#ffffff;">{nom_projet}</p>
      <p style="margin:0 0 24px;">Connecte-toi au portail pour voir les détails et démarrer le projet.</p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#00CED1;border-radius:6px;padding:14px 32px;text-align:center;">
            <a href="https://tntmom.pythonanywhere.com/dashboard" style="color:#111111;text-decoration:none;font-weight:bold;font-size:15px;">Voir le portail</a>
          </td>
        </tr>
      </table>
    """
    return _base_email_interne(f"✍ Contrat signé — {nom_projet}", contenu)


def email_milestone_approuve_naomie(nom_client, titre):
    contenu = f"""
      <p style="margin:0 0 8px;"><strong style="color:#ffffff;">{nom_client}</strong> vient d'approuver une étape.</p>
      <p style="margin:0 0 24px;padding:12px 20px;background-color:#1a1a1a;border-left:3px solid #00CED1;color:#ffffff;">{titre}</p>
      <p style="margin:0 0 24px;">Tu peux maintenant marquer la facture comme payée.</p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#00CED1;border-radius:6px;padding:14px 32px;text-align:center;">
            <a href="https://tntmom.pythonanywhere.com/dashboard" style="color:#111111;text-decoration:none;font-weight:bold;font-size:15px;">Voir le portail</a>
          </td>
        </tr>
      </table>
    """
    return _base_email_interne(f"✅ Milestone approuvé — {titre}", contenu)


def email_message_recu_naomie(nom_client, sujet, message):
    contenu = f"""
      <p style="margin:0 0 4px;"><strong style="color:#ffffff;">{nom_client}</strong> t'a envoyé un message.</p>
      <p style="margin:0 0 16px;color:#aaaaaa;font-size:13px;">Sujet : {sujet or '(aucun)'}</p>
      <p style="margin:0 0 24px;padding:16px 20px;background-color:#1a1a1a;border-left:3px solid #00CED1;color:#f0f0f0;font-style:italic;">{message}</p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#00CED1;border-radius:6px;padding:14px 32px;text-align:center;">
            <a href="https://tntmom.pythonanywhere.com/dashboard" style="color:#111111;text-decoration:none;font-weight:bold;font-size:15px;">Répondre dans le portail</a>
          </td>
        </tr>
      </table>
    """
    return _base_email_interne(f"💬 Message de {nom_client}", contenu)


def email_lead_naomie(nom, email_client, message):
    email_ligne = f'<p style="margin:0 0 4px;color:#aaaaaa;font-size:13px;">Courriel : <strong style="color:#ffffff;">{email_client}</strong></p>' if email_client else ''
    contenu = f"""
      <p style="margin:0 0 8px;">Nouveau lead depuis le formulaire de contact de tntm.ca.</p>
      <p style="margin:0 0 4px;color:#aaaaaa;font-size:13px;">Nom : <strong style="color:#ffffff;">{nom}</strong></p>
      {email_ligne}
      <p style="margin:16px 0 24px;padding:16px 20px;background-color:#1a1a1a;border-left:3px solid #00CED1;color:#f0f0f0;font-style:italic;">{message}</p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#00CED1;border-radius:6px;padding:14px 32px;text-align:center;">
            <a href="https://tntmom.pythonanywhere.com/leads" style="color:#111111;text-decoration:none;font-weight:bold;font-size:15px;">Voir les leads</a>
          </td>
        </tr>
      </table>
    """
    return _base_email_interne(f"🔔 Nouveau lead — {nom}", contenu)


def email_formulaire_naomie(nom_client, titre_formulaire):
    contenu = f"""
      <p style="margin:0 0 8px;"><strong style="color:#ffffff;">{nom_client}</strong> vient de remplir un formulaire.</p>
      <p style="margin:0 0 24px;padding:12px 20px;background-color:#1a1a1a;border-left:3px solid #00CED1;color:#ffffff;">{titre_formulaire}</p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#00CED1;border-radius:6px;padding:14px 32px;text-align:center;">
            <a href="https://tntmom.pythonanywhere.com/dashboard" style="color:#111111;text-decoration:none;font-weight:bold;font-size:15px;">Voir les réponses</a>
          </td>
        </tr>
      </table>
    """
    return _base_email_interne(f"📋 Formulaire rempli — {titre_formulaire}", contenu)



def email_facture(nom_client, numero, contrat_nom, description, montant, date_emission, statut):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#FF0090;">Ta facture est prête, {nom_client} 🧾</p>
      <p style="margin:0 0 24px;color:#aaaaaa;font-size:13px;">Voici le détail de ta facture.</p>

      <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 32px;border-collapse:collapse;font-size:14px;">
        <tr>
          <td style="padding:10px 14px;background-color:#1a1a1a;color:#aaaaaa;width:40%;">Projet</td>
          <td style="padding:10px 14px;background-color:#1a1a1a;color:#ffffff;">{contrat_nom}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;background-color:#222222;color:#aaaaaa;">Description</td>
          <td style="padding:10px 14px;background-color:#222222;color:#ffffff;">{description}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;background-color:#1a1a1a;color:#aaaaaa;">Montant</td>
          <td style="padding:10px 14px;background-color:#1a1a1a;font-size:16px;font-weight:bold;color:#FF0090;">{montant}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;background-color:#222222;color:#aaaaaa;">Date d'émission</td>
          <td style="padding:10px 14px;background-color:#222222;color:#ffffff;">{date_emission or '—'}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;background-color:#1a1a1a;color:#aaaaaa;">Statut</td>
          <td style="padding:10px 14px;background-color:#1a1a1a;color:#00CED1;font-weight:bold;">{statut}</td>
        </tr>
      </table>

      <p style="margin:0;color:#888888;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)
