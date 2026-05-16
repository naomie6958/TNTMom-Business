const toggle = document.querySelector('#menu-toggle')
const nav = document.querySelector('nav')

toggle.addEventListener('click', function() {
    nav.classList.toggle('open')
})

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
