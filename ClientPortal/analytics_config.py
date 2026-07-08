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
        'site_tag': '61dcf932fa5e4be59825d5ab50457d07',
    },
    'chopper-burger': {
        'nom': 'Chopper Burger',
        'domain': 'chopperburger.tntm.ca',
        'site_tag': 'f580d45db19743f5b8547d767a8e52c6',
    },
    'tntm': {
        'nom': 'TNTM',
        'domain': 'tntm.ca',
        'site_tag': '1cb13c5e7f7e4a62bb999e006a42d2dd',
    },
}
