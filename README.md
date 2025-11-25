# FHIR Emulator

A lightweight Flask-based FHIR server emulator for testing and development of ePIs and IPS resources.

## Endpoints

The server exposes generalized FHIR-style endpoint :

- `/fhir/<resource_type>`

`<resource_type>` maps directly to a folder under the configured `FILES_DIR` (see below) and the same behavior applies to all resource types (Bundle, Patient, Organization, etc.). Examples below assume `Bundle` and `Patient` are present.

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
GET /fhir/Patient?_count=0
```
Response: Bundle with `total` set, no `entry` or `link` keys.

### Get first page of 10 patients
```
GET /fhir/Patient?_count=10&_page=1
```

### Search for a patient by id
```
GET /fhir/Patient?_id=patient-1&_count=10
```

### Search patients by name
```
GET /fhir/Patient?name=John&_count=10
```

### Search female patients, paginated
```
GET /fhir/Patient?gender=female&_count=5&_page=1
```

### Search patients born in 1980
```
GET /fhir/Patient?birthdate=1980&_count=10
```

### Combine search with pagination (offset-based)
```
GET /fhir/Patient?gender=female&_count=1&_offset=0
```

### Search for a specific bundle
```
GET /fhir/Bundle?_id=bundle-1&_count=10
```

### Access resources by path (ID and extra)
You can access a resource by placing the id in the path. Any extra path element after the id is accepted (for example `$summary`) and is treated like a normal search request.
```
GET /fhir/Bundle/bundle-1?_count=10
GET /fhir/Patient/patient-1?_count=10
GET /fhir/Patient/patient-1/$summary?_count=10
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

The `FILES_DIR` environment variable controls where the app loads resources. The server expects one directory per resource type under `FILES_DIR`.

Expected structure (example):

```
$FILES_DIR/
	Bundle/
		bundle1.json
		bundle2.json
	Patient/
		patient1.json
		patient2.json
	Organization/
		org1.json
```

Any resource type present as a folder under `FILES_DIR` becomes available at the matching `<resource_type>` endpoint.

If you prefer to limit what the server will serve, you can either only create the folders you want to expose or add a simple whitelist in `app.py` before returning results.

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

## Extending with new resource types

To add a new resource type:

1. Create a directory named after the resource under `FILES_DIR` (for example `Organization`).
2. Place JSON resource files in that folder (one resource per file).
3. No code changes are required: the dynamic routes `/.../<resource_type>` will serve the new resources automatically.

If you want to add custom behavior for a specific resource type or namespace you can register explicit Flask routes in `app.py` and delegate to the same `fhir_endpoint_impl()` logic.
