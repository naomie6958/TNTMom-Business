const toggle = document.querySelector('#menu-toggle')
const nav = document.querySelector('nav')

toggle.addEventListener('click', function() {
    nav.classList.toggle('open')
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
            const titre = projet.link 
                ? `<a href="${projet.link}"><h3>${projet.nom}</h3></a>` : `<h3>${projet.nom}</h3>`; 
            card.innerHTML = titre + `<p>${projet.description}</p>`;
            galerie.appendChild(card)
        })
    })