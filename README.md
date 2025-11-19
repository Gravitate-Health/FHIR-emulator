# FHIR Emulator

A lightweight Flask-based FHIR server emulator for testing and development of ePIs and IPS resources within the FOSPS system.

## Endpoints

### `/epi/api/fhir/Bundle`
Returns FHIR Bundle resources with optional search and pagination support.

### `/ips/api/fhir/Patient`
Returns FHIR Patient resources with optional search and pagination support.

## Query Parameters

### Pagination
- `_count` (integer, default: 0) — Number of resources per page. If 0, returns total count with no entries or links.
- `_page` (positive integer, default: 1) — 1-based page number (alternative to `_offset`).
- `_offset` (non-negative integer, default: 0) — Zero-based offset into results (alternative to `_page`).

### Search
Resources are filtered by any field. Common search parameters:
- `_id` — Exact match on resource id (case-insensitive).
- `name` — Substring search on patient name (given and family fields).
- `gender` — Exact match on gender (male/female/etc., case-insensitive).
- `birthdate` — Prefix match on birthDate (e.g., `1980` matches `1980-01-01`).
- Any other field — Generic case-insensitive substring matching.

Multiple search parameters are combined with AND logic (all must match).

## Examples

### Get total count without entries
```
GET /ips/api/fhir/Patient?_count=0
```
Response: Bundle with `total` set, no `entry` or `link` keys.

### Get first page of 10 patients
```
GET /ips/api/fhir/Patient?_count=10&_page=1
```

### Search for a patient by id
```
GET /ips/api/fhir/Patient?_id=patient-1&_count=10
```

### Search patients by name
```
GET /ips/api/fhir/Patient?name=John&_count=10
```

### Search female patients, paginated
```
GET /ips/api/fhir/Patient?gender=female&_count=5&_page=1
```

### Search patients born in 1980
```
GET /ips/api/fhir/Patient?birthdate=1980&_count=10
```

### Combine search with pagination (offset-based)
```
GET /ips/api/fhir/Patient?gender=female&_count=1&_offset=0
```

### Search for a specific bundle
```
GET /epi/api/fhir/Bundle?_id=bundle-1&_count=10
```

## Running Locally

Setup and run (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Server starts at `http://127.0.0.1:5000`

## Docker

Build:
```powershell
docker build -t fhir-emulator:local .
```

Run with bind-mounted resources (app directory as `/app`):
```powershell
docker run -p 5000:5000 -v ${PWD}:/app -e FILES_DIR=/app/files fhir-emulator:local
```

Run with external resource directory:
```powershell
docker run -p 5000:5000 -v C:\path\to\resources:C:\resources -e FILES_DIR=C:\resources fhir-emulator:local
```

The `FILES_DIR` environment variable controls where the app loads Bundle and Patient resources.  
Expected structure: `$FILES_DIR/Bundle/*.json` and `$FILES_DIR/Patient/*.json`.

## Testing

Run all tests:
```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
```

Test coverage includes:
- Pagination (first/middle/last pages, link relations)
- Search by id, name, gender, birthdate
- Empty results
- Combined search and pagination
