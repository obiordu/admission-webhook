import pytest
from src.mutators.defaults import (
    DefaultLabelsAnnotationsMutator,
    DefaultSecurityContextMutator,
    DefaultResourcesMutator
)
from src.schemas.admission import AdmissionReview, AdmissionRequest, GroupVersionKind

@pytest.fixture
def admission_request():
    return AdmissionRequest(
        uid="test-uid",
        kind=GroupVersionKind(group="", version="v1", kind="Pod"),
        operation="CREATE",
        object={
            "metadata": {},
            "spec": {
                "containers": [
                    {
                        "name": "test-container",
                        "image": "nginx:latest"
                    }
                ]
            }
        }
    )

@pytest.fixture
def admission_review(admission_request):
    return AdmissionReview(request=admission_request)

def test_default_labels_annotations_mutator():
    # Test setup
    default_labels = {"environment": "test", "app": "webhook"}
    default_annotations = {"description": "test-pod", "owner": "test-user"}
    mutator = DefaultLabelsAnnotationsMutator(default_labels, default_annotations)
    
    # Test Pod mutation
    pod_review = AdmissionReview(request=AdmissionRequest(
        uid="test-uid",
        kind=GroupVersionKind(group="", version="v1", kind="Pod"),
        operation="CREATE",
        object={
            "metadata": {},
            "spec": {
                "containers": [{"name": "test-container"}]
            }
        }
    ))
    
    result = mutator.mutate(pod_review)
    assert result.mutated
    assert result.patched["metadata"]["labels"] == default_labels
    assert result.patched["metadata"]["annotations"] == default_annotations
    
    # Test Deployment mutation
    deployment_review = AdmissionReview(request=AdmissionRequest(
        uid="test-uid",
        kind=GroupVersionKind(group="apps", version="v1", kind="Deployment"),
        operation="CREATE",
        object={
            "metadata": {},
            "spec": {
                "template": {
                    "metadata": {},
                    "spec": {
                        "containers": [{"name": "test-container"}]
                    }
                }
            }
        }
    ))
    
    result = mutator.mutate(deployment_review)
    assert result.mutated
    assert result.patched["metadata"]["labels"] == default_labels
    assert result.patched["metadata"]["annotations"] == default_annotations
    assert result.patched["spec"]["template"]["metadata"]["labels"] == default_labels
    assert result.patched["spec"]["template"]["metadata"]["annotations"] == default_annotations

def test_default_security_context_mutator():
    # Test setup
    mutator = DefaultSecurityContextMutator(
        run_as_non_root=True,
        read_only_root_filesystem=True,
        run_as_user=1000,
        run_as_group=2000,
        fs_group=3000
    )
    
    # Test Pod mutation
    pod_review = AdmissionReview(request=AdmissionRequest(
        uid="test-uid",
        kind=GroupVersionKind(group="", version="v1", kind="Pod"),
        operation="CREATE",
        object={
            "metadata": {},
            "spec": {
                "containers": [{"name": "test-container"}]
            }
        }
    ))
    
    result = mutator.mutate(pod_review)
    assert result.mutated
    
    # Verify pod security context
    pod_security_context = result.patched["spec"]["securityContext"]
    assert pod_security_context["runAsNonRoot"] is True
    assert pod_security_context["runAsUser"] == 1000
    assert pod_security_context["runAsGroup"] == 2000
    assert pod_security_context["fsGroup"] == 3000
    
    # Verify container security context
    container_security_context = result.patched["spec"]["containers"][0]["securityContext"]
    assert container_security_context["runAsNonRoot"] is True
    assert container_security_context["readOnlyRootFilesystem"] is True
    assert container_security_context["allowPrivilegeEscalation"] is False
    assert container_security_context["runAsUser"] == 1000
    assert container_security_context["runAsGroup"] == 2000

def test_default_resources_mutator():
    # Test setup
    default_requests = {"cpu": "100m", "memory": "128Mi"}
    default_limits = {"cpu": "200m", "memory": "256Mi"}
    mutator = DefaultResourcesMutator(default_requests, default_limits)
    
    # Test Pod mutation
    pod_review = AdmissionReview(request=AdmissionRequest(
        uid="test-uid",
        kind=GroupVersionKind(group="", version="v1", kind="Pod"),
        operation="CREATE",
        object={
            "metadata": {},
            "spec": {
                "containers": [{"name": "test-container"}]
            }
        }
    ))
    
    result = mutator.mutate(pod_review)
    assert result.mutated
    
    # Verify container resources
    container_resources = result.patched["spec"]["containers"][0]["resources"]
    assert container_resources["requests"] == default_requests
    assert container_resources["limits"] == default_limits
    
    # Test Deployment mutation
    deployment_review = AdmissionReview(request=AdmissionRequest(
        uid="test-uid",
        kind=GroupVersionKind(group="apps", version="v1", kind="Deployment"),
        operation="CREATE",
        object={
            "metadata": {},
            "spec": {
                "template": {
                    "metadata": {},
                    "spec": {
                        "containers": [{"name": "test-container"}]
                    }
                }
            }
        }
    ))
    
    result = mutator.mutate(deployment_review)
    assert result.mutated
    
    # Verify container resources in deployment
    container_resources = result.patched["spec"]["template"]["spec"]["containers"][0]["resources"]
    assert container_resources["requests"] == default_requests
    assert container_resources["limits"] == default_limits

def test_mutator_error_handling():
    # Test setup
    mutator = DefaultLabelsAnnotationsMutator({"app": "test"}, {})
    
    # Test with invalid request
    invalid_review = AdmissionReview(request=AdmissionRequest(
        uid="test-uid",
        kind=GroupVersionKind(group="", version="v1", kind="InvalidKind"),
        operation="CREATE",
        object={}
    ))
    
    result = mutator.mutate(invalid_review)
    assert not result.mutated
    
    # Test with missing spec field
    invalid_pod_review = AdmissionReview(request=AdmissionRequest(
        uid="test-uid",
        kind=GroupVersionKind(group="", version="v1", kind="Pod"),
        operation="CREATE",
        object={}
    ))
    
    result = mutator.mutate(invalid_pod_review)
    assert result.mutated
    assert "metadata" in result.patched
    assert "labels" in result.patched["metadata"]
    assert result.patched["metadata"]["labels"]["app"] == "test"
