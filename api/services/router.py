import requests
import polyline

def get_route(start_ll: tuple, finish_ll: tuple):
    """
    Fetches route from OSRM Demo server.
    start_ll and finish_ll are (lat, lon) tuples.
    Returns:
    {
        'distance_miles': float,
        'waypoints': list of (lat, lon),
        'encoded_polyline': str
    }
    """
    # OSRM expects lon,lat
    start_lon, start_lat = start_ll[1], start_ll[0]
    finish_lon, finish_lat = finish_ll[1], finish_ll[0]
    
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{finish_lon},{finish_lat}"
    params = {
        'overview': 'full',
        'geometries': 'polyline'
    }
    
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    if data['code'] != 'Ok':
        raise ValueError("OSRM API could not calculate route")
        
    route = data['routes'][0]
    encoded_polyline = route['geometry']
    distance_meters = route['distance']
    distance_miles = distance_meters * 0.000621371
    
    waypoints = polyline.decode(encoded_polyline) # returns list of (lat, lon)
    
    return {
        'distance_miles': distance_miles,
        'waypoints': waypoints,
        'encoded_polyline': encoded_polyline
    }
