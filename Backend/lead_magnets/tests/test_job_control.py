import time
import uuid
import threading
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from lead_magnets.models import LeadMagnet, LeadMagnetGeneration
from accounts.models import User

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_user(db):
    user = User.objects.create_user(email="test@example.com", password="password")
    return user

@pytest.fixture
def lead_magnet(test_user):
    lm = LeadMagnet.objects.create(title="Test LM", owner=test_user)
    LeadMagnetGeneration.objects.create(
        lead_magnet=lm,
        main_topic="Architecture",
        target_audience="Homeowners",
        audience_pain_points=["Cost"],
        desired_outcome="Save money",
        call_to_action="Contact us",
        lead_magnet_type="guide"
    )
    return lm

@pytest.mark.django_db
def test_job_cancellation(api_client, test_user, lead_magnet):
    api_client.force_authenticate(user=test_user)
    
    # 1. Start a job
    start_url = reverse('generate_pdf_start')
    response = api_client.post(start_url, {"lead_magnet_id": lead_magnet.id, "template_id": "modern-guide"})
    assert response.status_code == 202
    job_id = response.data['job_id']
    
    # 2. Verify job is running (status might be pending or processing)
    status_url = reverse('generate_pdf_status', kwargs={'job_id': job_id})
    response = api_client.get(status_url)
    assert response.data['status'] in ('pending', 'processing')
    
    # 3. Start a NEW job for the same Lead Magnet (should cancel the first)
    response = api_client.post(start_url, {"lead_magnet_id": lead_magnet.id, "template_id": "modern-guide"})
    assert response.status_code == 202
    new_job_id = response.data['job_id']
    assert new_job_id != job_id
    
    # 4. Check first job status (should be cancelled)
    # We might need a tiny sleep to allow the thread to pick up the cancellation
    time.sleep(0.5)
    response = api_client.get(status_url)
    assert response.data['status'] == 'cancelled'
    
    # 5. Stop the new job manually
    stop_url = reverse('generate_pdf_stop', kwargs={'job_id': new_job_id})
    response = api_client.post(stop_url)
    assert response.status_code == 200
    
    # 6. Check new job status (should be terminated)
    time.sleep(0.5)
    new_status_url = reverse('generate_pdf_status', kwargs={'job_id': new_job_id})
    response = api_client.get(new_status_url)
    assert response.data['status'] == 'terminated'
