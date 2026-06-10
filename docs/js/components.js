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
                <nav>
                    <a href="/index.html">Accueil</a>
                    <div class="nav-group">
                        <a href="/index.html#galerie" class="nav-group-link">Mes projets</a>
                        <button class="nav-chevron-btn" aria-expanded="false">▾</button>
                        <div class="nav-sub">
                            <a href="https://chopperburger.tntm.ca" target="_blank" class="nav-sub-item">↳ Chopper Burger</a>
                            <a href="/clientportal.html" class="nav-sub-item">↳ ClientPortal</a>
                            <a href="/familydashboard.html" class="nav-sub-item">↳ Family Dashboard</a>
                        </div>
                    </div>
                    <a href="/process.html">Comment je travaille</a>
                    <a href="/tarifs.html">Tarifs</a>
                    <a href="/about.html">À propos</a>
                    <a href="/contact.html">Contact</a>
                    <a href="https://portail.tntm.ca/portail/login" target="_blank" class="nav-portail">Portail client →</a>
                </nav>
                <button id="menu-toggle" aria-label="Ouvrir le menu">☰</button>
            </header>
            </div>
        `;

        // Logique du menu encapsulée
        const toggle = this.querySelector('#menu-toggle');
        const nav = this.querySelector('nav');
        const isDesktop = () => window.matchMedia('(min-width: 900px)').matches;

        if (isDesktop() && localStorage.getItem('tntmNavOpen') === 'true') nav.classList.add('open');

        toggle.addEventListener('click', () => {
            nav.classList.toggle('open');
            if (!nav.classList.contains('open')) {
                const sub = this.querySelector('.nav-sub');
                const chevron = this.querySelector('.nav-chevron-btn');
                if (sub) sub.classList.remove('open');
                if (chevron) { chevron.setAttribute('aria-expanded', 'false'); chevron.textContent = '▾'; }
            }
            if (isDesktop()) localStorage.setItem('tntmNavOpen', nav.classList.contains('open'));
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
        this.querySelectorAll('nav a').forEach(link => {
            const href = link.getAttribute('href').split('/').pop();
            if (href === currentPage && !link.classList.contains('nav-portail')) link.classList.add('active');
        });
    }
}
customElements.define('tntm-header', TntmHeader);

class TntmFooter extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <footer>
                <div id="footer-brand">
                    <img src="/images/tntmom-favicon-bleu.svg" alt="TNTM" id="footer-favicon">
                    <span>The Nerdy Trap Mom</span>
                </div>
                <a href="https://buymeacoffee.com/tntm" target="_blank" class="bmc-btn">☕ Buy me a coffee</a>
                <span id="footer-copy">© 2026 TNTM — Naomie McMahon Tanguay</span>
            </footer>
        `;
    }
}
customElements.define('tntm-footer', TntmFooter);