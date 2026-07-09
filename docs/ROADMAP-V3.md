# 🚀 ROADMAP V3.0 — tntm.ca (Site Vitrine)
> Analyse complète — 2026-06-24
> V1 + V2 complètes. Ce roadmap couvre les correctifs urgents et les améliorations futures.

---

## 🔴 1. Contenu périmé (à corriger en priorité)

- [x] **`data/projets.json` — 3 erreurs** *(déjà résolu, confirmé lors de l'audit du 2026-07-08)*
  - Chopper Burger : tag `"Render"` → `"Railway"` ; description dit "domaine custom à venir" → retirer (jamais acheté)
  - ClientPortal : tag `"PythonAnywhere"` → `"Railway"`
  - Family Dashboard : `"statut": "en-cours"` → `"live"` (déployé familydashboard.tntm.ca depuis 2026-06-23)

- [x] **`clientportal.html` — stack périmée** *(déjà résolu, confirmé 2026-07-08)*
  - Stack affiche `"PythonAnywhere"` → corriger pour `"Railway"`

- [x] **`familydashboard.html` — statut périmé** *(déjà résolu, confirmé 2026-07-08)*
  - Badge `"◐ En cours — développement actif"` → `"● Live — Usage privé"` (pas de lien public — app familiale avec données enfants)

- [x] **`about.html` — skills périmées**
  - Section Outils : `"PythonAnywhere"` → `"Railway"`
  - Ajouter `"Sass/SCSS"` (Module 05 complété) aux compétences Frontend
  - Second témoignage placeholder `"À venir / Prochain projet"` → retirer ou remplir

---

## 🟠 2. Fonctionnalités manquantes

- [x] **Underground Motorsport dans la galerie**
  - Ajouter entrée dans `projets.json` (statut : "en-cours", couleur : "vert")
  - Ajouter dans la nav dropdown de `components.js`
  - Créer `undergroundmotorsport.html` (fiche projet) quand le projet est plus avancé

- [x] **Family Dashboard — lien live dans la nav**
  - `components.js` nav dropdown : lien pointe maintenant vers `https://familydashboard.tntm.ca`

- [x] **Liens sociaux dans le footer** *(déjà résolu, confirmé 2026-07-08 — Facebook + GitHub + LinkedIn présents dans components.js)*
  - GitHub (`github.com/naomie6958`) et/ou LinkedIn
  - Actuellement footer = seulement Buy me a coffee + copyright

---

## 🟡 3. UX & Contenu

- [x] **Screenshots mises à jour (2026-06-27)**
  - ClientPortal : 3 nouvelles captures dans `images/Screenshots/2026-06-27/`
  - Family Dashboard : 2 nouvelles captures dans `images/Screenshots/2026-06-27/`

- [x] **`nao-scheduler.html` et `sobriety-tracker.html`** *(résolu par suppression, confirmé 2026-07-08 — les fichiers n'existent plus dans docs/)*
  - Ces pages sont accessibles publiquement (pas dans la nav mais indexables)
  - Décision à prendre : ajouter `noindex` en meta, protéger par login, ou supprimer du repo

- [x] **Formulaire contact — étendu (2026-07-07)**
  - Ajout téléphone (optionnel), préférence de recontact (radio), type de projet (select), budget approximatif (optionnel)
  - JS de soumission mis à jour pour envoyer tous les nouveaux champs
  - [x] **Reste à faire :** styliser les boutons radio *(déjà fait, confirmé 2026-07-08 — retravaillé encore cette session : cases 14px, plus de padding hérité qui les faisait déborder, empilées verticalement)*

- [x] **Formulaire contact — courriel de fallback** *(vérifié 2026-07-08 — `naomiemt@tntm.ca` est la vraie adresse, testée fonctionnelle via ImprovMX, voir ROADMAP-MASTER.md)*
  - En cas d'erreur API, message dit `naomiemt@tntm.ca` — vérifier que c'est le bon courriel public

- [ ] **Page d'accueil — badge "Disponible"** *(décision 2026-07-09 : géré depuis ClientPortal, pas depuis tntm.ca directement — voir backlog ClientPortal dans ROADMAP-MASTER.md)*
  - `<span class="disponible-badge">● Disponible pour de nouveaux projets</span>` est hardcodé
  - Plan : petit champ statut côté admin ClientPortal + route publique (ex: `/api/public/statut`), tntm.ca va chercher la valeur au chargement — même pattern que la galerie de projets (`/api/public/projets`)

---

## 🔵 4. Technique

- [x] **URL portail dans `clientportal.html`** *(vérifié 2026-07-08 — `/portail/login` utilisé de façon cohérente à 3 endroits, semble volontaire)*
  - Lien CTA : `https://portail.tntm.ca/portail/login` → vérifier si l'URL est correcte (devrait peut-être être `/login` directement)

- [x] **`components.js` — chemin absolu `/js/components.js`** *(pas de changement nécessaire — utiliser Live Server en local)*
  - Fonctionne parfaitement sur GitHub Pages mais casse si tu testes en local (file://)
  - Solution : utiliser Live Server en local, pas de changement de code nécessaire

- [x] **Menu nav ouvert par défaut au chargement**
  - `components.js` ligne 45 : `if (isDesktop() && localStorage.getItem('tntmNavOpen') === 'true')` → si l'utilisateur avait laissé le menu ouvert, il reste ouvert au prochain chargement
  - Fix : retirer la persistance localStorage du menu, ou forcer `closed` au chargement de la homepage

---

## ✅ Ordre suggéré

| Priorité | Item | Effort |
|---|---|---|
| 1 | projets.json — 3 corrections | ~10 min |
| 2 | familydashboard.html — statut + lien live | ~10 min |
| 3 | clientportal.html — stack Railway | ~5 min |
| 4 | about.html — skills + témoignage | ~15 min |
| 5 | Underground Motorsport dans galerie | ~20 min |
| 6 | Screenshots récentes | ~30 min |
| 7 | Liens sociaux footer | ~15 min |
| 8 | nao-scheduler / sobriety — décision | ~10 min |
| 9 | Badge "Disponible" dynamique | ~30 min |
