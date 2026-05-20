# Product Requirements Document
## Fuel Route Optimizer — Django REST API

---

### 1. Overview

The Fuel Route Optimizer is a Django REST API that accepts a start and finish location within the USA and returns an optimised driving route with the cheapest available fuel stops. It guarantees the vehicle never runs out of fuel while minimising the total trip fuel cost.

---

### 2. Goals & Success Criteria

| Goal | Metric |
|---|---|
| Return cheapest fuel-stop plan for any US road trip | Total cost is minimised via greedy look-ahead algorithm |
| Never leave the vehicle stranded | Every consecutive stop pair is ≤ 500 miles apart |
| Fast response | API responds in < 2 seconds end-to-end |
| Minimal external API dependency | ≤ 3 external calls per request (2 geocoding + 1 routing) |
| Correct cost calculation | `gallons = distance / 10`, `cost = gallons × price` |

---

### 3. Scope

**In scope**
- Single POST endpoint accepting plain-text US city/state locations
- Geocoding of start and finish addresses
- Route retrieval (full polyline + total distance)
- Fuel station selection from a provided CSV dataset (~8,151 US truck stops)
- Greedy look-ahead optimisation algorithm
- GeoJSON + encoded polyline in response
- CSV ingestion management command

**Out of scope**
- User authentication / accounts
- Multi-vehicle or multi-trip support
- Real-time fuel price feeds
- Turn-by-turn navigation
- Frontend / map UI

---

### 4. Users & Stakeholders

| Role | Need |
|---|---|
| API Consumer (driver / logistics app) | Cheapest fuel plan for a long-haul route |
| Backend Reviewer | Clean Django code, working algorithm, Postman demo |

---

### 5. Functional Requirements

#### 5.1 Endpoint

```
POST /api/route/
Content-Type: application/json
```

**Request**
```json
{ "start": "Chicago, IL", "finish": "Los Angeles, CA" }
```

**Response**
```json
{
  "route": {
    "total_distance_miles": 2015.4,
    "encoded_polyline": "_p~iF~ps|U...",
    "geojson": { "type": "LineString", "coordinates": [[...]] }
  },
  "fuel_stops": [
    {
      "stop_number": 1,
      "station_name": "LOVES TRAVEL STOP #766",
      "address": "I-80, EXIT 27, Atkinson, IL",
      "latitude": 41.41,
      "longitude": -89.99,
      "retail_price_per_gallon": 3.389,
      "gallons_purchased": 38.5,
      "cost_at_stop": 130.48,
      "miles_from_start": 180.2
    }
  ],
  "summary": {
    "total_fuel_stops": 5,
    "total_gallons": 201.5,
    "total_fuel_cost_usd": 698.42
  }
}
```

#### 5.2 Vehicle Constants

| Parameter | Value |
|---|---|
| Max range | 500 miles |
| Fuel efficiency | 10 MPG |
| Tank capacity | 50 gallons |
| Look-ahead safety buffer | 80% of max range (400 miles) |

#### 5.3 Fuel Station Data

- Source: `fuel-prices-for-be-assessment.csv` (~8,151 US truck stop stations)
- Loaded once via `python manage.py load_fuel_data`
- CSV contains no lat/lon — stations are pre-geocoded by `(city, state)` during load and persisted to DB
- Duplicate OPIS IDs: keep the row with the lowest retail price

#### 5.4 Optimisation Algorithm

- Decode OSRM polyline into ordered waypoints (~10-mile intervals)
- Assign each station a `route_mile_marker` (closest waypoint on polyline)
- Filter stations to ±10 miles laterally from route (haversine)
- Greedy loop: from current position, find cheapest station within 400 miles ahead; drive there, fill to full; repeat until destination
- At final segment: purchase only the fuel needed to reach destination (no overfill)

#### 5.5 Error Handling

| Condition | HTTP Response |
|---|---|
| Start/finish cannot be geocoded | `400 Bad Request` with descriptive message |
| No fuel stations found near route | `422 Unprocessable Entity` |
| OSRM unreachable | `503 Service Unavailable` |
| Route < 500 miles | `200 OK` with empty `fuel_stops` array, cost calculated |

---

### 6. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Response time | < 2 seconds (OSRM call ≈ 0.5–1s) |
| External API calls per request | ≤ 3 (2× Nominatim, 1× OSRM) |
| Station scan performance | Bounding-box pre-filter before haversine on 8k+ records |
| Nominatim rate limit compliance | 2 calls per request — within 1 req/sec limit |
| OSRM timeout | 15 seconds; fail gracefully |

---

### 7. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Framework | Django 5.x + Django REST Framework | Project requirement |
| Routing API | OSRM Demo Server | Free, no key, single call returns full polyline + distance |
| Geocoding | Nominatim / OpenStreetMap | Free, no API key |
| Fuel Data | Provided CSV | Loaded once into DB |
| Spatial Math | `geopy` (haversine) | Lightweight, pip-installable |
| Response Format | GeoJSON + encoded polyline | Standard, map-renderable |

**`requirements.txt`**
```
Django>=5.0
djangorestframework>=3.15
geopy>=2.4
requests>=2.31
polyline>=2.0
```

---

### 8. Data Model

```python
class FuelStation(models.Model):
    opis_id      = models.IntegerField()
    name         = models.CharField(max_length=255)
    address      = models.CharField(max_length=255)
    city         = models.CharField(max_length=100)
    state        = models.CharField(max_length=2)
    rack_id      = models.IntegerField()
    retail_price = models.FloatField()
    latitude     = models.FloatField(null=True)
    longitude    = models.FloatField(null=True)

    class Meta:
        indexes = [models.Index(fields=['latitude', 'longitude'])]
```

---

### 9. Deliverables

- [ ] `load_fuel_data` management command loads CSV successfully
- [ ] `POST /api/route/` returns the correct JSON structure
- [ ] All fuel stops are ≤ 500 miles apart
- [ ] Total fuel cost math is correct
- [ ] Response time < 2 seconds
- [ ] Code pushed to GitHub
- [ ] Loom demo video (≤ 5 min): Postman walkthrough + code explanation
