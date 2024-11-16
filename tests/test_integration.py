import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from src.app.main import app
import logging
import ssl
import tempfile
import os
from typing import Dict, Any

def test_metrics_collection(test_client: TestClient):
    """Test Prometheus metrics collection"""
    # Make some requests to generate metrics
    test_client.get("/health")
    test_client.get("/ready")
    
    # Get metrics
    response = test_client.get("/metrics")
    assert response.status_code == 200
    
    # Verify specific metrics exist
    metrics_text = response.text
    assert "webhook_requests_total" in metrics_text
    assert "webhook_request_duration_seconds" in metrics_text
    assert "webhook_response_status" in metrics_text

def test_logging_configuration(caplog, test_client: TestClient):
    """Test logging functionality"""
    with caplog.at_level(logging.INFO):
        test_client.get("/health")
        
        # Verify log messages
        assert any("Health check request received" in record.message 
                  for record in caplog.records)
        assert any("Health check response sent" in record.message 
                  for record in caplog.records)

def test_tls_certificate_handling():
    """Test TLS certificate handling"""
    # Create temporary certificate files
    with tempfile.NamedTemporaryFile(delete=False) as cert_file, \
         tempfile.NamedTemporaryFile(delete=False) as key_file:
        try:
            # Generate self-signed certificate
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            import datetime
            
            # Generate key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Generate certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost")
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow()
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=1)
            ).sign(private_key, hashes.SHA256())
            
            # Write certificate and key to files
            cert_file.write(cert.public_bytes(serialization.Encoding.PEM))
            key_file.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
            cert_file.flush()
            key_file.flush()
            
            # Create SSL context with the certificate
            ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_file.name, key_file.name)
            
            # Verify SSL context
            assert ssl_context.get_ca_certs() == []
            
        finally:
            # Clean up temporary files
            os.unlink(cert_file.name)
            os.unlink(key_file.name)

def test_configuration_loading():
    """Test configuration loading from environment variables"""
    test_config = {
        "LOG_LEVEL": "DEBUG",
        "METRICS_ENABLED": "true",
        "VALIDATION_ENABLED": "true",
        "MUTATION_ENABLED": "true",
        "ALLOWED_REGISTRIES": "docker.io,gcr.io",
        "DENY_LATEST_TAG": "true",
        "ENFORCE_NON_ROOT": "true",
        "ENFORCE_READONLY_ROOT": "true",
        "ENFORCE_PRIVILEGED": "true",
        "ENFORCE_RESOURCE_LIMITS": "true"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as env_file:
        try:
            # Write test configuration to file
            for key, value in test_config.items():
                env_file.write(f"{key}={value}\n")
            env_file.flush()
            
            # Load configuration
            from src.app.config import load_config
            config = load_config(env_file.name)
            
            # Verify configuration
            assert config.log_level == "DEBUG"
            assert config.metrics_enabled is True
            assert config.validation_enabled is True
            assert config.mutation_enabled is True
            assert "docker.io" in config.allowed_registries
            assert "gcr.io" in config.allowed_registries
            assert config.deny_latest_tag is True
            assert config.enforce_non_root is True
            assert config.enforce_readonly_root is True
            assert config.enforce_privileged is True
            assert config.enforce_resource_limits is True
            
        finally:
            os.unlink(env_file.name)

def test_error_handling(test_client: TestClient):
    """Test error handling"""
    # Test invalid JSON
    response = test_client.post("/validate", json={"invalid": "request"})
    assert response.status_code == 400
    assert "error" in response.json()
    
    # Test missing required fields
    response = test_client.post("/validate", json={
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview"
    })
    assert response.status_code == 400
    assert "error" in response.json()
    
    # Test invalid content type
    response = test_client.post("/validate", data="not json")
    assert response.status_code == 400
    assert "error" in response.json()
