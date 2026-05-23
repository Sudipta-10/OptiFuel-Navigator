# OptiFuel Navigator API

A high-performance, algorithmic Fuel Route Optimizer built with Django. This application takes a starting location and a destination within the USA, calculates the driving route, and dynamically determines the most cost-effective fuel stops along the way based on real-world fuel prices.

## 🚀 Features

- **Algorithmic Fuel Optimization:** Calculates optimal refueling stops based on a 500-mile vehicle range, 10 MPG fuel efficiency, and real-time station pricing.
- **Ultra-Fast Performance:** 
  - Makes exactly **one** external API call to the routing engine (OSRM).
  - Uses an internal offline geocoding engine (`pgeocode`) and a custom `fast_haversine` mathematical heuristic to map thousands of fuel stations against the route geometry in less than 0.1 seconds.
- **Background CSV Processing:** Asynchronously parses, geocodes, and loads massive fuel price datasets into a SQLite database without blocking the main thread.
- **Interactive UI:** Includes a beautiful, modern frontend dashboard with live upload progress tracking and Leaflet map integration.

## 🛠 Tech Stack

- **Backend:** Django, Django REST Framework
- **Geocoding & Math:** `pgeocode` (offline geocoding), custom Haversine implementation
- **Routing Engine:** OpenStreetMap / OSRM (Free, no API key required)
- **Frontend:** HTML/CSS/JS, Leaflet.js
- **Database:** SQLite (for easy setup and portability)

## ⚡️ Algorithmic Approach (Why it's fast)

A naive approach to finding gas stations along a route would involve making thousands of API calls to a routing service to check the distance from the highway to every station in the country. This would take minutes or hours and easily trigger API rate limits.

Instead, this application:
1. Calls the OSRM routing API exactly **once** to get the polyline/waypoints of the entire trip.
2. Filters the 6,000+ stations down to a small bounding box surrounding the route.
3. Steps through the route geometry and uses a custom, pure-math `fast_haversine` function to calculate the Euclidean distance between the route waypoints and the stations.
4. Uses a greedy algorithmic loop to simulate the 500-mile tank range, looking ahead to find the cheapest station within the reachable safety window.

## 📦 Setup & Installation

**1. Clone the repository**
```bash
git clone https://github.com/Sudipta-10/OptiFuel-Navigator.git
cd OptiFuel-Navigator
```

**2. Create a virtual environment & install dependencies**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Run migrations**
```bash
python manage.py migrate
```

**4. Start the server**
```bash
python manage.py runserver
```

## 🌐 API Documentation

### 1. Calculate Route
**POST** `/api/route/`
Calculates the optimal route and fuel stops.

**Request Body:**
```json
{
    "start": "New York, NY",
    "finish": "Los Angeles, CA"
}
```

**Response:**
```json
{
    "route": {
        "total_distance_miles": 2790.5,
        "encoded_polyline": "...",
        "geojson": { ... }
    },
    "fuel_stops": [
        {
            "stop_number": 1,
            "station_name": "SHEETZ #639",
            "address": "I-80 Exit 223",
            "latitude": 41.1035,
            "longitude": -80.6520,
            "retail_price_per_gallon": 3.059,
            "gallons_purchased": 39.51,
            "cost_at_stop": 120.85,
            "miles_from_start": 395.06
        }
    ],
    "summary": {
        "total_fuel_stops": 6,
        "total_gallons": 279.05,
        "total_fuel_cost_usd": 850.45
    }
}
```

### 2. Upload Fuel Data
**POST** `/api/upload/`
Upload the `fuel-prices-for-be-assessment.csv` file (FormData).

### 3. Check Upload Status
**GET** `/api/upload-status/`
Returns the progress of the background CSV processing job.
