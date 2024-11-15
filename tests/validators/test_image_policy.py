import pytest
from src.validators.image_policy import ImagePolicyValidator

@pytest.fixture
def validator():
    return ImagePolicyValidator()

def test_supports_pod():
    validator = ImagePolicyValidator()
    request = {"request": {"kind": {"kind": "Pod"}}}
    assert validator.supports(request) is True

def test_supports_deployment():
    validator = ImagePolicyValidator()
    request = {"request": {"kind": {"kind": "Deployment"}}}
    assert validator.supports(request) is True

def test_not_supports_other():
    validator = ImagePolicyValidator()
    request = {"request": {"kind": {"kind": "Service"}}}
    assert validator.supports(request) is False

def test_validate_allowed_registry():
    validator = ImagePolicyValidator(allowed_registries=["docker.io"])
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "image": "docker.io/nginx:1.19"
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is True

def test_validate_disallowed_registry():
    validator = ImagePolicyValidator(allowed_registries=["docker.io"])
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "image": "gcr.io/test/image:v1"
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "Image registry not allowed" in result.message

def test_validate_latest_tag():
    validator = ImagePolicyValidator(deny_latest_tag=True)
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "image": "nginx:latest"
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "Latest tag is not allowed" in result.message

def test_validate_no_tag():
    validator = ImagePolicyValidator(deny_latest_tag=True)
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "image": "nginx"
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "Latest tag is not allowed" in result.message

def test_validate_multiple_containers():
    validator = ImagePolicyValidator(allowed_registries=["docker.io"], deny_latest_tag=True)
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "container1",
                        "image": "docker.io/nginx:1.19"
                    },
                    {
                        "name": "container2",
                        "image": "gcr.io/test/image:v1"
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "Image registry not allowed" in result.message

def test_validate_invalid_image_format():
    validator = ImagePolicyValidator()
    request = {
        "object": {
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "image": ""
                    }
                ]
            }
        }
    }
    result = validator._validate(request)
    assert result.allowed is False
    assert "Invalid image format" in result.message
