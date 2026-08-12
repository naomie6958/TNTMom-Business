const heroBg = document.querySelector('.hero-bg');
const heroBgClip = document.querySelector('.hero-bg-clip');
const hero = document.getElementById('hero');

if (heroBg && hero) {
    let enAttente = false;

    function appliquerEffets() {
        const heroHeight = hero.offsetHeight;
        const progres = Math.min(Math.max(window.scrollY / heroHeight, 0), 1);

        const flou = (1 - progres) * 2;
        const decalageY = progres * 40;
        // Cristal clear : la netteté (flou) ET la vivacité montent ensemble avec le scroll
        const luminosite = 1 + progres * 0.15;
        const saturation = 1 + progres * 0.35;

        heroBg.style.filter = `blur(${flou}px) brightness(${luminosite}) saturate(${saturation})`;
        heroBg.style.transform = `translateY(${decalageY}px)`;

        // Scintillement seulement une fois l'image presque entièrement clarifiée
        if (heroBgClip) {
            heroBgClip.classList.toggle('scintille', progres > 0.85);
        }

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
