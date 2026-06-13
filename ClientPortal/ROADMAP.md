# 🚀 ROADMAP CLIENT PORTAL - V2.0

## 🏗️ 1. Restructuration par Blueprint (Urgence)
- [x] **`routes_auth.py`** : Extraction du login/logout et session.
- [x] **`routes_admin_clients.py`** : Extraction du CRM complet (ajout, fiches, suppression).
- [x] **`routes_admin_compta.py`** : Extraction des heures, dépenses et budget.
- [x] **`routes_admin_tools.py`** : Extraction des formulaires, tarifs et packages.
- [x] **Nettoyage `app.py`** : Le réduire au strict minimum (init et serve).

## 🧠 2. Logique de Développement & Robustesse
- [x] **E-mails Asynchrones (Threading)** : Ne plus figer l'UI lors de l'envoi d'e-mails.
- [x] **Soft Delete (CRM)** : Désactiver le `ON DELETE CASCADE` destructif et utiliser une colonne `archivé/deleted`.
- [x] **Export CSV Comptabilité** : Générer des rapports Excel pour la fin d'année fiscale.
- [x] **Validation JSON Globale** : Sécuriser la lecture de `milestones` et `reponses`.

## 🎨 3. Expérience Utilisateur (UX / UI)
- [x] **Forms Asynchrones (AJAX)** : Remplacer les `redirect` par des appels `fetch` (ex: ajout dépense, chrono).
- [x] **Bannière "Vue Client"** : Indicateur visuel fort lors de l'utilisation de `switch-client`.
- [x] **Bouton Flottant (FAB) Mobile** : Action rapide pour le punch de temps ou ajout de notes.
- [x] **Filtres JS** : Recherche dynamique sur la liste des clients et factures.
- [x] **Skeleton Loading** : Animation d'attente pour le Command Center.

## 💼 4. Fonctionnalités Produit (Business)
- [ ] **Paiement Stripe** : Bouton "Payer" directement sur les factures du portail.
- [x] **Générateur PDF** : Créer un vrai fichier PDF pour les factures et contrats (Intégré via WeasyPrint).
- [x] **Journal d'activité client** : Voir l'heure de dernière connexion et les fichiers téléchargés.
- [x] **Commentaires sur fichiers** : Feedback direct sur les maquettes dans le portail.
- [x] **Templates de Contrats** : Sauvegarder des structures de projets réutilisables (Géré via les Forfaits/Packages).

---
*Prochaines étapes définies en collaboration avec l'assistant Tech Lead.*