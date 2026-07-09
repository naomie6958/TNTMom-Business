// Cloudflare Web Analytics — injecté ici plutôt que dupliqué sur chaque page,
// puisque components.js est déjà chargé partout. Une seule source à maintenir.
// Note : ce fichier est chargé dans <head> sans defer, donc document.body n'existe
// pas encore ici — on ajoute au <head> à la place (toujours disponible à ce stade).
(function () {
    // Auto-exclusion : visiter n'importe quelle page une fois avec ?noanalytics
    // dans l'URL enregistre le choix dans localStorage pour de bon (jusqu'à
    // vidage des données du site) — le beacon ne se charge alors plus jamais
    // sur cet appareil/navigateur, sans affecter les autres visiteurs.
    if (new URLSearchParams(window.location.search).has('noanalytics')) {
        localStorage.setItem('tntm_exclude_analytics', 'true');
    }
    if (localStorage.getItem('tntm_exclude_analytics') === 'true') return;

    const beacon = document.createElement('script');
    beacon.defer = true;
    beacon.src = 'https://static.cloudflareinsights.com/beacon.min.js';
    beacon.setAttribute('data-cf-beacon', '{"token": "1cb13c5e7f7e4a62bb999e006a42d2dd"}');
    document.head.appendChild(beacon);
})();

class TntmHeader extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <div class="sticky-header">
            <header>
                <div id="header-brand">
                    <a href="/index.html" class="header-banner-link">
                        <div class="header-banner">
                            <span class="hb-tnt">TNT</span>
                            <div class="hb-sep"></div>
                            <div class="hb-right">
                                <span class="hb-label">Développeuse</span>
                                <span class="hb-mom">MOM</span>
                            </div>
                        </div>
                    </a>
                </div>
                <div class="nav-primary">
                    <a href="/index.html">Accueil</a>
                    <a href="/about.html">À propos</a>
                    <a href="/contact.html">Contact</a>
                </div>
                <nav>
                    <div class="nav-group">
                        <a href="/index.html#galerie" class="nav-group-link">Mes projets</a>
                        <button class="nav-chevron-btn" aria-expanded="false" title="Voir les projets" aria-label="Voir les projets">▾</button>
                        <div class="nav-sub">
                            <a href="https://chopperburger.tntm.ca" target="_blank" class="nav-sub-item">↳ Chopper Burger</a>
                            <a href="/clientportal.html" class="nav-sub-item">↳ ClientPortal</a>
                            <a href="https://familydashboard.tntm.ca" class="nav-sub-item">↳ Family Dashboard</a>
                        </div>
                    </div>
                    <a href="/process.html">Comment je travaille</a>
                    <a href="/tarifs.html">Tarifs</a>
                    <a href="https://portail.tntm.ca/portail/login" target="_blank" class="nav-portail">Portail client →</a>
                </nav>
                <button id="menu-toggle" aria-label="Ouvrir le menu" title="Menu">☰</button>
            </header>
            </div>
        `;

        // Logique du menu encapsulée
        const toggle = this.querySelector('#menu-toggle');
        const nav = this.querySelector('nav');
        const isDesktop = () => window.matchMedia('(min-width: 900px)').matches;


        toggle.addEventListener('click', () => {
            nav.classList.toggle('open');
            if (!nav.classList.contains('open')) {
                const sub = this.querySelector('.nav-sub');
                const chevron = this.querySelector('.nav-chevron-btn');
                if (sub) sub.classList.remove('open');
                if (chevron) { chevron.setAttribute('aria-expanded', 'false'); chevron.textContent = '▾'; }
            }
        });

        const chevronBtn = this.querySelector('.nav-chevron-btn');
        const navSub = this.querySelector('.nav-sub');
        if (chevronBtn && navSub) {
            chevronBtn.addEventListener('click', () => {
                navSub.classList.toggle('open');
                const isOpen = navSub.classList.contains('open');
                chevronBtn.setAttribute('aria-expanded', String(isOpen));
                chevronBtn.textContent = isOpen ? '▴' : '▾';
            });
        }

        // Surligner la page active dynamiquement
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        this.querySelectorAll('.nav-primary a, nav a').forEach(link => {
            const href = link.getAttribute('href').split('/').pop();
            if (href === currentPage && !link.classList.contains('nav-portail') && !link.classList.contains('nav-cta')) link.classList.add('active');
        });

        // Hauteur réelle du header (var CSS), pour les sections qui doivent
        // remplir l'écran restant (ex: calc(100vh - var(--header-h))) sans
        // dépendre d'un chiffre en dur qui se périme dès que le header change.
        const setHeaderHeight = () => {
            document.documentElement.style.setProperty('--header-h', `${this.offsetHeight}px`);
        };
        setHeaderHeight();
        window.addEventListener('resize', setHeaderHeight);
    }
}
customElements.define('tntm-header', TntmHeader);

class TntmFooter extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <footer>
                <div id="footer-brand">
                    <img src="images/tntmom-favicon-bleu.svg" alt="TNTM" id="footer-favicon">
                    <span>The Nerdy Trap Mom</span>
                </div>
                <div id="footer-links">
                    <a href="https://www.facebook.com/profile.php?id=61589509485529" target="_blank" class="footer-social">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:0.4rem;"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>TNTMom
                    </a>
                    <a href="https://github.com/naomie6958" target="_blank" class="footer-social">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:0.4rem;"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12z"/></svg>GitHub
                    </a>
                    <a href="https://www.linkedin.com/in/naomie-mcmahon-tanguay-67140218a" target="_blank" class="footer-social">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:0.4rem;"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.446-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 1 1 0-4.124 2.062 2.062 0 0 1 0 4.124zM7.114 20.452H3.558V9h3.556v11.452z"/></svg>LinkedIn
                    </a>
                    <a href="https://buymeacoffee.com/tntm" target="_blank" class="bmc-btn">☕ Buy me a coffee</a>
                </div>
                <span id="footer-copy">© 2026 TNTM — Naomie McMahon Tanguay</span>
            </footer>
        `;
    }
}
customElements.define('tntm-footer', TntmFooter);