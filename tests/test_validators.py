import pytest
from src.validators.security import SecurityContextValidator, ImagePolicyValidator, ResourceRequirementsValidator
from typing import Dict, Any

def test_security_context_validator_privileged(sample_pod_request: Dict[str, Any]):
    """Test privileged container validation"""
    validator = SecurityContextValidator(enforce_privileged=True)
    
    # Add privileged security context
    sample_pod_request["request"]["object"]["spec"]["containers"][0]["securityContext"] = {
        "privileged": True
    }
    
    result = validator.validate(sample_pod_request)
    assert not result.allowed
    assert "Privileged containers are not allowed" in result.message

def test_security_context_validator_root(sample_pod_request: Dict[str, Any]):
    """Test root user validation"""
    validator = SecurityContextValidator(enforce_non_root=True)
    
    # Add root user security context
    sample_pod_request["request"]["object"]["spec"]["containers"][0]["securityContext"] = {
        "runAsUser": 0
    }
    
    result = validator.validate(sample_pod_request)
    assert not result.allowed
    assert "Running as root is not allowed" in result.message

def test_security_context_validator_host_network(sample_pod_request: Dict[str, Any]):
    """Test host network validation"""
    validator = SecurityContextValidator(enforce_host_network=True)
    
    # Add host network
    sample_pod_request["request"]["object"]["spec"]["hostNetwork"] = True
    
    result = validator.validate(sample_pod_request)
    assert not result.allowed
    assert "Host network access is not allowed" in result.message

def test_image_policy_validator_registry(sample_pod_request: Dict[str, Any]):
    """Test image registry validation"""
    validator = ImagePolicyValidator(allowed_registries=["docker.io"])
    
    # Use disallowed registry
    sample_pod_request["request"]["object"]["spec"]["containers"][0]["image"] = "gcr.io/test/image:v1"
    
    result = validator.validate(sample_pod_request)
    assert not result.allowed
    assert "Image registry not allowed" in result.message

def test_image_policy_validator_latest_tag(sample_pod_request: Dict[str, Any]):
    """Test latest tag validation"""
    validator = ImagePolicyValidator(deny_latest_tag=True)
    
    # Use latest tag
    sample_pod_request["request"]["object"]["spec"]["containers"][0]["image"] = "nginx:latest"
    
    result = validator.validate(sample_pod_request)
    assert not result.allowed
    assert "Latest tag is not allowed" in result.message

def test_resource_requirements_validator(sample_pod_request: Dict[str, Any]):
    """Test resource requirements validation"""
    validator = ResourceRequirementsValidator(enforce_limits=True)
    
    # Remove resource limits
    container = sample_pod_request["request"]["object"]["spec"]["containers"][0]
    container.pop("resources", None)
    
    result = validator.validate(sample_pod_request)
    assert not result.allowed
    assert "Resource limits are required" in result.message

def test_resource_requirements_validator_with_limits(sample_pod_request: Dict[str, Any]):
    """Test resource requirements validation with valid limits"""
    validator = ResourceRequirementsValidator(enforce_limits=True)
    
    # Add valid resource limits
    container = sample_pod_request["request"]["object"]["spec"]["containers"][0]
    container["resources"] = {
        "limits": {
            "cpu": "1",
            "memory": "1Gi"
        },
        "requests": {
            "cpu": "100m",
            "memory": "128Mi"
        }
    }
    
    result = validator.validate(sample_pod_request)
    assert result.allowed

def test_validator_chain(sample_pod_request: Dict[str, Any]):
    """Test validator chain execution"""
    validators = [
        SecurityContextValidator(enforce_privileged=True),
        ImagePolicyValidator(allowed_registries=["docker.io"]),
        ResourceRequirementsValidator(enforce_limits=True)
    ]
    
    # Add violations for each validator
    container = sample_pod_request["request"]["object"]["spec"]["containers"][0]
    container["securityContext"] = {"privileged": True}
    container["image"] = "gcr.io/test/image:v1"
    container.pop("resources", None)
    
    for validator in validators:
        result = validator.validate(sample_pod_request)
        assert not result.allowed
