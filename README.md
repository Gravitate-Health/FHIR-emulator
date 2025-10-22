# Simple FHIR Emulator


This is a minimal Flask-based FHIR emulator exposing two endpoints:

- `/epi/api/fhir/Bundle` - accepts `_count` query param. If `_count=0` returns a FHIR Bundle with `total` set to the number of matching resources but no `entry` or paging links. If `_count>0` returns up to `_count` resource entries loaded from `files/Bundle/*.json`.
- `/ips/api/fhir/Patient` - same behavior but loads resources from `files/Patient/*.json`.

The purpose of this module is to provide ePIs and IPS in a lightweight manner for testing and developing purposes of the FOSPS system.

## Running
Run locally:

```
pip install -r requirements.txt
python app.py
```

Build and run with Docker (bind local `files/` as a volume):

```
docker build -t fhir-emulator .
docker run -p 5000:5000 -v ${PWD}:/app -e FILES_DIR=/app/files fhir-emulator
```

Or use a host directory for resources:

```
docker run -p 5000:5000 -v C:\path\to\your\resources:\resources -e FILES_DIR=\resources fhir-emulator
```
## Testing
Run tests:

```
pytest -q
```
