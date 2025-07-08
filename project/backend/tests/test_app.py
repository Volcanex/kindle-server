"""
Basic application tests
"""

def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'kindle-content-server'

def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get('/')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['service'] == 'Kindle Content Server Backend'
    assert 'endpoints' in data

def test_404_handling(client):
    """Test 404 error handling."""
    response = client.get('/nonexistent')
    assert response.status_code == 404
    
    data = response.get_json()
    assert 'error' in data