# Gestionnaire de formulaires multi-clients — remplace Formspree sur les sites clients statiques.
# Pour ajouter un nouveau client : une entrée ici + pointer son <form action> vers
# https://portail.tntm.ca/api/public/form-submit avec un champ caché name="client" value="slug"

CLIENT_SITES = {
    'underground-motorsport': {
        'nom': 'Underground Motorsport',
        # Temporaire : naomiemcmahont@gmail.com en attendant que Luc confirme
        # lucbill1991@icloud.com sur le système (voir _notes-client.md du dossier client)
        'email': 'naomiemcmahont@gmail.com',
    },
}
