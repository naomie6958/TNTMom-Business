# 🚀 ROADMAP V2.0 — tntm.ca (Site Vitrine)

## 📍 Milestone 1 : Performance & Accessibilité (Quick Wins)
*Des petits ajustements invisibles mais qui plaisent énormément à Google.*
- [x] **Attributs `loading="lazy"`** : Déjà parfaitement configuré sur les images non visibles au chargement.
- [x] **Accessibilité du menu mobile** : Ajout du tag `aria-label` pour les lecteurs d'écran.
- [x] **Page 404 Custom** : Création d'une page d'erreur personnalisée avec le design "Chaos introuvable".
- [x] **Icônes Apple (Touch Icons)** : Ajout des balises `<link rel="apple-touch-icon">` pour l'enregistrement sur écran d'accueil iOS.
- [x] **Fix UX** : Menu de navigation mobile/desktop fermé par défaut au premier chargement.

## 📍 Milestone 2 : Résilience & Micro-interactions (UX)
*Améliorer ce qu'il se passe quand les choses "chargent" ou "échouent".*
- [x] **Skeleton Loading (Tarifs)** : Ajout d'une animation d'attente (fausses cartes) le temps que l'API réponde.
- [x] **Feedback du formulaire de Contact** : Remplacement du bouton cliqué par une animation de chargement (spinner CSS).

## 📍 Milestone 3 : L'Architecture DRY (Don't Repeat Yourself) 🛠️
*Transformer un site statique classique en une architecture modulaire ultra professionnelle.*
- [x] **Web Components Natifs** : Création de `<tntm-header>` et `<tntm-footer>` en Vanilla JS.
- [x] **Encapsulation JS** : Logique du menu hamburger et du surlignement de page active isolée dans le composant.
- [x] **Déploiement global** : Remplacement des blocs de code HTML répétitifs sur les 8 pages du site.

## 📍 Milestone 4 : Contenu & SEO Avancé
*Préparer le terrain pour attirer plus de trafic organique.*
- [x] **Balises Canoniques** : Ajouter `<link rel="canonical">` pour indiquer à Google l'URL "officielle" de chaque page et éviter le contenu dupliqué.
- [ ] **Open Graph (Social Media)** : Créer des images spécifiques par page (ex: une image avec écrit "Tarifs") pour un meilleur impact lors des partages de liens.
- [x] **Open Graph (Social Media)** : Créer des images spécifiques par page (ex: une image avec écrit "Tarifs") pour un meilleur impact lors des partages de liens.
- [x] **Données Structurées (Schema.org)** : Ajouter du JSON-LD pour que Google comprenne parfaitement tes services et tes prix (Bonus Senior).

---
*Mise à jour suite à la migration vers l'infrastructure Cloud indépendante (Railway / Namecheap).*