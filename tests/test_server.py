from fastapi.testclient import TestClient

from backend.server import app

client = TestClient(app)


def test_health_endpoint():
  response = client.get('/health')
  assert response.status_code == 200
  payload = response.json()
  assert payload['status'] == 'ok'
  assert 'request_id' in payload


def test_rejects_relative_paths():
  response = client.post('/convert', json={'files': ['relative/path.txt']})

  assert response.status_code == 422


def test_convert_unsupported_file(tmp_path):
  unsupported = tmp_path / 'sample.pdf'
  unsupported.write_text('fake content')

  response = client.post('/convert', json={'files': [str(unsupported)]})
  payload = response.json()

  assert response.status_code == 200
  assert payload['results'][0]['status'] == 'error'
  assert 'Unsupported format' in payload['results'][0]['message']


def test_convert_text_file(tmp_path):
  text_file = tmp_path / 'sample.txt'
  text_file.write_text('hello world')

  response = client.post('/convert', json={'files': [str(text_file)]})
  payload = response.json()

  assert response.status_code == 200
  assert 'request_id' in payload
  result = payload['results'][0]
  assert result['status'] == 'ok'
  assert result['content']['length'] == 11
  assert 'hello world' in result['content']['preview']
