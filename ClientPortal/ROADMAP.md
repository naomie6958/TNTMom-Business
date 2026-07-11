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
- [x] **Table `budget_revenus`** — ajouter une table pour les revenus : source, montant, date, mois
- [x] **UI revenus** dans `bill/budget.html` — section revenus avec ajout/suppression
- [x] **Solde mensuel** — afficher revenus - dépenses = solde en bas de page
- [x] **Route API** `GET/POST/DELETE /api/budget-revenu`

### 3.2 Comptabilité Naomie — Améliorations
- [x] **Filtre par période** dans heures_rapports.html ✅ 2026-07-11 (formulaire GET debut/fin, appliqué aux 3 requêtes)
- [x] **Résumé fiscal annuel** — revenus totaux + dépenses déductibles + bénéfice net par année

---

## 🔵 Phase 4 — Portfolio Manager (outil tntm.ca)

> Gérer les cartes de la galerie tntm.ca directement depuis le portail admin.
> Approche : les cartes sont stockées en DB dans le portail. tntm.ca fetch depuis `portail.tntm.ca/api/projets` au lieu du fichier JSON statique.

### 4.1 Back-end ✅ 2026-06-28
- [x] **Table `portfolio_projets`** — id, nom, tagline, description, tags (JSON), statut, couleur, image_url, link, ordre, actif
- [x] **Route API publique** `GET /api/public/projets` — retourne le JSON des projets actifs (CORS activé)
- [x] **Routes admin CRUD** — créer / modifier / archiver / réordonner les cartes
- [x] **Seed initial** — 4 projets seedés au déploiement

### 4.2 Interface admin ✅ 2026-06-28
- [x] **Page `/portfolio`** dans le portail admin — liste des cartes avec statut, couleur, ordre, visible
- [x] **Formulaire création/édition** — nom, tagline, description, tags, statut, couleur (9 options), lien, image_url, ordre
- [x] **Suppression** — modale de confirmation stylée (pas de confirm() natif)
- [x] **Prévisualisation live** — aperçu de la carte telle qu'elle apparaît sur tntm.ca
- [ ] **Upload image** — depuis le portail directement (utilise le système d'upload existant)

### 4.3 tntm.ca — Connexion live
- [x] **Modifier `script.js`** — changer `fetch('data/projets.json')` pour `fetch('https://portail.tntm.ca/api/projets')`
- [x] **Fallback** — si l'API ne répond pas, afficher un message gracieux
- [x] **CORS** — activer sur la route `/api/projets` dans Flask

---

## 🟡 Phase 5 — Business

- [ ] **Paiement Stripe** — bouton "Payer en ligne" sur les factures du portail client
- [ ] **Relance automatique** — email automatique si une facture reste impayée après X jours
- [ ] **Tableau de bord revenus** — graphique mensuel des entrées d'argent (dépenses vs revenus vs objectif)

---

## 🗑️ Nettoyage — À retirer

- [ ] **Système de messagerie interne** — retirer complètement, jugé inutile (redondant avec les outils de messagerie déjà utilisés au quotidien) — 2026-07-09

---

## ✅ Ordre suggéré (restants — mis à jour 2026-07-11)

| Priorité | Item | Effort |
|---|---|---|
| 1 | Statut « Disponible » tntm.ca géré depuis l'admin (voir ROADMAP-MASTER) | ~1h |
| 2 | Retrait de la messagerie interne (Nettoyage) | ~30 min |
| 3 | Upload image portfolio (4.2) | ~45 min |
| 4 | Stripe (5) | ~2h, session dédiée |

> ⚠️ Note restructuration (plan cowork Phases B/C — templates + app.py) : `migrate_db.py` doit **rester à la racine** (le Procfile le lance au démarrage — l'avoir déplacé a causé un 502 en prod le 2026-07-11). À corriger avant tout re-déplacement : faire importer `DB_PATH` depuis `database.py`.
