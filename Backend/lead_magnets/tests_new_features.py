
import pytest
from Backend.lead_magnets.groq_client import GroqClient

@pytest.fixture
def groq_client():
    return GroqClient()

def test_render_image(groq_client):
    url = "https://example.com/image.jpg"
    alt = "Test Image"
    html = groq_client.render_image(url, alt)
    
    assert '<picture' in html
    assert 'srcset="https://example.com/image.jpg"' in html
    assert 'alt="Test Image"' in html
    assert 'aspect-ratio: 16/9' in html
    assert 'loading="lazy"' in html

def test_render_image_no_url(groq_client):
    assert groq_client.render_image("") == ""

def test_theme_palette_endpoint(client, db):
    # This assumes you have a user and firm profile set up in your test DB
    from django.contrib.auth.models import User
    from Backend.lead_magnets.models import FirmProfile
    
    user = User.objects.create_user(username='testuser', password='password')
    FirmProfile.objects.create(user=user, primary_brand_color="#FF0000")
    
    client.login(username='testuser', password='password')
    response = client.get('/api/theme/')
    
    assert response.status_code == 200
    data = response.json()
    assert data['primary'] == "#FF0000"
    assert data['surface'] == "#ffffff"

def test_theme_palette_dark_mode(client, db):
    from django.contrib.auth.models import User
    user = User.objects.create_user(username='darkuser', password='password')
    client.login(username='darkuser', password='password')
    
    response = client.get('/api/theme/?mode=dark')
    assert response.status_code == 200
    data = response.json()
    assert data['surface'] == "#1a202c"
