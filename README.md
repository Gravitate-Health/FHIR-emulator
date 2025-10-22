# Simple Flask server


This is a minimal Flask-based FHIR emulator exposing two endpoints:

- `/epi/api/fhir/Bundle` - accepts `_count` query param. If `_count=0` returns a FHIR Bundle with `total` set to the number of matching resources but no `entry` or paging links. If `_count>0` returns up to `_count` resource entries loaded from `files/Bundle/*.json`.
- `/ips/api/fhir/Patient` - same behavior but loads resources from `files/Patient/*.json`.

Run locally (PowerShell):

```powershell
python -m venv .venv
\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Build and run with Docker (bind local `files/` as a volume):

```powershell
docker build -t fhir-emulator:local .
docker run -p 5000:5000 -v ${PWD}:/app -e FILES_DIR=/app/files fhir-emulator:local
```

Or use a host directory for resources:

```powershell
docker run -p 5000:5000 -v C:\path\to\your\resources:C:\resources -e FILES_DIR=C:\resources fhir-emulator:local
```

Run tests:

```powershell
\.venv\Scripts\Activate.ps1
pytest -q
```
