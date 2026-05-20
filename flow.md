# Fuel Route Optimizer — System Flow

---

## 1. High-Level Request Flow

```
Client
  │
  │  POST /api/route/  { "start": "...", "finish": "..." }
  ▼
RouteView (api/views.py)
  │
  ├──► geocoder.py ──────────────────────► Nominatim API  (call 1: start)
  │                                                        (call 2: finish)
  │       returns (lat, lon) for each
  │
  ├──► router.py ────────────────────────► OSRM API       (call 3: route)
  │       returns distance_miles, waypoints[], encoded_polyline
  │
  ├──► FuelStation.objects.all()  ──────── PostgreSQL / SQLite (no external call)
  │
  ├──► fuel_optimizer.py
  │       assigns mile markers, filters near-route stations,
  │       runs greedy look-ahead loop
  │       returns fuel_stops[], summary{}
  │
  └──► JSON Response  { route, fuel_stops, summary }
```

---

## 2. Setup / Data Ingestion Flow (one-time)

```
CSV file (8,151 rows)
  │
  ▼
load_fuel_data.py  (Django management command)
  │
  ├── csv.DictReader → parse rows
  │
  ├── group by (city, state)
  │       │
  │       └──► Nominatim geocode (cached per unique city+state)
  │                returns lat, lon
  │
  ├── deduplicate OPIS IDs (keep lowest retail_price)
  │
  └── FuelStation.objects.bulk_create()
            │
            ▼
        Database  ✓
```

---

## 3. Fuel Optimisation Algorithm Flow

```
INPUTS
  waypoints[]        ← decoded OSRM polyline, ~10-mile intervals
  all_stations[]     ← from DB
  fuel_level = 50    ← start full
  current_pos = start

┌──────────────────────────────────────────────────────────┐
│  PRE-PROCESSING                                          │
│                                                          │
│  1. assign_route_mile_markers(stations, waypoints)       │
│     For each station → find nearest waypoint             │
│                      → assign cumulative mile position   │
│                                                          │
│  2. stations_near_route(stations, waypoints, ±10 miles)  │
│     haversine lateral filter                             │
└──────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│  GREEDY LOOP                                             │
│                                                          │
│  WHILE current_pos ≠ destination                         │
│    │                                                     │
│    ├─ reachable_range = fuel_level × 10 (MPG)            │
│    │                                                     │
│    ├─ candidates = stations with                         │
│    │     mile_marker ∈ (current_mile, current_mile+400]  │
│    │     (80% of 500-mile tank = 400-mile safety window) │
│    │                                                     │
│    ├─ IF no candidates in 400-mile window                │
│    │     → extend search to full reachable_range         │
│    │     → IF still none → return 422 error              │
│    │                                                     │
│    ├─ best = min(candidates, key=retail_price)           │
│    │                                                     │
│    ├─ miles_driven = dist(current_pos → best)            │
│    ├─ fuel_used    = miles_driven / 10                   │
│    ├─ fuel_level  -= fuel_used                           │
│    │                                                     │
│    ├─ IF best is final segment to destination            │
│    │     gallons_added = fuel needed only (no overfill)  │
│    │  ELSE                                               │
│    │     gallons_added = 50 − fuel_level  (fill to full) │
│    │     fuel_level    = 50                              │
│    │                                                     │
│    ├─ record stop { station, gallons_added, cost, miles }│
│    │                                                     │
│    └─ current_pos = best                                 │
│                                                          │
│  END WHILE                                               │
└──────────────────────────────────────────────────────────┘
  │
  ▼
OUTPUTS
  stops[]    ← ordered list of fuel stop records
  summary{}  ← total_stops, total_gallons, total_cost_usd
```

---

## 4. Project Module Map

```
fuel_route_project/
│
├── manage.py
├── requirements.txt
│
├── fuel_route_project/
│   ├── settings.py
│   ├── urls.py          ──► includes api.urls
│   └── wsgi.py
│
└── api/
    ├── models.py         FuelStation (opis_id, name, address, city,
    │                                  state, rack_id, retail_price,
    │                                  latitude, longitude)
    │
    ├── serializers.py    DRF serializer for FuelStation
    │
    ├── views.py          RouteView (APIView)
    │                       POST → orchestrates geocoder + router
    │                              + fuel_optimizer
    │
    ├── urls.py           path('route/', RouteView.as_view())
    │
    ├── services/
    │   ├── geocoder.py        geocode(location_str) → (lat, lon)
    │   │                        via Nominatim / OSM
    │   │
    │   ├── router.py          get_route(start_ll, end_ll) → dict
    │   │                        via OSRM (1 call)
    │   │                        returns distance_miles, waypoints,
    │   │                                encoded_polyline
    │   │
    │   ├── fuel_optimizer.py  optimize_fuel_stops(route, stations)
    │   │                        → (stops[], summary{})
    │   │                      assign_route_mile_markers()
    │   │                      stations_near_route()
    │   │
    │   └── csv_loader.py      helper used by load_fuel_data command
    │
    └── management/commands/
        └── load_fuel_data.py  python manage.py load_fuel_data
                                 --file data/fuel-prices-for-be-assessment.csv
```

---

## 5. External API Calls Summary

```
Request lifecycle — at most 3 external calls:

  Call 1  Nominatim  geocode(start)   → (lat, lon)
  Call 2  Nominatim  geocode(finish)  → (lat, lon)
  Call 3  OSRM       get_route()      → distance + polyline

  All subsequent work: in-memory + DB only.
```

---

## 6. Error Flow

```
POST /api/route/
  │
  ├─ start/finish empty or invalid
  │     └──► geocoder raises exception
  │               └──► 400 Bad Request  { "error": "Cannot geocode '...'" }
  │
  ├─ OSRM timeout / unreachable
  │     └──► 503 Service Unavailable
  │
  ├─ No fuel stations found within reachable range anywhere on route
  │     └──► 422 Unprocessable Entity  { "error": "No fuel stations near route" }
  │
  └─ Route < 500 miles (fits in one tank)
        └──► 200 OK  { fuel_stops: [], summary: { total_fuel_cost_usd: X } }
```

---

## 7. Build Order (Step Sequence)

```
Step 1  Django project scaffold + pip installs
Step 2  FuelStation model + migrations
Step 3  load_fuel_data management command (CSV → geocode → bulk_create)
Step 4  geocoder.py service (Nominatim)
Step 5  router.py service (OSRM)
Step 6  fuel_optimizer.py (mile markers + greedy loop)
Step 7  RouteView wiring (views.py)
Step 8  URL configuration
Step 9  Testing (Postman: NY→LA, Chicago→Miami)
```
