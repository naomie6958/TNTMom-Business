const heroBg = document.querySelector('.hero-bg');
const hero = document.getElementById('hero');

if (heroBg && hero) {
    let enAttente = false;

    function appliquerEffets() {
        const heroHeight = hero.offsetHeight;
        const progres = Math.min(Math.max(window.scrollY / heroHeight, 0), 1);

        const flou = progres * 8;
        const decalageY = progres * 40;

        heroBg.style.filter = `blur(${flou}px)`;
        heroBg.style.transform = `translateY(${decalageY}px)`;

        enAttente = false;
    }

    window.addEventListener('scroll', () => {
        if (!enAttente) {
            window.requestAnimationFrame(appliquerEffets);
            enAttente = true;
        }
    }, { passive: true });

    appliquerEffets();
}
