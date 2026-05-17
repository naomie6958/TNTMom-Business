// ── Lightbox ──────────────────────────────────────────────────────────────
const lightbox = document.createElement('div');
lightbox.className = 'lightbox';
lightbox.innerHTML = '<button class="lightbox-close" aria-label="Fermer">✕</button><img class="lightbox-img" src="" alt="">';
document.body.appendChild(lightbox);

const lbImg   = lightbox.querySelector('.lightbox-img');
const lbClose = lightbox.querySelector('.lightbox-close');

function openLightbox(src, alt) {
    lbImg.src = src;
    lbImg.alt = alt;
    lightbox.classList.add('open');
    document.body.style.overflow = 'hidden';
}
function closeLightbox() {
    lightbox.classList.remove('open');
    document.body.style.overflow = '';
}

lightbox.addEventListener('click', e => { if (e.target !== lbImg) closeLightbox(); });
lbClose.addEventListener('click', closeLightbox);
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });

document.querySelectorAll('.screenshot-item img').forEach(img => {
    img.addEventListener('click', () => openLightbox(img.src, img.alt));
});

// ── Nav toggle ────────────────────────────────────────────────────────────
const toggle = document.querySelector('#menu-toggle')
const nav = document.querySelector('nav')

const isDesktop = () => window.matchMedia('(min-width: 900px)').matches;

// Sur desktop : ouvrir par défaut sauf si localStorage dit fermé
if (isDesktop()) {
    if (localStorage.getItem('tntmNavOpen') !== 'false') nav.classList.add('open');
}

toggle.addEventListener('click', function() {
    nav.classList.toggle('open')
    if (!nav.classList.contains('open')) {
        const sub = document.querySelector('.nav-sub')
        const chevron = document.querySelector('.nav-chevron-btn')
        if (sub) sub.classList.remove('open')
        if (chevron) { chevron.setAttribute('aria-expanded', 'false'); chevron.textContent = '▾'; }
    }
    if (isDesktop()) {
        localStorage.setItem('tntmNavOpen', nav.classList.contains('open'));
    }
})

// ── Sous-menu Mes projets ─────────────────────────────────────────────────
const chevronBtn = document.querySelector('.nav-chevron-btn')
const navSub = document.querySelector('.nav-sub')

if (chevronBtn && navSub) {
    chevronBtn.addEventListener('click', function() {
        navSub.classList.toggle('open')
        const isOpen = navSub.classList.contains('open')
        chevronBtn.setAttribute('aria-expanded', String(isOpen))
        chevronBtn.textContent = isOpen ? '▴' : '▾'
    })
}

const currentPage = window.location.pathname.split('/').pop() || 'index.html';
document.querySelectorAll('nav a').forEach(link => {
    if (link.getAttribute('href') === currentPage) {
        link.classList.add('active');
    }
})

const STATUT_LABELS = {
    'live':      { label: '● Live',       cls: 'statut-live' },
    'en-cours':  { label: '◐ En cours',   cls: 'statut-en-cours' },
    'prototype': { label: '◇ Prototype',  cls: 'statut-prototype' },
}

function initiales(nom) {
    return nom.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
}

fetch('data/projets.json')
    .then(r => r.json())
    .then(projets => {
        const galerie = document.querySelector('#galerie');
        if (!galerie) return;
        galerie.innerHTML = '';

        projets.forEach(projet => {
            const card = document.createElement('div');
            card.className = 'projet-card' + (projet.couleur ? ' projet-card--' + projet.couleur : '');

            // ── Header visuel ─────────────────────────────────────────────
            const imgWrap = document.createElement('div');
            imgWrap.className = 'projet-card-preview projet-card-preview--' + (projet.couleur || 'magenta');
            if (projet.image) {
                const img = document.createElement('img');
                img.src = projet.image;
                img.alt = projet.nom;
                img.className = 'projet-card-img';
                imgWrap.appendChild(img);
            } else {
                imgWrap.innerHTML = `<span class="projet-card-initiales">${initiales(projet.nom)}</span>`;
            }
            card.appendChild(imgWrap);

            // ── Corps ─────────────────────────────────────────────────────
            const body = document.createElement('div');
            body.className = 'projet-card-body';

            // Titre + statut
            const header = document.createElement('div');
            header.className = 'projet-card-header';
            const titre = document.createElement('h3');
            titre.textContent = projet.nom;
            header.appendChild(titre);
            if (projet.statut && STATUT_LABELS[projet.statut]) {
                const { label, cls } = STATUT_LABELS[projet.statut];
                const badge = document.createElement('span');
                badge.className = 'projet-statut-badge ' + cls;
                badge.textContent = label;
                header.appendChild(badge);
            }
            body.appendChild(header);

            // Tagline
            if (projet.tagline) {
                const tl = document.createElement('p');
                tl.className = 'projet-tagline';
                tl.textContent = projet.tagline;
                body.appendChild(tl);
            }

            // Description
            const desc = document.createElement('p');
            desc.className = 'projet-desc';
            desc.textContent = projet.description;
            body.appendChild(desc);

            // Tags
            if (projet.tags && projet.tags.length) {
                const tags = document.createElement('div');
                tags.className = 'projet-tags';
                projet.tags.forEach(tag => {
                    const span = document.createElement('span');
                    span.className = 'projet-tag';
                    span.textContent = tag;
                    tags.appendChild(span);
                });
                body.appendChild(tags);
            }

            // Lien
            if (projet.link) {
                const isExternal = projet.link.startsWith('http');
                const lien = document.createElement('a');
                lien.href = projet.link;
                if (isExternal) lien.target = '_blank';
                lien.className = 'projet-card-link';
                lien.textContent = isExternal ? 'Voir le projet →' : 'Voir la fiche →';
                body.appendChild(lien);
            }

            card.appendChild(body);
            galerie.appendChild(card);
        });
    })

// ── Animations IntersectionObserver ───────────────────────────────────────
const animObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            e.target.classList.add('visible');
            animObserver.unobserve(e.target);
        }
    });
}, { threshold: 0.12 });

document.querySelectorAll('.anim-fade-up').forEach(el => animObserver.observe(el));
