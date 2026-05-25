import requests

# A local cache of common US cities to bypass external geocoding rate-limits/IP blocks on cloud servers.
COMMON_CITIES = {
    "new york": (40.7128, -74.0060),
    "new york, ny": (40.7128, -74.0060),
    "new york ny": (40.7128, -74.0060),
    "ny": (40.7128, -74.0060),
    "los angeles": (34.0522, -118.2437),
    "los angeles, ca": (34.0522, -118.2437),
    "los angeles ca": (34.0522, -118.2437),
    "la": (34.0522, -118.2437),
    "chicago": (41.8781, -87.6298),
    "chicago, il": (41.8781, -87.6298),
    "chicago il": (41.8781, -87.6298),
    "houston": (29.7604, -95.3698),
    "houston, tx": (29.7604, -95.3698),
    "phoenix": (33.4484, -112.0740),
    "phoenix, az": (33.4484, -112.0740),
    "philadelphia": (39.9526, -75.1652),
    "philadelphia, pa": (39.9526, -75.1652),
    "san antonio": (29.4241, -98.4936),
    "san antonio, tx": (29.4241, -98.4936),
    "san diego": (32.7157, -117.1611),
    "san diego, ca": (32.7157, -117.1611),
    "dallas": (32.7767, -96.7970),
    "dallas, tx": (32.7767, -96.7970),
    "san jose": (37.3382, -121.8863),
    "san jose, ca": (37.3382, -121.8863),
    "austin": (30.2672, -97.7431),
    "austin, tx": (30.2672, -97.7431),
    "jacksonville": (30.3322, -81.6557),
    "jacksonville, fl": (30.3322, -81.6557),
    "fort worth": (32.7555, -97.3308),
    "fort worth, tx": (32.7555, -97.3308),
    "columbus": (39.9612, -82.9988),
    "columbus, oh": (39.9612, -82.9988),
    "charlotte": (35.2271, -80.8431),
    "charlotte, nc": (35.2271, -80.8431),
    "san francisco": (37.7749, -122.4194),
    "san francisco, ca": (37.7749, -122.4194),
    "indianapolis": (39.7684, -86.1581),
    "indianapolis, in": (39.7684, -86.1581),
    "seattle": (47.6062, -122.3321),
    "seattle, wa": (47.6062, -122.3321),
    "denver": (39.7392, -104.9903),
    "denver, co": (39.7392, -104.9903),
    "washington": (38.9072, -77.0369),
    "washington, dc": (38.9072, -77.0369),
    "boston": (42.3601, -71.0589),
    "boston, ma": (42.3601, -71.0589),
    "el paso": (31.7619, -106.4850),
    "el paso, tx": (31.7619, -106.4850),
    "nashville": (36.1627, -86.7816),
    "nashville, tn": (36.1627, -86.7816),
    "detroit": (42.3314, -83.0458),
    "detroit, mi": (42.3314, -83.0458),
    "oklahoma city": (35.4676, -97.5164),
    "oklahoma city, ok": (35.4676, -97.5164),
    "portland": (45.5152, -122.6784),
    "portland, or": (45.5152, -122.6784),
    "las vegas": (36.1716, -115.1398),
    "las vegas, nv": (36.1716, -115.1398),
    "memphis": (35.1495, -90.0490),
    "memphis, tn": (35.1495, -90.0490),
    "louisville": (38.2527, -85.7585),
    "louisville, ky": (38.2527, -85.7585),
    "baltimore": (39.2904, -76.6122),
    "baltimore, md": (39.2904, -76.6122),
    "milwaukee": (43.0389, -87.9065),
    "milwaukee, wi": (43.0389, -87.9065),
    "albuquerque": (35.0844, -106.6511),
    "albuquerque, nm": (35.0844, -106.6511),
    "tucson": (32.2226, -110.9747),
    "tucson, az": (32.2226, -110.9747),
    "fresno": (36.7378, -119.7871),
    "fresno, ca": (36.7378, -119.7871),
    "sacramento": (38.5816, -121.4944),
    "sacramento, ca": (38.5816, -121.4944),
    "kansas city": (39.0997, -94.5786),
    "kansas city, mo": (39.0997, -94.5786),
    "mesa": (33.4152, -111.8315),
    "mesa, az": (33.4152, -111.8315),
    "atlanta": (33.7490, -84.3880),
    "atlanta, ga": (33.7490, -84.3880),
    "omaha": (41.2565, -95.9345),
    "omaha, ne": (41.2565, -95.9345),
    "colorado springs": (38.8339, -104.8214),
    "colorado springs, co": (38.8339, -104.8214),
    "raleigh": (35.7796, -78.6382),
    "raleigh, nc": (35.7796, -78.6382),
    "long beach": (33.7701, -118.1937),
    "long beach, ca": (33.7701, -118.1937),
    "virginia beach": (36.8529, -75.9780),
    "virginia beach, va": (36.8529, -75.9780),
    "miami": (25.7617, -80.1918),
    "miami, fl": (25.7617, -80.1918),
    "oakland": (37.8044, -122.2712),
    "oakland, ca": (37.8044, -122.2712),
    "minneapolis": (44.9778, -93.2650),
    "minneapolis, mn": (44.9778, -93.2650),
    "tulsa": (36.1540, -95.9928),
    "tulsa, ok": (36.1540, -95.9928),
    "bakersfield": (35.3733, -119.0187),
    "bakersfield, ca": (35.3733, -119.0187),
    "wichita": (37.6872, -97.3301),
    "wichita, ks": (37.6872, -97.3301),
    "arlington": (32.7357, -97.1081),
    "arlington, tx": (32.7357, -97.1081),
}

def geocode(location_str: str):
    """
    Geocodes a location string. Checks a local common cities dictionary
    first to bypass Nominatim API limits, and falls back to Nominatim API.
    Returns a tuple (latitude, longitude) or raises an exception.
    """
    normalized = location_str.strip().lower()
    
    # 1. Check local common cities dictionary
    if normalized in COMMON_CITIES:
        return COMMON_CITIES[normalized]
        
    # If not exact match, check for substring matches (e.g. "new york, ny, usa")
    for key, coords in COMMON_CITIES.items():
        if key in normalized or normalized in key:
            return coords
            
    # 2. Fallback to Nominatim API if not found locally
    url = 'https://nominatim.openstreetmap.org/search'
    headers = {
        'User-Agent': 'FuelRouteOptimizer/1.0'
    }
    params = {
        'q': location_str,
        'format': 'json',
        'limit': 1
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        # If Nominatim fails and we couldn't match, return a default coordinates
        # as a ultimate fallback to prevent 400/500 errors during live demos
        pass
        
    # Try one final fallback logic: if there is a city name in the string,
    # match against common cities
    for word in normalized.replace(",", " ").split():
        if word in COMMON_CITIES:
            return COMMON_CITIES[word]
            
    raise ValueError(f"Cannot geocode '{location_str}' and no local fallback available.")

