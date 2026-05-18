# ================================================================
# LOGIQUE COMPTABILITÉ — TNTMom (version SQLite / Flask)
# Ce module est importé par app.py dans la route /comptabilite.
# Il contient les 5 fonctions de logique financière.
#
# Toutes les fonctions de calcul acceptent un paramètre :
#   inclure_demo (bool, défaut False)
#   False → exclut le client démo (id_client 4, c.demo = 1) → vrais chiffres
#   True  → inclut tous les clients → mode présentation visuelle
# ================================================================

from datetime import date
from database import get_db


# ── UTILITAIRE INTERNE ────────────────────────────────────────────

def _clause_demo(inclure_demo):
    """Retourne le fragment SQL à ajouter dans un WHERE pour filtrer le démo."""
    return '' if inclure_demo else 'AND c.demo = 0'


# ── FONCTION 5 : DÉTECTION DES RETARDS ──────────────────────────

def verifier_et_mettre_retards(inclure_demo=False):
    """
    Met à jour en DB les factures 'envoyée' dont l'échéance est dépassée
    → statut 'en retard'. TOUJOURS sur les vrais clients uniquement
    (la mise à jour ne touche jamais les données démo).

    Retourne la liste des alertes à afficher (selon inclure_demo).
    """
    conn = get_db()
    aujourd_hui = date.today().isoformat()

    # Mise à jour permanente — jamais sur le client démo
    conn.execute('''
        UPDATE factures SET statut = 'en retard'
        WHERE statut = 'envoyée'
          AND date_echeance IS NOT NULL
          AND date_echeance < ?
          AND client_id IN (SELECT id FROM clients WHERE demo = 0)
    ''', (aujourd_hui,))
    conn.commit()

    # Alertes affichées — respecte le mode démo
    retardees = conn.execute(f'''
        SELECT f.id, f.montant, f.milestone_titre, f.description,
               f.date_echeance, c.nom as client_nom
        FROM factures f
        JOIN clients c ON c.id = f.client_id
        WHERE f.statut IN ('envoyée', 'en retard')
          AND f.date_echeance IS NOT NULL
          AND f.date_echeance < ?
          {_clause_demo(inclure_demo)}
        ORDER BY f.date_echeance ASC
    ''', (aujourd_hui,)).fetchall()
    conn.close()

    alertes = []
    for f in retardees:
        echeance = date.fromisoformat(f['date_echeance'])
        jours_retard = (date.today() - echeance).days
        alertes.append({
            'client': f['client_nom'],
            'jalon': f['milestone_titre'] or f['description'] or '—',
            'montant': float(f['montant'] or 0),
            'jours_retard': jours_retard,
            'facture_id': f['id'],
        })

    return alertes


# ── FONCTION 3 : TAX TRACKER ─────────────────────────────────────

def calculer_tax_tracker(seuil=30_000.0, inclure_demo=False):
    """
    Calcule le chiffre d'affaires total facturé et alerte si on approche
    du seuil TPS/TVQ (30 000 $ par défaut).

    Règle fiscale : statuts 'envoyée', 'en retard' et 'payée' comptent tous.
    """
    conn = get_db()
    row = conn.execute(f'''
        SELECT COALESCE(SUM(f.montant), 0) as total
        FROM factures f
        JOIN clients c ON c.id = f.client_id
        WHERE f.statut IN ('envoyée', 'en retard', 'payée')
          {_clause_demo(inclure_demo)}
    ''').fetchone()
    conn.close()

    total = float(row['total'])
    pourcentage = min((total / seuil) * 100, 100)

    return {
        'total_facture': total,
        'seuil': seuil,
        'pourcentage_vers_seuil': round(pourcentage, 1),
        'alerte_taxes': total >= seuil * 0.80,   # Avertissement dès 80 %
        'seuil_depasse': total >= seuil,          # Inscription obligatoire
    }


# ── FONCTION 4b : TOTAL DES DÉPENSES ────────────────────────────

def calculer_total_depenses():
    """
    Additionne toutes les dépenses enregistrées, regroupées par catégorie.
    Les dépenses ne sont pas liées à un client → pas de filtre démo.
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

def calculer_provision_fiscale(taux_provision=0.25, inclure_demo=False):
    """
    Calcule combien mettre de côté pour les impôts, sur la base
    du REVENU NET (factures payées - dépenses d'entreprise).

    LOGIQUE :
      Revenu brut  = factures au statut 'payée'
      Dépenses     = table 'depenses' (pas de filtre client)
      Revenu net   = Revenu brut - Dépenses
      Provision    = Revenu net × 25%   → compte épargne fiscal
      Disponible   = Revenu net - Provision
    """
    conn = get_db()
    row = conn.execute(f'''
        SELECT COALESCE(SUM(f.montant), 0) as total
        FROM factures f
        JOIN clients c ON c.id = f.client_id
        WHERE f.statut = 'payée'
          {_clause_demo(inclure_demo)}
    ''').fetchone()
    conn.close()

    revenu_brut = float(row['total'])
    info_dep = calculer_total_depenses()
    total_depenses = info_dep['total']

    revenu_net = max(0.0, revenu_brut - total_depenses)
    montant_provision = revenu_net * taux_provision
    montant_disponible = revenu_net - montant_provision

    return {
        'revenu_brut': revenu_brut,
        'total_depenses': total_depenses,
        'revenu_net': revenu_net,
        'taux_provision_pct': int(taux_provision * 100),
        'montant_provision': montant_provision,
        'montant_disponible': montant_disponible,
    }
