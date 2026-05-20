from geopy.distance import geodesic
import math

# Vehicle constants
MAX_RANGE_MILES = 500
MPG = 10
TANK_CAPACITY_GALLONS = 50
SAFETY_BUFFER_MILES = 400 # 80% of max range

def optimize_fuel_stops(route_data, stations_queryset):
    waypoints = route_data['waypoints']
    total_distance_miles = route_data['distance_miles']
    
    # 1. Bounding box filter for stations to avoid checking all 8k+ with haversine
    lats = [wp[0] for wp in waypoints]
    lons = [wp[1] for wp in waypoints]
    min_lat, max_lat = min(lats) - 0.2, max(lats) + 0.2
    min_lon, max_lon = min(lons) - 0.2, max(lons) + 0.2
    
    stations = stations_queryset.filter(
        latitude__gte=min_lat, latitude__lte=max_lat,
        longitude__gte=min_lon, longitude__lte=max_lon
    )
    
    # Calculate cumulative miles for waypoints
    cumulative_miles = [0]
    for i in range(1, len(waypoints)):
        dist = geodesic(waypoints[i-1], waypoints[i]).miles
        cumulative_miles.append(cumulative_miles[-1] + dist)

    # 2. Assign mile markers to stations
    valid_stations = []
    for station in stations:
        station_loc = (station.latitude, station.longitude)
        
        # Find closest waypoint
        closest_dist = float('inf')
        closest_mile_marker = 0
        
        # Optimization: step by 10 to quickly find rough location, then fine-tune if needed
        # Or just evaluate all waypoints (there might be thousands though for long trips)
        # We can just evaluate all waypoints, it's fast enough in python
        for i, wp in enumerate(waypoints):
            dist = geodesic(station_loc, wp).miles
            if dist < closest_dist:
                closest_dist = dist
                closest_mile_marker = cumulative_miles[i]
                
        # Only keep stations within 10 miles laterally
        if closest_dist <= 10.0:
            valid_stations.append({
                'station': station,
                'mile_marker': closest_mile_marker
            })
            
    # Sort valid stations by mile marker
    valid_stations.sort(key=lambda x: x['mile_marker'])
    
    # 3. Greedy loop
    current_mile = 0
    fuel_level = TANK_CAPACITY_GALLONS
    stops = []
    
    while current_mile < total_distance_miles:
        # Distance left to destination
        dist_to_dest = total_distance_miles - current_mile
        
        # Can we reach the destination?
        reachable_range = fuel_level * MPG
        if reachable_range >= dist_to_dest:
            break
            
        # Candidates in safety window (up to 400 miles ahead)
        candidates = [s for s in valid_stations if current_mile < s['mile_marker'] <= current_mile + SAFETY_BUFFER_MILES]
        
        # If no candidates in safety window, extend to full reachable range
        if not candidates:
            candidates = [s for s in valid_stations if current_mile < s['mile_marker'] <= current_mile + reachable_range]
            
        if not candidates:
            raise ValueError("No fuel stations near route in reachable range")
            
        # Find the cheapest candidate
        best_candidate = min(candidates, key=lambda x: x['station'].retail_price)
        
        # Drive to best_candidate
        miles_driven = best_candidate['mile_marker'] - current_mile
        fuel_used = miles_driven / MPG
        fuel_level -= fuel_used
        
        # How much to buy?
        dist_from_candidate_to_dest = total_distance_miles - best_candidate['mile_marker']
        fuel_needed_to_dest = dist_from_candidate_to_dest / MPG
        
        if fuel_needed_to_dest <= (TANK_CAPACITY_GALLONS - fuel_level):
            gallons_added = fuel_needed_to_dest
        else:
            gallons_added = TANK_CAPACITY_GALLONS - fuel_level
            
        fuel_level += gallons_added
        cost = gallons_added * best_candidate['station'].retail_price
        
        stops.append({
            'stop_number': len(stops) + 1,
            'station_name': best_candidate['station'].name,
            'address': best_candidate['station'].address,
            'latitude': best_candidate['station'].latitude,
            'longitude': best_candidate['station'].longitude,
            'retail_price_per_gallon': best_candidate['station'].retail_price,
            'gallons_purchased': round(gallons_added, 2),
            'cost_at_stop': round(cost, 2),
            'miles_from_start': round(best_candidate['mile_marker'], 2)
        })
        
        current_mile = best_candidate['mile_marker']

    total_gallons = sum(s['gallons_purchased'] for s in stops)
    total_cost = sum(s['cost_at_stop'] for s in stops)
    
    summary = {
        'total_fuel_stops': len(stops),
        'total_gallons': round(total_gallons, 2),
        'total_fuel_cost_usd': round(total_cost, 2)
    }
    
    return stops, summary
