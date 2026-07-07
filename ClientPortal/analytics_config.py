# Sites suivis par le dashboard Analytics (Cloudflare Web Analytics).
# Pour ajouter un site : une entrée ici + coller le script beacon Cloudflare
# dans le <head> du site en question.
#
# 'site_tag' = le token trouvé dans data-cf-beacon='{"token": "..."}' du script beacon
# (le même token sert à la fois à envoyer les données ET à les relire via l'API GraphQL).

ANALYTICS_SITES = {
    'underground-motorsport': {
        'nom': 'Underground Motorsport',
        'domain': 'undergroundmotorsport.ca',
        'site_tag': None,  # à remplir une fois le script Cloudflare généré
    },
    'chopper-burger': {
        'nom': 'Chopper Burger',
        'domain': 'chopperburger.tntm.ca',
        'site_tag': None,
    },
    'tntm': {
        'nom': 'TNTM',
        'domain': 'tntm.ca',
        'site_tag': None,
    },
}
