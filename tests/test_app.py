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
    resp = client.get('/epi/api/fhir/Bundle?_count=0')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'].startswith('application/fhir+json')
    data = resp.get_json()
    # should include total and no entries key
    assert 'total' in data
    assert 'entry' not in data


def test_fhir_bundle_with_entries(client):
    resp = client.get('/epi/api/fhir/Bundle?_count=1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] >= 0
    assert 'entry' in data
    assert len(data['entry']) <= 1


def test_fhir_bundle_paging_links(client):
    # total should be >=3; request page size 1 to force links
    resp = client.get('/epi/api/fhir/Bundle?_count=1&_page=1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'link' in data
    rels = {l['relation'] for l in data['link']}
    assert 'self' in rels
    assert 'next' in rels
    # prev should not be on the first page
    assert 'prev' not in rels

    # middle page should have prev and next
    resp2 = client.get('/epi/api/fhir/Bundle?_count=1&_page=2')
    data2 = resp2.get_json()
    rels2 = {l['relation'] for l in data2['link']}
    assert 'prev' in rels2 and 'next' in rels2




def test_fhir_patient_count_zero(client):
    resp = client.get('/ips/api/fhir/Patient?_count=0')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'total' in data
    assert 'entry' not in data


def test_fhir_patient_with_entries(client):
    resp = client.get('/ips/api/fhir/Patient?_count=1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] >= 0
    assert 'entry' in data
    assert len(data['entry']) <= 1


def test_fhir_patient_paging_links(client):
    resp = client.get('/ips/api/fhir/Patient?_count=1&_page=1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'link' in data
    rels = {l['relation'] for l in data['link']}
    assert 'self' in rels
    assert 'next' in rels
    assert 'prev' not in rels
    resp2 = client.get('/ips/api/fhir/Patient?_count=1&_page=3')
    data2 = resp2.get_json()
    rels2 = {l['relation'] for l in data2['link']}
    # last page should have prev and last
    assert 'prev' in rels2 and 'last' in rels2
