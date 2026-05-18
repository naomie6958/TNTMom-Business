# ================================================================
# LOGIQUE COMPTABILITÉ — TNTMom (version SQLite / Flask)
# Ce module est importé par app.py dans la route /comptabilite.
# Il contient les 5 fonctions de logique financière.
# ================================================================

from datetime import date
from database import get_db


# ── FONCTION 5 : DÉTECTION DES RETARDS ──────────────────────────

def verifier_et_mettre_retards():
    """
    Parcourt toutes les factures avec statut 'envoyée' qui ont une
    date_echeance dépassée, et les met automatiquement à 'en retard'
    en base de données.

    Appelée EN PREMIER dans la route — elle met à jour les statuts
    avant que les autres calculs lisent les données.

    Retourne une liste d'alertes (jalons en retard détectés).
    """
    conn = get_db()
    aujourd_hui = date.today().isoformat()  # Format SQLite : 'YYYY-MM-DD'

    # On cherche les factures envoyées dont l'échéance est passée
    # (on exclut les clients démo pour ne pas fausser les chiffres)
    retardees = conn.execute('''
        SELECT f.id, f.montant, f.milestone_titre, f.description,
               f.date_echeance, c.nom as client_nom
        FROM factures f
        JOIN clients c ON c.id = f.client_id
        WHERE f.statut = 'envoyée'
          AND f.date_echeance IS NOT NULL
          AND f.date_echeance < ?
          AND c.demo = 0
    ''', (aujourd_hui,)).fetchall()

    alertes = []
    for f in retardees:
        # Mise à jour permanente en DB — le statut sera visible dans le tableau
        conn.execute(
            "UPDATE factures SET statut = 'en retard' WHERE id = ?",
            (f['id'],)
        )
        echeance = date.fromisoformat(f['date_echeance'])
        jours_retard = (date.today() - echeance).days

        alertes.append({
            'client': f['client_nom'],
            'jalon': f['milestone_titre'] or f['description'] or '—',
            'montant': float(f['montant'] or 0),
            'jours_retard': jours_retard,
            'facture_id': f['id'],
        })

    conn.commit()
    conn.close()
    return alertes


# ── FONCTION 3 : TAX TRACKER ─────────────────────────────────────

def calculer_tax_tracker(seuil=30_000.0):
    """
    Calcule le chiffre d'affaires total facturé au client (peu importe
    si payé ou non) et alerte si on approche du seuil TPS/TVQ.

    Règle fiscale : les statuts 'envoyée', 'en retard' et 'payée'
    comptent tous. Seules les factures jamais émises seraient exclues,
    mais dans notre DB tout ce qui est créé est déjà "émis".
    """
    conn = get_db()
    row = conn.execute('''
        SELECT COALESCE(SUM(f.montant), 0) as total
        FROM factures f
        JOIN clients c ON c.id = f.client_id
        WHERE f.statut IN ('envoyée', 'en retard', 'payée')
          AND c.demo = 0
    ''').fetchone()
    conn.close()

    total = float(row['total'])
    pourcentage = min((total / seuil) * 100, 100)

    return {
        'total_facture': total,
        'seuil': seuil,
        'pourcentage_vers_seuil': round(pourcentage, 1),
        'alerte_taxes': total >= seuil * 0.80,  # Avertissement dès 80%
        'seuil_depasse': total >= seuil,         # Inscription obligatoire
    }


# ── FONCTION 4b : TOTAL DES DÉPENSES ────────────────────────────

def calculer_total_depenses():
    """
    Additionne toutes les dépenses enregistrées, regroupées par catégorie.
    Retourne le total global et un dict {catégorie: montant}.
    """
    conn = get_db()

    rows = conn.execute('''
        SELECT categorie, SUM(montant) as total
        FROM depenses
        GROUP BY categorie
        ORDER BY categorie
    ''').fetchall()

    total_row = conn.execute(
        'SELECT COALESCE(SUM(montant), 0) as total FROM depenses'
    ).fetchone()

    conn.close()

    return {
        'total': float(total_row['total']),
        'par_categorie': {r['categorie']: float(r['total']) for r in rows},
    }


# ── FONCTION 2 : PROVISION FISCALE ──────────────────────────────

def calculer_provision_fiscale(taux_provision=0.25):
    """
    Calcule combien mettre de côté pour les impôts, sur la base
    du REVENU NET (factures payées - dépenses d'entreprise).

    LOGIQUE :
      Revenu brut  = toutes les factures au statut 'payée' (argent reçu)
      Dépenses     = tout ce qui est dans la table 'depenses'
      Revenu net   = Revenu brut - Dépenses  (le "profit" réel)
      Provision    = Revenu net × 25%         → compte épargne fiscal
      Disponible   = Revenu net - Provision   → ton salaire net

    Pourquoi sur le net? Les impôts canadiens s'appliquent sur le profit,
    pas le chiffre d'affaires brut. Calculer sur le net est plus précis.
    """
    conn = get_db()
    row = conn.execute('''
        SELECT COALESCE(SUM(f.montant), 0) as total
        FROM factures f
        JOIN clients c ON c.id = f.client_id
        WHERE f.statut = 'payée'
          AND c.demo = 0
    ''').fetchone()
    conn.close()

    revenu_brut = float(row['total'])
    info_dep = calculer_total_depenses()
    total_depenses = info_dep['total']

    # max(0, ...) évite une provision négative si les dépenses dépassent les revenus
    revenu_net = max(0.0, revenu_brut - total_depenses)
    montant_provision = revenu_net * taux_provision
    montant_disponible = revenu_net - montant_provision

    return {
        'revenu_brut': revenu_brut,
        'total_depenses': total_depenses,
        'revenu_net': revenu_net,
        'taux_provision_pct': int(taux_provision * 100),
        'montant_provision': montant_provision,   # → compte épargne fiscal
        'montant_disponible': montant_disponible, # → ton compte courant
    }
