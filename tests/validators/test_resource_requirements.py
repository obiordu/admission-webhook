import pytest
from src.validators.resource_requirements import ResourceRequirementsValidator

@pytest.fixture
def validator():
    return ResourceRequirementsValidator()

def test_supports_pod():
    validator = ResourceRequirementsValidator()
    request = {"request": {"kind": {"kind": "Pod"}}}
    assert validator.supports(request) is True

def test_supports_deployment():
    validator = ResourceRequirementsValidator()
    request = {"request": {"kind": {"kind": "Deployment"}}}
    assert validator.supports(request) is True

def test_not_supports_other():
    validator = ResourceRequirementsValidator()
    request = {"request": {"kind": {"kind": "Service"}}}
    assert validator.supports(request) is False

def test_validate_valid_resources():
    validator = ResourceRequirementsValidator()
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "resources": {
                            "limits": {
                                "cpu": "1",
                                "memory": "512Mi"
                            },
                            "requests": {
                                "cpu": "100m",
                                "memory": "128Mi"
                            }
                        }
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is True

def test_validate_missing_resources():
    validator = ResourceRequirementsValidator()
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "resources": {}
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "must specify resource requirements" in result.message

def test_validate_missing_cpu_limits():
    validator = ResourceRequirementsValidator()
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "resources": {
                            "limits": {
                                "memory": "512Mi"
                            },
                            "requests": {
                                "cpu": "100m",
                                "memory": "128Mi"
                            }
                        }
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "must specify CPU limits" in result.message

def test_validate_missing_memory_limits():
    validator = ResourceRequirementsValidator()
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "resources": {
                            "limits": {
                                "cpu": "1"
                            },
                            "requests": {
                                "cpu": "100m",
                                "memory": "128Mi"
                            }
                        }
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "must specify memory limits" in result.message

def test_validate_invalid_pod_spec():
    validator = ResourceRequirementsValidator()
    request = {"object": {}}
    result = validator._validate(request)
    assert result.allowed is False
    assert "Invalid pod specification" in result.message

def test_validate_no_enforce_limits():
    validator = ResourceRequirementsValidator(enforce_limits=False)
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "resources": {}
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is True
