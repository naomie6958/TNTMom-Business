# 🚀 ROADMAP V3.0 — tntm.ca (Site Vitrine)
> Analyse complète — 2026-06-24
> V1 + V2 complètes. Ce roadmap couvre les correctifs urgents et les améliorations futures.

---

## 🔴 1. Contenu périmé (à corriger en priorité)

- [ ] **`data/projets.json` — 3 erreurs**
  - Chopper Burger : tag `"Render"` → `"Railway"` ; description dit "domaine custom à venir" → retirer (jamais acheté)
  - ClientPortal : tag `"PythonAnywhere"` → `"Railway"`
  - Family Dashboard : `"statut": "en-cours"` → `"live"` (déployé familydashboard.tntm.ca depuis 2026-06-23)

- [ ] **`clientportal.html` — stack périmée**
  - Stack affiche `"PythonAnywhere"` → corriger pour `"Railway"`

- [ ] **`familydashboard.html` — statut périmé**
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

- [ ] **Liens sociaux dans le footer**
  - GitHub (`github.com/naomie6958`) et/ou LinkedIn
  - Actuellement footer = seulement Buy me a coffee + copyright

---

## 🟡 3. UX & Contenu

- [x] **Screenshots mises à jour (2026-06-27)**
  - ClientPortal : 3 nouvelles captures dans `images/Screenshots/2026-06-27/`
  - Family Dashboard : 2 nouvelles captures dans `images/Screenshots/2026-06-27/`

- [ ] **`nao-scheduler.html` et `sobriety-tracker.html`**
  - Ces pages sont accessibles publiquement (pas dans la nav mais indexables)
  - Décision à prendre : ajouter `noindex` en meta, protéger par login, ou supprimer du repo

- [x] **Formulaire contact — étendu (2026-07-07)**
  - Ajout téléphone (optionnel), préférence de recontact (radio), type de projet (select), budget approximatif (optionnel)
  - JS de soumission mis à jour pour envoyer tous les nouveaux champs
  - [ ] **Reste à faire :** styliser les boutons radio (apparence par défaut du navigateur actuellement, pas le style TNTM — cacher l'input natif + dessiner un cercle custom via `::before`/`::after` sur le label)

- [ ] **Formulaire contact — courriel de fallback**
  - En cas d'erreur API, message dit `naomiemt@tntm.ca` — vérifier que c'est le bon courriel public

- [ ] **Page d'accueil — badge "Disponible"**
  - `<span class="disponible-badge">● Disponible pour de nouveaux projets</span>` est hardcodé
  - Quand tu seras à pleine capacité, penser à le rendre dynamique ou facile à changer

---

## 🔵 4. Technique

- [ ] **URL portail dans `clientportal.html`**
  - Lien CTA : `https://portail.tntm.ca/portail/login` → vérifier si l'URL est correcte (devrait peut-être être `/login` directement)

- [ ] **`components.js` — chemin absolu `/js/components.js`**
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
