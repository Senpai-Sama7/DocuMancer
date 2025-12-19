from pathlib import Path

from fastapi.testclient import TestClient

from backend.server import app


def test_health_check():
  client = TestClient(app)
  response = client.get('/health')
  assert response.status_code == 200
  assert response.json() == {'status': 'ok'}


def test_convert_reads_files(tmp_path):
  sample = Path('tests/data/sample.txt').resolve()
  assert sample.exists()
  client = TestClient(app)
  response = client.post('/convert', json={'files': [str(sample)]})
  assert response.status_code == 200
  payload = response.json()
  assert payload['results'][0]['name'] == 'sample.txt'
  assert 'Hello DocuMancer' in payload['results'][0]['content']
