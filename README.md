# maps_api

Django REST API for geocoding and distance calculation using the Google Maps Geocoding API.

## Setup

Copy the example env and fill in your Google Maps key:

```
cp .env.example .env
```

Install deps and run:

```
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Swagger UI is at `http://localhost:8000/api/docs/`

---

## Endpoints

### POST /api/geocode/

Converts a free-text address or place name to coordinates.

```json
// request
{ "address": "beverly centre" }

// response
{
  "formatted_address": "Beverly Center, 8500 Beverly Blvd, Los Angeles, CA 90048, USA",
  "latitude": "34.075930",
  "longitude": "-118.376090",
  "place_id": "ChIJ...",
  "cached": false
}
```

---

### POST /api/reverse-geocode/

Coordinates to a human-readable address.

```json
// request
{ "latitude": 34.0759, "longitude": -118.3761 }

// response
{
  "formatted_address": "Beverly Center, 8500 Beverly Blvd, Los Angeles, CA 90048, USA",
  "latitude": "34.075900",
  "longitude": "-118.376100",
  "place_id": "ChIJ...",
  "cached": false
}
```

---

### POST /api/distance/

Takes two free-text addresses, geocodes them, and returns the straight-line distance (haversine). Both geocode results and the computed distance are cached in the DB so repeat queries don't hit Google.

```json
// request
{ "origin": "beverly centre", "destination": "LAX" }

// response
{
  "origin": {
    "formatted_address": "Beverly Center, 8500 Beverly Blvd, Los Angeles, CA 90048, USA",
    "latitude": "34.075930",
    "longitude": "-118.376090",
    "place_id": "ChIJ..."
  },
  "destination": {
    "formatted_address": "Los Angeles International Airport (LAX), 1 World Way, Los Angeles, CA 90045, USA",
    "latitude": "33.942501",
    "longitude": "-118.408056",
    "place_id": "ChIJ..."
  },
  "distance_km": "15.2341",
  "distance_miles": "9.4658"
}
```

---

### POST /api/distance/coordinates/

Straight-line distance between two lat/lng pairs. No geocoding, no DB — just the math.

```json
// request
{ "lat1": 34.0759, "lon1": -118.3761, "lat2": 33.9425, "lon2": -118.4081 }

// response
{ "distance_km": 15.1234, "distance_miles": 9.3970 }
```

---

## Database

Works with SQLite (default), PostgreSQL, or MySQL — set `DB_ENGINE` in `.env`.

```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=maps
DB_USER=postgres
DB_PASSWORD=secret
DB_HOST=localhost
DB_PORT=5432
```

## Running tests

```
python manage.py test tests/
```
