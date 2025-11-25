import os
import pytest

# Ensure the app uses the test resources directory for files
TEST_RESOURCES = os.path.join(os.path.dirname(__file__), 'resources')
os.environ['FILES_DIR'] = TEST_RESOURCES

from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'FHIR Emulator' in resp.data


def test_fhir_bundle_count_zero(client):
    resp = client.get('/fhir/Bundle?_count=0')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'].startswith('application/fhir+json')
    data = resp.get_json()
    # should include total and no entries key
    assert 'total' in data
    assert 'entry' not in data


def test_fhir_bundle_with_entries(client):
    resp = client.get('/fhir/Bundle?_count=1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] >= 0
    assert 'entry' in data
    assert len(data['entry']) <= 1


def test_fhir_bundle_paging_links(client):
    # total should be >=3; request page size 1 to force links
    resp = client.get('/fhir/Bundle?_count=1&_page=1', follow_redirects=True)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'link' in data
    rels = {l['relation'] for l in data['link']}
    assert 'self' in rels
    assert 'next' in rels
    # prev should not be on the first page
    assert 'prev' not in rels

    # middle page should have prev and next
    resp2 = client.get('/fhir/Bundle?_count=1&_page=2')
    data2 = resp2.get_json()
    rels2 = {l['relation'] for l in data2['link']}
    assert 'prev' in rels2 and 'next' in rels2




def test_fhir_patient_count_zero(client):
    resp = client.get('/fhir/Patient?_count=0')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'total' in data
    assert 'entry' not in data


def test_fhir_patient_with_entries(client):
    resp = client.get('/fhir/Patient?_count=1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] >= 0
    assert 'entry' in data
    assert len(data['entry']) <= 1


def test_fhir_patient_count_two(client):
    # Explicitly request 2 resources
    resp = client.get('/fhir/Patient?_count=2')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 3  # total 3 patients in test data
    assert 'entry' in data
    assert len(data['entry']) == 2  # but return only 2


def test_fhir_bundle_default_pagination(client):
    # No paging params: should return first 10 (default) with links
    resp = client.get('/fhir/Bundle')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 3  # total 3 bundles
    assert 'entry' in data
    assert len(data['entry']) == 3  # all fit in default 10
    assert 'link' in data  # should have pagination links


def test_fhir_patient_paging_links(client):
    resp = client.get('/fhir/Patient?_count=1&_page=1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'link' in data
    rels = {l['relation'] for l in data['link']}
    assert 'self' in rels
    assert 'next' in rels
    assert 'prev' not in rels
    resp2 = client.get('/fhir/Patient?_count=1&_page=3')
    data2 = resp2.get_json()
    rels2 = {l['relation'] for l in data2['link']}
    # last page should have prev and last
    assert 'prev' in rels2 and 'last' in rels2


def test_fhir_bundle_search_by_id(client):
    # Search for a specific bundle by id
    resp = client.get('/fhir/Bundle?_id=bundle-1&_count=10')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert len(data['entry']) == 1
    assert data['entry'][0]['resource']['id'] == 'bundle-1'


def test_fhir_patient_search_by_id(client):
    # Search for a specific patient by id
    resp = client.get('/fhir/Patient?_id=patient-1&_count=10')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert len(data['entry']) == 1
    assert data['entry'][0]['resource']['id'] == 'patient-1'


def test_fhir_patient_search_by_name(client):
    # Search for patients by name substring
    resp = client.get('/fhir/Patient?name=John&_count=10')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] >= 1
    # patient-1 has given name "John"
    ids = [e['resource']['id'] for e in data['entry']]
    assert 'patient-1' in ids


def test_fhir_patient_search_by_gender(client):
    # Search for patients by gender
    resp = client.get('/fhir/Patient?gender=female&_count=10')
    assert resp.status_code == 200
    data = resp.get_json()
    # patient-2 and patient-3 are female
    assert data['total'] == 2
    for entry in data['entry']:
        assert entry['resource']['gender'] == 'female'


def test_fhir_patient_search_by_birthdate(client):
    # Search for patients by birthdate prefix
    resp = client.get('/fhir/Patient?birthdate=1980&_count=10')
    assert resp.status_code == 200
    data = resp.get_json()
    # patient-1 has birthDate "1980-01-01"
    assert data['total'] == 1
    assert data['entry'][0]['resource']['id'] == 'patient-1'


def test_fhir_patient_search_no_results(client):
    # Search with no matches
    resp = client.get('/fhir/Patient?_id=nonexistent&_count=10')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 0
    assert 'entry' not in data or len(data.get('entry', [])) == 0


def test_fhir_patient_search_with_pagination(client):
    # Search and paginate results
    resp = client.get('/fhir/Patient?gender=female&_count=1&_page=1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 2
    assert len(data['entry']) == 1
    # should have next link
    assert 'link' in data
    rels = {l['relation'] for l in data['link']}
    assert 'next' in rels


def test_fhir_bundle_path_id(client):
    # Access bundle by path: /Bundle/{id}
    resp = client.get('/fhir/Bundle/bundle-1?_count=10')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert len(data['entry']) == 1
    assert data['entry'][0]['resource']['id'] == 'bundle-1'


def test_fhir_patient_path_id(client):
    # Access patient by path: /Patient/{id}
    resp = client.get('/fhir/Patient/patient-1?_count=10')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert len(data['entry']) == 1
    assert data['entry'][0]['resource']['id'] == 'patient-1'


def test_fhir_patient_path_id_with_summary(client):
    # Access patient with summary: /Patient/{id}/$summary
    # Should behave the same as /Patient/{id} since JSON already contains summary
    resp = client.get('/fhir/Patient/patient-2/$summary?_count=10')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert len(data['entry']) == 1
    assert data['entry'][0]['resource']['id'] == 'patient-2'


def test_fhir_patient_path_id_not_found(client):
    # Request a patient that doesn't exist via path
    resp = client.get('/fhir/Patient/nonexistent?_count=10')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 0
    assert 'entry' not in data or len(data.get('entry', [])) == 0


def test_fhir_bundle_path_id_count_zero(client):
    # Path ID with count=0 should still work
    resp = client.get('/fhir/Bundle/bundle-1?_count=0')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'total' in data
    assert 'entry' not in data

