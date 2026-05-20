import requests

def geocode(location_str: str):
    """
    Geocodes a location string using Nominatim API.
    Returns a tuple (latitude, longitude) or raises an exception.
    """
    url = 'https://nominatim.openstreetmap.org/search'
    headers = {
        'User-Agent': 'FuelRouteOptimizer/1.0'
    }
    params = {
        'q': location_str,
        'format': 'json',
        'limit': 1
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    if not data:
        raise ValueError(f"Cannot geocode '{location_str}'")
    
    return float(data[0]['lat']), float(data[0]['lon'])
