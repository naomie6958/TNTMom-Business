"""Lecture des stats Cloudflare Web Analytics via leur API GraphQL.

Le token d'API (CLOUDFLARE_API_TOKEN dans .env) a besoin de la permission
"Account Analytics: Read". Le "site_tag" de chaque site vient du script
beacon Cloudflare (data-cf-beacon='{"token": "..."}') — voir analytics_config.py.
"""
import os
import datetime
import requests

GRAPHQL_URL = 'https://api.cloudflare.com/client/v4/graphql'


def get_site_stats(site_tag, days=30):
    """Retourne {'total_visits': int, 'daily': [{'date': 'YYYY-MM-DD', 'visits': int}, ...]}
    pour les `days` derniers jours d'un site donné (identifié par son site_tag Cloudflare).
    Retourne None si le token, l'account tag ou le site_tag ne sont pas configurés.
    """
    token = os.getenv('CLOUDFLARE_API_TOKEN')
    account_tag = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    if not token or not account_tag or not site_tag:
        return None

    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    until = datetime.date.today().isoformat()

    query = """
    query($accountTag: String!, $siteTag: String!, $since: Date!, $until: Date!) {
      viewer {
        accounts(filter: {accountTag: $accountTag}) {
          rumPageloadEventsAdaptiveGroups(
            limit: 1000
            filter: { siteTag: $siteTag, date_geq: $since, date_leq: $until }
            orderBy: [date_ASC]
          ) {
            count
            dimensions { date }
          }
        }
      }
    }
    """
    variables = {
        'accountTag': account_tag,
        'siteTag': site_tag,
        'since': since,
        'until': until,
    }

    res = requests.post(
        GRAPHQL_URL,
        json={'query': query, 'variables': variables},
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        timeout=15,
    )
    res.raise_for_status()
    payload = res.json()

    if payload.get('errors'):
        raise ValueError(str(payload['errors']))

    groups = (
        payload.get('data', {})
        .get('viewer', {})
        .get('accounts', [{}])[0]
        .get('rumPageloadEventsAdaptiveGroups', [])
    )

    daily = [{'date': g['dimensions']['date'], 'visits': g['count']} for g in groups]
    total = sum(d['visits'] for d in daily)

    return {'total_visits': total, 'daily': daily}
