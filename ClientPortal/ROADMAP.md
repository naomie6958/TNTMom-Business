# 🚀 ROADMAP CLIENT PORTAL — V3.0
> Analyse complète — 2026-06-25
> Phases 1 + 2 complètes. Ce roadmap couvre les outils internes, le portfolio manager et les fonctionnalités business.

---

## ✅ Phases complétées

### Phase 1 — Restructuration Blueprint
- [x] `routes_auth.py` · `routes_admin_clients.py` · `routes_admin_compta.py` · `routes_admin_tools.py`
- [x] Nettoyage `app.py`

### Phase 2 — Logique & Robustesse
- [x] Emails asynchrones (threading)
- [x] Soft delete CRM
- [x] Export CSV comptabilité
- [x] Validation JSON globale
- [x] Forms AJAX · Bannière vue client · FAB mobile · Filtres JS · Skeleton loading
- [x] Générateur PDF (WeasyPrint)
- [x] Journal d'activité client · Commentaires sur fichiers · Templates contrats

---

## 🟠 Phase 3 — Outils Naomie (Bill/Nao)

### 3.1 Budget Bill — Revenus du ménage
- [ ] **Table `budget_revenus`** — ajouter une table pour les revenus : source, montant, date, mois
- [ ] **UI revenus** dans `bill/budget.html` — section revenus avec ajout/suppression
- [ ] **Solde mensuel** — afficher revenus - dépenses = solde en bas de page
- [ ] **Route API** `GET/POST/DELETE /api/budget-revenu`

### 3.2 Comptabilité Naomie — Améliorations
- [ ] **Filtre par période** dans heures_rapports.html (actuellement vue globale seulement)
- [ ] **Résumé fiscal annuel** — revenus totaux + dépenses déductibles + bénéfice net par année

---

## 🔵 Phase 4 — Portfolio Manager (outil tntm.ca)

> Gérer les cartes de la galerie tntm.ca directement depuis le portail admin.
> Approche : les cartes sont stockées en DB dans le portail. tntm.ca fetch depuis `portail.tntm.ca/api/projets` au lieu du fichier JSON statique.

### 4.1 Back-end
- [ ] **Table `portfolio_projets`** — id, nom, tagline, description, tags (JSON), statut, couleur, image_url, link, ordre, actif
- [ ] **Route API publique** `GET /api/projets` — retourne le JSON des projets actifs (remplace `data/projets.json` sur tntm.ca)
- [ ] **Routes admin CRUD** — créer / modifier / archiver / réordonner les cartes
- [ ] **Seed initial** — importer les 4 projets existants au déploiement

### 4.2 Interface admin
- [ ] **Page `/portfolio`** dans le portail admin — liste des cartes avec statut, ordre drag-and-drop
- [ ] **Formulaire création/édition** — nom, tagline, description, tags, statut, couleur (picker), lien, image
- [ ] **Prévisualisation live** — aperçu de la carte telle qu'elle apparaît sur tntm.ca
- [ ] **Upload image** — depuis le portail directement (utilise le système d'upload existant)

### 4.3 tntm.ca — Connexion live
- [ ] **Modifier `script.js`** — changer `fetch('data/projets.json')` pour `fetch('https://portail.tntm.ca/api/projets')`
- [ ] **Fallback** — si l'API ne répond pas, afficher un message gracieux
- [ ] **CORS** — activer sur la route `/api/projets` dans Flask

---

## 🟡 Phase 5 — Business

- [ ] **Paiement Stripe** — bouton "Payer en ligne" sur les factures du portail client
- [ ] **Relance automatique** — email automatique si une facture reste impayée après X jours
- [ ] **Tableau de bord revenus** — graphique mensuel des entrées d'argent (dépenses vs revenus vs objectif)

---

## ✅ Ordre suggéré

| Priorité | Item | Effort |
|---|---|---|
| 1 | Budget Bill — revenus du ménage (3.1) | ~1h30 |
| 2 | Portfolio Manager back-end + API (4.1) | ~1h |
| 3 | Interface admin portfolio (4.2) | ~1h30 |
| 4 | Connexion tntm.ca live (4.3) | ~30 min |
| 5 | Filtres comptabilité (3.2) | ~45 min |
| 6 | Stripe (5) | ~2h |
