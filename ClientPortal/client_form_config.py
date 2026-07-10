# Gestionnaire de formulaires multi-clients — remplace Formspree sur les sites clients statiques.
# Pour ajouter un nouveau client : une entrée ici + pointer son <form action> vers
# https://portail.tntm.ca/api/public/form-submit avec un champ caché name="client" value="slug"

CLIENT_SITES = {
    'underground-motorsport': {
        'nom': 'Underground Motorsport',
        'email': 'admin@undergroundmotorsport.ca',
    },
    'nadia-ta-doula': {
        'nom': 'Nadia ta Doula',
        'email': 'naomiemcmahont@gmail.com',  # TEST TEMPORAIRE 2026-07-09 — remettre nadiatadoula@outlook.com avant de laisser Nadia tester
    },
}
