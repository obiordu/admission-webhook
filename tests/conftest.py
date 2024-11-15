import pytest
from fastapi.testclient import TestClient
from src.app.main import app
import os
import tempfile
import ssl
from typing import Generator, Dict, Any
import base64
import json

@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application"""
    with TestClient(app) as client:
        yield client

@pytest.fixture
def test_ssl_context() -> Generator[ssl.SSLContext, None, None]:
    """Create a test SSL context with self-signed certificate"""
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
            
            # Create SSL context
            ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_file.name, key_file.name)
            
            yield ssl_context
            
        finally:
            os.unlink(cert_file.name)
            os.unlink(key_file.name)

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Create test configuration"""
    return {
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

@pytest.fixture
def test_admission_request() -> Dict[str, Any]:
    """Create test admission request"""
    return {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "request": {
            "uid": "test-uid",
            "kind": {
                "group": "apps",
                "version": "v1",
                "kind": "Deployment"
            },
            "resource": {
                "group": "apps",
                "version": "v1",
                "resource": "deployments"
            },
            "namespace": "default",
            "operation": "CREATE",
            "userInfo": {
                "username": "test-user",
                "groups": ["system:authenticated"]
            },
            "object": {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "test-deployment",
                    "namespace": "default"
                },
                "spec": {
                    "replicas": 1,
                    "selector": {
                        "matchLabels": {
                            "app": "test"
                        }
                    },
                    "template": {
                        "metadata": {
                            "labels": {
                                "app": "test"
                            }
                        },
                        "spec": {
                            "containers": [{
                                "name": "test-container",
                                "image": "docker.io/test:v1.0.0"
                            }]
                        }
                    }
                }
            }
        }
    }

@pytest.fixture
def sample_pod_request() -> Dict[str, Any]:
    return {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "request": {
            "uid": "test-uid",
            "kind": {"group": "", "version": "v1", "kind": "Pod"},
            "resource": {"group": "", "version": "v1", "kind": "pods"},
            "requestKind": {"group": "", "version": "v1", "kind": "Pod"},
            "requestResource": {"group": "", "version": "v1", "kind": "pods"},
            "name": "test-pod",
            "namespace": "default",
            "operation": "CREATE",
            "userInfo": {
                "username": "test-user",
                "groups": ["system:authenticated"]
            },
            "object": {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": "test-pod",
                    "namespace": "default"
                },
                "spec": {
                    "containers": [{
                        "name": "nginx",
                        "image": "nginx:latest"
                    }]
                }
            }
        }
    }

@pytest.fixture
def sample_deployment_request() -> Dict[str, Any]:
    return {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "request": {
            "uid": "test-uid",
            "kind": {"group": "apps", "version": "v1", "kind": "Deployment"},
            "resource": {"group": "apps", "version": "v1", "kind": "deployments"},
            "requestKind": {"group": "apps", "version": "v1", "kind": "Deployment"},
            "requestResource": {"group": "apps", "version": "v1", "kind": "deployments"},
            "name": "test-deployment",
            "namespace": "default",
            "operation": "CREATE",
            "userInfo": {
                "username": "test-user",
                "groups": ["system:authenticated"]
            },
            "object": {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "test-deployment",
                    "namespace": "default"
                },
                "spec": {
                    "replicas": 1,
                    "selector": {
                        "matchLabels": {
                            "app": "test"
                        }
                    },
                    "template": {
                        "metadata": {
                            "labels": {
                                "app": "test"
                            }
                        },
                        "spec": {
                            "containers": [{
                                "name": "nginx",
                                "image": "nginx:latest"
                            }]
                        }
                    }
                }
            }
        }
    }

@pytest.fixture
def encode_json_patch():
    def _encode(patch: list) -> str:
        return base64.b64encode(json.dumps(patch).encode()).decode()
    return _encode
