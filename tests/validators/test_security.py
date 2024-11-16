import pytest
from src.validators.security import SecurityContextValidator

@pytest.fixture
def validator():
    return SecurityContextValidator()

def test_supports_pod():
    validator = SecurityContextValidator()
    request = {"request": {"kind": {"kind": "Pod"}}}
    assert validator.supports(request) is True

def test_supports_deployment():
    validator = SecurityContextValidator()
    request = {"request": {"kind": {"kind": "Deployment"}}}
    assert validator.supports(request) is True

def test_not_supports_other():
    validator = SecurityContextValidator()
    request = {"request": {"kind": {"kind": "Service"}}}
    assert validator.supports(request) is False

def test_validate_privileged_container():
    validator = SecurityContextValidator(enforce_privileged=True)
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "securityContext": {
                            "privileged": True
                        }
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "Privileged containers are not allowed" in result.message

def test_validate_root_user():
    validator = SecurityContextValidator(enforce_non_root=True)
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "securityContext": {
                            "runAsUser": 0
                        }
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "Running as root is not allowed" in result.message

def test_validate_host_network():
    validator = SecurityContextValidator(enforce_host_network=True)
    request = {
        "object": {
            "spec": {
                "hostNetwork": True,
                "containers": [
                    {
                        "name": "test-container"
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "Host network access is not allowed" in result.message

def test_validate_readonly_root():
    validator = SecurityContextValidator(enforce_readonly_root=True)
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "securityContext": {
                            "readOnlyRootFilesystem": False
                        }
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "Read-only root filesystem is required" in result.message

def test_validate_multiple_containers():
    validator = SecurityContextValidator(
        enforce_privileged=True,
        enforce_non_root=True,
        enforce_readonly_root=True
    )
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "container1",
                        "securityContext": {
                            "privileged": False,
                            "runAsUser": 1000,
                            "readOnlyRootFilesystem": True
                        }
                    },
                    {
                        "name": "container2",
                        "securityContext": {
                            "privileged": True,
                            "runAsUser": 0,
                            "readOnlyRootFilesystem": False
                        }
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert any(msg in result.message for msg in [
        "Privileged containers are not allowed",
        "Running as root is not allowed",
        "Read-only root filesystem is required"
    ])

def test_validate_no_security_context():
    validator = SecurityContextValidator()
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container"
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is True
