import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any

def test_health_check(test_client: TestClient):
    """Test health check endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_readiness_check(test_client: TestClient):
    """Test readiness check endpoint"""
    response = test_client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

def test_validate_pod(test_client: TestClient, sample_pod_request: Dict[str, Any]):
    """Test pod validation"""
    response = test_client.post("/validate", json=sample_pod_request)
    assert response.status_code == 200
    
    data = response.json()
    assert data["apiVersion"] == "admission.k8s.io/v1"
    assert data["kind"] == "AdmissionReview"
    assert data["response"]["allowed"] is True
    assert data["response"]["uid"] == sample_pod_request["request"]["uid"]

def test_validate_deployment(test_client: TestClient, sample_deployment_request: Dict[str, Any]):
    """Test deployment validation"""
    response = test_client.post("/validate", json=sample_deployment_request)
    assert response.status_code == 200
    
    data = response.json()
    assert data["apiVersion"] == "admission.k8s.io/v1"
    assert data["kind"] == "AdmissionReview"
    assert data["response"]["allowed"] is True
    assert data["response"]["uid"] == sample_deployment_request["request"]["uid"]

def test_validate_invalid_request(test_client: TestClient):
    """Test validation with invalid request"""
    invalid_request = {"invalid": "request"}
    response = test_client.post("/validate", json=invalid_request)
    assert response.status_code == 400

def test_mutate_pod(test_client: TestClient, sample_pod_request: Dict[str, Any]):
    """Test pod mutation"""
    response = test_client.post("/mutate", json=sample_pod_request)
    assert response.status_code == 200
    
    data = response.json()
    assert data["apiVersion"] == "admission.k8s.io/v1"
    assert data["kind"] == "AdmissionReview"
    assert data["response"]["allowed"] is True
    assert data["response"]["uid"] == sample_pod_request["request"]["uid"]
    assert "patchType" in data["response"]
    assert data["response"]["patchType"] == "JSONPatch"

def test_mutate_deployment(test_client: TestClient, sample_deployment_request: Dict[str, Any]):
    """Test deployment mutation"""
    response = test_client.post("/mutate", json=sample_deployment_request)
    assert response.status_code == 200
    
    data = response.json()
    assert data["apiVersion"] == "admission.k8s.io/v1"
    assert data["kind"] == "AdmissionReview"
    assert data["response"]["allowed"] is True
    assert data["response"]["uid"] == sample_deployment_request["request"]["uid"]
    assert "patchType" in data["response"]
    assert data["response"]["patchType"] == "JSONPatch"

def test_mutate_invalid_request(test_client: TestClient):
    """Test mutation with invalid request"""
    invalid_request = {"invalid": "request"}
    response = test_client.post("/mutate", json=invalid_request)
    assert response.status_code == 400
