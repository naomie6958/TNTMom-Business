# Sites suivis par le dashboard Analytics (Cloudflare Web Analytics).
# Pour ajouter un site : une entrée ici + coller le script beacon Cloudflare
# dans le <head> du site en question.
#
# 'site_tag' = l'identifiant utilisé par l'API GraphQL Analytics (dimension
# `siteTag` du dataset rumPageloadEventsAdaptiveGroups) — CE N'EST PAS le même
# token que celui collé dans data-cf-beacon='{"token": "..."}' du script beacon
# (fausse hypothèse d'origine, trouvée le 2026-07-09 en diagnostiquant le
# dashboard /analytics qui affichait toujours 0). Pour retrouver la bonne
# valeur : Cloudflare dashboard → Analytics & Logs → Web Analytics → site en
# question → "Manage site" → JS Snippet installation, ou interroger le
# dataset sans filtre siteTag pour voir quels tags reçoivent vraiment des events.

ANALYTICS_SITES = {
    'underground-motorsport': {
        'nom': 'Underground Motorsport',
        'domain': 'undergroundmotorsport.ca',
        'site_tag': '2094ee46411a4719881d42f1d0e8e359',
    },
    'chopper-burger': {
        'nom': 'Chopper Burger',
        'domain': 'chopperburger.tntm.ca',
        'site_tag': 'e3aaa0fdd62342af96b8a1f3b15fc49d',
    },
    'tntm': {
        'nom': 'TNTM',
        'domain': 'tntm.ca',
        'site_tag': '1a771c40da5743c8bb5b6a5883b1595f',
    },
}
