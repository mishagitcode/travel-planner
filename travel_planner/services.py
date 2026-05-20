import requests

ARTIC_BASE_URL = 'https://api.artic.edu/api/v1'


def fetch_place_from_api(external_id: str) -> dict | None:
    try:
        response = requests.get(
            f'{ARTIC_BASE_URL}/artworks/{external_id}',
            params={'fields': 'id,title'},
            timeout=5,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json().get('data', {})
        return {'name': data['title'], 'external_id': str(data['id'])}
    except (requests.RequestException, KeyError):
        return None
