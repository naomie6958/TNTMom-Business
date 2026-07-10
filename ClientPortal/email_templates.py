def base_email(contenu_html):
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#0f0f14;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f0f14;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#1a1a24;border:1px solid #2a2a3a;border-radius:12px;overflow:hidden;max-width:600px;width:100%;">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#1a1a24;padding:24px 32px;border-bottom:1px solid #2a2a3a;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="70" style="vertical-align:middle;">
                    <img src="https://tntm.ca/images/Logo_gem.png" alt="TNTMom" height="70" style="display:block;">
                  </td>
                  <td style="vertical-align:middle;text-align:right;">
                    <p style="margin:0;font-size:22px;font-weight:bold;letter-spacing:1px;color:#f0eeff;">TNTMom</p>
                    <p style="margin:4px 0 0;font-size:12px;letter-spacing:0.5px;">
                      <span style="color:#6e6e9a;">Gestionnaire du </span><span style="color:#d94fbd;">chaos</span><span style="color:#6e6e9a;">, par le </span><span style="color:#87CEEB;">chaos</span>
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CONTENU -->
          <tr>
            <td style="padding:36px 32px;color:#f0eeff;font-size:15px;line-height:1.7;">
              {contenu_html}
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:24px 32px;border-top:1px solid #2a2a3a;text-align:center;">
              <p style="margin:0;color:#87CEEB;font-size:13px;font-weight:bold;">Naomie McMahon Tanguay</p>
              <p style="margin:4px 0 0;color:#6e6e9a;font-size:12px;">Développeuse web freelance</p>
              <p style="margin:8px 0 0;font-size:12px;">
                <a href="https://tntm.ca" style="color:#d94fbd;text-decoration:none;font-weight:bold;">tntm.ca</a>
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
      <p style="margin:0 0 20px 0;"><span style="display:inline-block;padding:4px 12px;border:1px solid #87CEEB;color:#87CEEB;font-size:11px;font-weight:bold;border-radius:4px;letter-spacing:1px;">NOTIFICATION INTERNE</span></p>
      <p style="margin:0 0 24px;font-size:20px;font-weight:bold;color:#87CEEB;">{titre}</p>
      {contenu_html}
    """
    return base_email(contenu_avec_header)


# ─── COURRIELS CLIENT ────────────────────────────────────────────────────────

def email_bienvenue(nom_client, lien_acces):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#d94fbd;">Bienvenue, {nom_client} ! ✨</p>
      <p style="margin:0 0 24px;color:#6e6e9a;font-size:13px;">Ton portail client TNTMom est prêt.</p>

      <p style="margin:0 0 16px;">Ton espace personnel est maintenant créé. Tu peux y suivre l'avancement de ton projet, approuver les étapes, consulter tes contrats et me laisser des messages.</p>

      <p style="margin:0 0 24px;">Connecte-toi à ton portail pour suivre ton projet :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#d94fbd;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="{lien_acces}" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:14px;">Accéder à mon portail</a>
          </td>
        </tr>
      </table>

      <p style="margin:0 0 4px;color:#6e6e9a;font-size:12px;">Conserve ce courriel — il contient ton lien d'accès direct au portail.</p>
      <p style="margin:0;color:#6e6e9a;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)


def email_contrat_envoye(nom_client, nom_projet):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#d94fbd;">Ton contrat est prêt, {nom_client} ! ✍</p>
      <p style="margin:0 0 24px;color:#6e6e9a;font-size:13px;">Une nouvelle étape dans ton projet TNTMom.</p>

      <p style="margin:0 0 8px;">J'ai préparé un contrat pour ton projet :</p>
      <p style="margin:0 0 24px;padding:16px 20px;background-color:#222230;border-left:3px solid #d94fbd;font-weight:bold;color:#f0eeff;border-radius:4px;">{nom_projet}</p>

      <p style="margin:0 0 24px;">Connecte-toi à ton portail pour le lire et le signer :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#d94fbd;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://portail.tntm.ca/portail/login" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:14px;">Lire et signer mon contrat</a>
          </td>
        </tr>
      </table>

      <p style="margin:0;color:#6e6e9a;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)


def email_milestone_livre(nom_client, titre_milestone):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#d94fbd;">Bonne nouvelle, {nom_client} ! 🎉</p>
      <p style="margin:0 0 24px;color:#6e6e9a;font-size:13px;">Une étape de ton projet est prête pour ta révision.</p>

      <p style="margin:0 0 8px;">L'étape suivante est maintenant complétée :</p>
      <p style="margin:0 0 24px;padding:16px 20px;background-color:#222230;border-left:3px solid #d94fbd;font-weight:bold;color:#f0eeff;border-radius:4px;">{titre_milestone}</p>

      <p style="margin:0 0 24px;">Connecte-toi à ton portail pour consulter les livrables et approuver l'étape :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#d94fbd;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://portail.tntm.ca/portail/login" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:14px;">Voir mon livrable</a>
          </td>
        </tr>
      </table>

      <p style="margin:0;color:#6e6e9a;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)

def email_commentaire_fichier_admin(nom_client, nom_fichier, commentaire):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#d94fbd;">Nouveau commentaire 💬</p>
      <p style="margin:0 0 24px;color:#6e6e9a;font-size:13px;">Naomie a laissé un commentaire sur le fichier <strong>{nom_fichier}</strong>.</p>

      <p style="margin:0 0 24px;padding:16px 20px;background-color:#222230;border-left:3px solid #d94fbd;color:#f0eeff;font-style:italic;border-radius:4px;">« {commentaire} »</p>

      <p style="margin:0 0 24px;">Connecte-toi à ton portail pour voir le fichier et lui répondre :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#d94fbd;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://portail.tntm.ca/portail/login" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:14px;">Voir le commentaire</a>
          </td>
        </tr>
      </table>

      <p style="margin:0;color:#6e6e9a;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)


def email_reponse_message(nom_client, sujet):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#d94fbd;">Naomie t'a répondu 💬</p>
      <p style="margin:0 0 24px;color:#6e6e9a;font-size:13px;">Tu as reçu une réponse dans ton portail.</p>

      <p style="margin:0 0 8px;">Réponse à ton message :</p>
      <p style="margin:0 0 24px;padding:16px 20px;background-color:#222230;border-left:3px solid #d94fbd;color:#f0eeff;border-radius:4px;">« {sujet} »</p>

      <p style="margin:0 0 24px;">Connecte-toi à ton portail pour lire la réponse :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#d94fbd;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://portail.tntm.ca/portail/login" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:14px;">Lire la réponse</a>
          </td>
        </tr>
      </table>

      <p style="margin:0;color:#6e6e9a;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)


def email_message_naomie(nom_client, sujet):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#d94fbd;">Tu as un nouveau message 📩</p>
      <p style="margin:0 0 24px;color:#6e6e9a;font-size:13px;">Naomie t'a envoyé un message dans ton portail.</p>

      <p style="margin:0 0 8px;">Sujet :</p>
      <p style="margin:0 0 24px;padding:16px 20px;background-color:#222230;border-left:3px solid #d94fbd;color:#f0eeff;border-radius:4px;">« {sujet} »</p>

      <p style="margin:0 0 24px;">Connecte-toi à ton portail pour le lire :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#d94fbd;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://portail.tntm.ca/portail/login" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:14px;">Lire mon message</a>
          </td>
        </tr>
      </table>

      <p style="margin:0;color:#6e6e9a;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)


def email_lead_confirmation(nom):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#d94fbd;">Merci pour ton message, {nom} ! 🙌</p>
      <p style="margin:0 0 24px;color:#6e6e9a;font-size:13px;">Je l'ai bien reçu.</p>

      <p style="margin:0 0 24px;">Je lis tous mes messages et je te reviens personnellement dans les <strong style="color:#f0eeff;">24 à 48h</strong>.</p>

      <p style="margin:0 0 24px;">En attendant, jette un œil à mes services :</p>

      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#d94fbd;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://tntm.ca" style="color:#ffffff;text-decoration:none;font-weight:bold;font-size:14px;">Visiter tntm.ca</a>
          </td>
        </tr>
      </table>

      <p style="margin:0;color:#6e6e9a;font-size:12px;">À très bientôt !</p>
    """
    return base_email(contenu)


# ─── NOTIFICATIONS INTERNES (NAOMIE) ─────────────────────────────────────────

def email_contrat_signe_naomie(nom_client, nom_projet):
    contenu = f"""
      <p style="margin:0 0 8px;"><strong style="color:#f0eeff;">{nom_client}</strong> vient de signer son contrat.</p>
      <p style="margin:0 0 24px;padding:16px 20px;background-color:#222230;border-left:3px solid #87CEEB;color:#f0eeff;border-radius:4px;">{nom_projet}</p>
      <p style="margin:0 0 24px;">Connecte-toi au portail pour voir les détails et démarrer le projet.</p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#87CEEB;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://portail.tntm.ca/dashboard" style="color:#0f0f14;text-decoration:none;font-weight:bold;font-size:14px;">Voir le portail</a>
          </td>
        </tr>
      </table>
    """
    return _base_email_interne(f"✍ Contrat signé — {nom_projet}", contenu)


def email_milestone_approuve_naomie(nom_client, titre):
    contenu = f"""
      <p style="margin:0 0 8px;"><strong style="color:#f0eeff;">{nom_client}</strong> vient d'approuver une étape.</p>
      <p style="margin:0 0 24px;padding:16px 20px;background-color:#222230;border-left:3px solid #87CEEB;color:#f0eeff;border-radius:4px;">{titre}</p>
      <p style="margin:0 0 24px;">Tu peux maintenant marquer la facture comme payée.</p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#87CEEB;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://portail.tntm.ca/dashboard" style="color:#0f0f14;text-decoration:none;font-weight:bold;font-size:14px;">Voir le portail</a>
          </td>
        </tr>
      </table>
    """
    return _base_email_interne(f"✅ Milestone approuvé — {titre}", contenu)


def email_message_recu_naomie(nom_client, sujet, message):
    contenu = f"""
      <p style="margin:0 0 4px;"><strong style="color:#f0eeff;">{nom_client}</strong> t'a envoyé un message.</p>
      <p style="margin:0 0 16px;color:#6e6e9a;font-size:13px;">Sujet : {sujet or '(aucun)'}</p>
      <p style="margin:0 0 24px;padding:16px 20px;background-color:#222230;border-left:3px solid #87CEEB;color:#f0eeff;font-style:italic;border-radius:4px;">{message}</p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#87CEEB;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://portail.tntm.ca/dashboard" style="color:#0f0f14;text-decoration:none;font-weight:bold;font-size:14px;">Répondre dans le portail</a>
          </td>
        </tr>
      </table>
    """
    return _base_email_interne(f"💬 Message de {nom_client}", contenu)


def email_form_submission_underground_motorsport(champs):
    """Gabarit brandé Underground Motorsport (rouge/noir) — remplace le gabarit générique TNTMom pour ce client."""
    lignes = "".join(
        f"""
        <tr>
          <td style="padding:10px 16px;background-color:#1E1E1E;color:#A0A0A0;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #2A2A2A;width:35%;">{cle}</td>
          <td style="padding:10px 16px;background-color:#1E1E1E;color:#F0F0F0;font-size:14px;border-bottom:1px solid #2A2A2A;">{valeur}</td>
        </tr>"""
        for cle, valeur in champs.items()
    )
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="dark light">
  <meta name="supported-color-schemes" content="dark light">
</head>
<body style="margin:0;padding:0;background-color:#000000;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#000000;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#2A2A2A;border:1px solid #3a3a3a;border-radius:4px;overflow:hidden;max-width:600px;width:100%;">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#000000;padding:24px 32px;border-bottom:1px solid #3a3a3a;">
              <p style="margin:0;font-size:24px;font-weight:900;letter-spacing:-0.5px;font-family:'Arial Narrow',Arial,sans-serif;color:#ffffff;">
                UNDERGROUND MOTORSPORT
              </p>
            </td>
          </tr>

          <!-- CONTENU -->
          <tr>
            <td style="padding:32px;">
              <p style="margin:0 0 6px;font-size:20px;font-weight:bold;color:#ffffff;">Nouvelle demande de diagnostic 🔧</p>
              <p style="margin:0 0 24px;color:#A0A0A0;font-size:13px;">Reçue via le formulaire du site web.</p>

              <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border-radius:4px;overflow:hidden;border:1px solid #3a3a3a;">
                {lignes}
              </table>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:20px 32px;border-top:1px solid #3a3a3a;text-align:center;">
              <p style="margin:0;color:#A0A0A0;font-size:11px;">Formulaire de undergroundmotorsport.ca</p>
              <p style="margin:6px 0 0;font-size:11px;">
                <a href="https://tntm.ca" style="color:#ffffff;text-decoration:underline;">Site &amp; système par TNTMom</a>
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


def email_form_submission_nadia_ta_doula(champs):
    """Gabarit brandé Nadia ta Doula (crème/taupe, serif) — remplace le gabarit générique TNTMom pour ce client."""
    lignes = "".join(
        f"""
        <tr>
          <td style="padding:10px 16px;background-color:#FFFFFF;color:#3d3530;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #D9C4A8;width:35%;">{cle}</td>
          <td style="padding:10px 16px;background-color:#FFFFFF;color:#2c2825;font-size:14px;border-bottom:1px solid #D9C4A8;">{valeur}</td>
        </tr>"""
        for cle, valeur in champs.items()
    )
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light">
  <meta name="supported-color-schemes" content="light">
</head>
<body style="margin:0;padding:0;background-color:#FAFAFA;font-family:Georgia,'Cormorant Garamond',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#FAFAFA;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#FFFFFF;border:1px solid #D9C4A8;border-radius:4px;overflow:hidden;max-width:600px;width:100%;">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#3d3530;padding:28px 32px;text-align:center;">
              <p style="margin:0;font-size:26px;letter-spacing:0.05em;font-family:Georgia,'Cormorant Garamond',serif;color:#D9C4A8;">
                Nadia Gazaille
              </p>
              <p style="margin:4px 0 0;font-size:11px;letter-spacing:0.15em;text-transform:uppercase;font-family:Arial,Helvetica,sans-serif;color:#FAFAFA;">
                Accompagnatrice périnatale
              </p>
            </td>
          </tr>

          <!-- CONTENU -->
          <tr>
            <td style="padding:32px;font-family:Arial,Helvetica,sans-serif;">
              <p style="margin:0 0 6px;font-size:20px;font-weight:bold;color:#3d3530;font-family:Georgia,'Cormorant Garamond',serif;">Nouvelle demande de consultation 🌙</p>
              <p style="margin:0 0 24px;color:#3d3530;font-size:13px;">Reçue via le formulaire du site web.</p>

              <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border-radius:4px;overflow:hidden;border:1px solid #D9C4A8;">
                {lignes}
              </table>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:20px 32px;border-top:1px solid #D9C4A8;text-align:center;font-family:Arial,Helvetica,sans-serif;">
              <p style="margin:0;color:#3d3530;font-size:11px;">Formulaire de nadiatadoula.ca</p>
              <p style="margin:6px 0 0;font-size:11px;">
                <a href="https://tntm.ca" style="color:#3d3530;text-decoration:underline;">Site &amp; système par TNTMom</a>
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


def email_confirmation_nadia_ta_doula(prenom):
    """Confirmation envoyée au client qui remplit le formulaire de contact de Nadia ta Doula."""
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light">
  <meta name="supported-color-schemes" content="light">
</head>
<body style="margin:0;padding:0;background-color:#FAFAFA;font-family:Georgia,'Cormorant Garamond',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#FAFAFA;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#FFFFFF;border:1px solid #D9C4A8;border-radius:4px;overflow:hidden;max-width:600px;width:100%;">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#3d3530;padding:28px 32px;text-align:center;">
              <p style="margin:0;font-size:26px;letter-spacing:0.05em;font-family:Georgia,'Cormorant Garamond',serif;color:#D9C4A8;">
                Nadia Gazaille
              </p>
              <p style="margin:4px 0 0;font-size:11px;letter-spacing:0.15em;text-transform:uppercase;font-family:Arial,Helvetica,sans-serif;color:#FAFAFA;">
                Accompagnatrice périnatale
              </p>
            </td>
          </tr>

          <!-- CONTENU -->
          <tr>
            <td style="padding:32px;font-family:Arial,Helvetica,sans-serif;">
              <p style="margin:0 0 6px;font-size:20px;font-weight:bold;color:#3d3530;font-family:Georgia,'Cormorant Garamond',serif;">Merci{f' {prenom}' if prenom else ''} ! 🌙</p>
              <p style="margin:0 0 20px;color:#3d3530;font-size:14px;line-height:1.6;">
                J'ai bien reçu ta demande et je te réponds personnellement dans les 24 à 48h.
                En attendant, n'hésite pas si tu as d'autres questions.
              </p>
              <p style="margin:0;color:#3d3530;font-size:13px;font-style:italic;">À très bientôt !</p>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:20px 32px;border-top:1px solid #D9C4A8;text-align:center;font-family:Arial,Helvetica,sans-serif;">
              <p style="margin:0;color:#3d3530;font-size:11px;">Nadia ta Doula — nadiatadoula.ca</p>
              <p style="margin:6px 0 0;font-size:11px;">
                <a href="https://tntm.ca" style="color:#3d3530;text-decoration:underline;">Site &amp; système par TNTMom</a>
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


def email_confirmation_underground_motorsport(nom):
    """Confirmation envoyée au client qui remplit le formulaire de contact de Underground Motorsport."""
    return f"""
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="dark light">
  <meta name="supported-color-schemes" content="dark light">
</head>
<body style="margin:0;padding:0;background-color:#000000;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#000000;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color:#2A2A2A;border:1px solid #3a3a3a;border-radius:4px;overflow:hidden;max-width:600px;width:100%;">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#000000;padding:24px 32px;border-bottom:1px solid #3a3a3a;">
              <p style="margin:0;font-size:24px;font-weight:900;letter-spacing:-0.5px;font-family:'Arial Narrow',Arial,sans-serif;color:#ffffff;">
                UNDERGROUND MOTORSPORT
              </p>
            </td>
          </tr>

          <!-- CONTENU -->
          <tr>
            <td style="padding:32px;">
              <p style="margin:0 0 6px;font-size:20px;font-weight:bold;color:#ffffff;">Merci{f' {nom}' if nom else ''} ! 🔧</p>
              <p style="margin:0 0 20px;color:#F0F0F0;font-size:14px;line-height:1.6;">
                On a bien reçu ta demande de diagnostic. On te recontacte sous 6 à 12h.
              </p>
              <p style="margin:0;color:#A0A0A0;font-size:13px;">À bientôt !</p>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:20px 32px;border-top:1px solid #3a3a3a;text-align:center;">
              <p style="margin:0;color:#A0A0A0;font-size:11px;">Underground Motorsport — undergroundmotorsport.ca</p>
              <p style="margin:6px 0 0;font-size:11px;">
                <a href="https://tntm.ca" style="color:#ffffff;text-decoration:underline;">Site &amp; système par TNTMom</a>
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


def email_form_submission_client(nom_site, champs):
    lignes = "".join(
        f'<p style="margin:0 0 10px;color:#6e6e9a;font-size:13px;">{cle} : '
        f'<strong style="color:#f0eeff;">{valeur}</strong></p>'
        for cle, valeur in champs.items()
    )
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#d94fbd;">Nouvelle demande — {nom_site} 📬</p>
      <p style="margin:0 0 24px;color:#6e6e9a;font-size:13px;">Reçue via le formulaire de votre site web.</p>
      {lignes}
    """
    return base_email(contenu)


def email_lead_naomie(nom, email_client, message):
    email_ligne = f'<p style="margin:0 0 4px;color:#6e6e9a;font-size:13px;">Courriel : <strong style="color:#f0eeff;">{email_client}</strong></p>' if email_client else ''
    contenu = f"""
      <p style="margin:0 0 8px;">Nouveau lead depuis le formulaire de contact de tntm.ca.</p>
      <p style="margin:0 0 4px;color:#6e6e9a;font-size:13px;">Nom : <strong style="color:#f0eeff;">{nom}</strong></p>
      {email_ligne}
      <p style="margin:16px 0 24px;padding:16px 20px;background-color:#222230;border-left:3px solid #87CEEB;color:#f0eeff;font-style:italic;border-radius:4px;">{message}</p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#87CEEB;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://portail.tntm.ca/leads" style="color:#0f0f14;text-decoration:none;font-weight:bold;font-size:14px;">Voir les leads</a>
          </td>
        </tr>
      </table>
    """
    return _base_email_interne(f"🔔 Nouveau lead — {nom}", contenu)


def email_commentaire_fichier_client(nom_client, nom_fichier, commentaire):
    contenu = f"""
      <p style="margin:0 0 8px;"><strong style="color:#f0eeff;">{nom_client}</strong> a commenté un fichier.</p>
      <p style="margin:0 0 16px;color:#6e6e9a;font-size:13px;">Fichier : {nom_fichier}</p>
      <p style="margin:0 0 24px;padding:16px 20px;background-color:#222230;border-left:3px solid #87CEEB;color:#f0eeff;font-style:italic;border-radius:4px;">« {commentaire} »</p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#87CEEB;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://portail.tntm.ca/dashboard" style="color:#0f0f14;text-decoration:none;font-weight:bold;font-size:14px;">Voir le fichier</a>
          </td>
        </tr>
      </table>
    """
    return _base_email_interne(f"💬 Commentaire de {nom_client}", contenu)


def email_formulaire_naomie(nom_client, titre_formulaire):
    contenu = f"""
      <p style="margin:0 0 8px;"><strong style="color:#f0eeff;">{nom_client}</strong> vient de remplir un formulaire.</p>
      <p style="margin:0 0 24px;padding:16px 20px;background-color:#222230;border-left:3px solid #87CEEB;color:#f0eeff;border-radius:4px;">{titre_formulaire}</p>
      <table cellpadding="0" cellspacing="0" style="margin:0 0 32px;">
        <tr>
          <td style="background-color:#87CEEB;border-radius:6px;padding:12px 28px;text-align:center;">
            <a href="https://portail.tntm.ca/dashboard" style="color:#0f0f14;text-decoration:none;font-weight:bold;font-size:14px;">Voir les réponses</a>
          </td>
        </tr>
      </table>
    """
    return _base_email_interne(f"📋 Formulaire rempli — {titre_formulaire}", contenu)



def email_facture(nom_client, numero, contrat_nom, description, montant, date_emission, statut):
    contenu = f"""
      <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:#d94fbd;">Ta facture est prête, {nom_client} 🧾</p>
      <p style="margin:0 0 24px;color:#6e6e9a;font-size:13px;">Voici le détail de ta facture.</p>

      <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 32px;border-collapse:collapse;font-size:14px;border:1px solid #2a2a3a;border-radius:8px;overflow:hidden;">
        <tr>
          <td style="padding:12px 16px;background-color:#1a1a24;color:#6e6e9a;width:40%;border-bottom:1px solid #2a2a3a;">Projet</td>
          <td style="padding:12px 16px;background-color:#1a1a24;color:#f0eeff;border-bottom:1px solid #2a2a3a;">{contrat_nom}</td>
        </tr>
        <tr>
          <td style="padding:12px 16px;background-color:#222230;color:#6e6e9a;border-bottom:1px solid #2a2a3a;">Description</td>
          <td style="padding:12px 16px;background-color:#222230;color:#f0eeff;border-bottom:1px solid #2a2a3a;">{description}</td>
        </tr>
        <tr>
          <td style="padding:12px 16px;background-color:#1a1a24;color:#6e6e9a;border-bottom:1px solid #2a2a3a;">Montant</td>
          <td style="padding:12px 16px;background-color:#1a1a24;font-size:16px;font-weight:bold;color:#d94fbd;border-bottom:1px solid #2a2a3a;">{montant}</td>
        </tr>
        <tr>
          <td style="padding:12px 16px;background-color:#222230;color:#6e6e9a;border-bottom:1px solid #2a2a3a;">Date d'émission</td>
          <td style="padding:12px 16px;background-color:#222230;color:#f0eeff;border-bottom:1px solid #2a2a3a;">{date_emission or '—'}</td>
        </tr>
        <tr>
          <td style="padding:12px 16px;background-color:#1a1a24;color:#6e6e9a;">Statut</td>
          <td style="padding:12px 16px;background-color:#1a1a24;color:#87CEEB;font-weight:bold;">{statut}</td>
        </tr>
      </table>

      <p style="margin:0;color:#6e6e9a;font-size:12px;">Des questions ? Réponds directement à ce courriel.</p>
    """
    return base_email(contenu)
