const toggle = document.querySelector('#menu-toggle')
const nav = document.querySelector('nav')

toggle.addEventListener('click', function() {
    nav.classList.toggle('open')
})

// Met en évidence le lien de la page courante dans la nav
// pathname.split('/').pop() extrait le nom du fichier depuis l'URL
// ex: "/docs/about.html" → "about.html" ; "/" → "" → "index.html" (fallback)
const currentPage = window.location.pathname.split('/').pop() || 'index.html';
document.querySelectorAll('nav a').forEach(link => {
    if (link.getAttribute('href') === currentPage) {
        link.classList.add('active');
    }
})

fetch('projets.json')
    .then(response => response.json())
    .then(projets => {
        const galerie = document.querySelector('#galerie');
        if (!galerie) return;
        galerie.innerHTML = '';
        projets.forEach(projet => {
            const card = document.createElement('div');
            card.className = 'projet-card';

            // textContent traite la valeur comme texte pur — jamais exécutée comme HTML
            const h3 = document.createElement('h3');
            h3.textContent = projet.nom;

            if (projet.link) {
                const a = document.createElement('a');
                a.href = projet.link;
                a.appendChild(h3);
                card.appendChild(a);
            } else {
                card.classList.add('projet-card--wip');
                card.appendChild(h3);

                const badge = document.createElement('span');
                badge.className = 'wip-badge';
                badge.textContent = 'En cours';
                card.appendChild(badge);
            }

            const p = document.createElement('p');
            p.textContent = projet.description;
            card.appendChild(p);

            galerie.appendChild(card);
        })
    })