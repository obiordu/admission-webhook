from typing import Dict, Any, Optional, List
from .base import BaseValidator, ValidationResult
from ..schemas.admission import AdmissionReview

class SecurityContextValidator(BaseValidator):
    """Validator for security context settings"""

    def __init__(
        self,
        enforce_privileged: bool = True,
        enforce_non_root: bool = True,
        enforce_readonly_root: bool = True,
        enforce_host_network: bool = True
    ):
        self.enforce_privileged = enforce_privileged
        self.enforce_non_root = enforce_non_root
        self.enforce_readonly_root = enforce_readonly_root
        self.enforce_host_network = enforce_host_network

    def _validate(self, request: Dict[str, Any]) -> ValidationResult:
        """Validate the security context of containers"""
        try:
            pod = request.get("object", {})
            if not pod or "spec" not in pod:
                return ValidationResult(allowed=False, message="Invalid pod specification")

            spec = pod.get("spec", {})
            containers = spec.get("containers", [])
            
            # Check host network
            if self.enforce_host_network and spec.get("hostNetwork", False):
                return ValidationResult(allowed=False, message="Host network access is not allowed")

            for container in containers:
                security_context = container.get("securityContext", {})
                
                # Check privileged mode
                if self.enforce_privileged and security_context.get("privileged", False):
                    return ValidationResult(allowed=False, message="Privileged containers are not allowed")
                
                # Check root user
                if self.enforce_non_root:
                    run_as_user = security_context.get("runAsUser")
                    if run_as_user is not None and run_as_user == 0:
                        return ValidationResult(allowed=False, message="Running as root is not allowed")
                    
                # Check readonly root filesystem
                if self.enforce_readonly_root and not security_context.get("readOnlyRootFilesystem", False):
                    return ValidationResult(allowed=False, message="Root filesystem must be read-only")

            return ValidationResult(allowed=True, message="Security context validation passed")
        except Exception as e:
            return ValidationResult(allowed=False, message=f"Security context validation error: {str(e)}")

    def supports(self, request: Dict[str, Any]) -> bool:
        """Check if this validator supports the request"""
        try:
            kind = request.get("request", {}).get("kind", {}).get("kind", "")
            return kind in ["Pod", "Deployment"]
        except Exception:
            return False

    def validate(self, request: AdmissionReview) -> ValidationResult:
        """Validate security context in admission request"""
        try:
            if not self.supports(request.request):
                return ValidationResult(allowed=True)
                
            pod_spec = request.request.object.get("spec", {})
            if request.request.kind.kind == "Deployment":
                pod_spec = pod_spec.get("template", {}).get("spec", {})
                
            # Validate pod security context
            pod_error = self._validate(request.request.object)
            if pod_error:
                return pod_error
                
            return ValidationResult(allowed=True)
            
        except Exception as e:
            return ValidationResult(allowed=False, message=str(e))

class ImagePolicyValidator(BaseValidator):
    """Validates container image policies"""
    
    def __init__(self, allowed_registries: Optional[List[str]] = None,
                 deny_latest_tag: bool = False):
        self.allowed_registries = allowed_registries or []
        self.deny_latest_tag = deny_latest_tag
    
    def validate_image(self, image: str) -> Optional[str]:
        """Validate container image"""
        # Check registry
        if self.allowed_registries:
            registry = image.split("/")[0]
            if registry not in self.allowed_registries:
                return f"Image registry '{registry}' is not allowed"
        
        # Check tag
        if self.deny_latest_tag and ":latest" in image:
            return "Latest tag is not allowed"
            
        return None
    
    def validate(self, request: AdmissionReview) -> ValidationResult:
        """Validate image policy in admission request"""
        try:
            if request.request.kind.kind not in ["Pod", "Deployment"]:
                return ValidationResult(allowed=True)
                
            pod_spec = request.request.object.get("spec", {})
            if request.request.kind.kind == "Deployment":
                pod_spec = pod_spec.get("template", {}).get("spec", {})
                
            containers = pod_spec.get("containers", [])
            for container in containers:
                image = container.get("image", "")
                error = self.validate_image(image)
                if error:
                    return ValidationResult(
                        allowed=False,
                        message=f"Container '{container.get('name')}': {error}"
                    )
                    
            return ValidationResult(allowed=True)
            
        except Exception as e:
            return ValidationResult(allowed=False, message=str(e))

class ResourceRequirementsValidator(BaseValidator):
    """Validates container resource requirements"""
    
    def __init__(self, enforce_limits: bool = False,
                 min_memory: Optional[str] = None,
                 max_memory: Optional[str] = None,
                 min_cpu: Optional[str] = None,
                 max_cpu: Optional[str] = None):
        self.enforce_limits = enforce_limits
        self.min_memory = min_memory
        self.max_memory = max_memory
        self.min_cpu = min_cpu
        self.max_cpu = max_cpu
    
    def validate_resources(self, container: Dict[str, Any]) -> Optional[str]:
        """Validate container resource requirements"""
        resources = container.get("resources", {})
        
        if self.enforce_limits and not resources.get("limits"):
            return "Resource limits are required"
            
        limits = resources.get("limits", {})
        requests = resources.get("requests", {})
        
        # Validate memory
        if self.min_memory and requests.get("memory"):
            if not self._compare_resource("memory", requests["memory"], self.min_memory, ">="):
                return f"Memory request must be >= {self.min_memory}"
                
        if self.max_memory and limits.get("memory"):
            if not self._compare_resource("memory", limits["memory"], self.max_memory, "<="):
                return f"Memory limit must be <= {self.max_memory}"
                
        # Validate CPU
        if self.min_cpu and requests.get("cpu"):
            if not self._compare_resource("cpu", requests["cpu"], self.min_cpu, ">="):
                return f"CPU request must be >= {self.min_cpu}"
                
        if self.max_cpu and limits.get("cpu"):
            if not self._compare_resource("cpu", limits["cpu"], self.max_cpu, "<="):
                return f"CPU limit must be <= {self.max_cpu}"
                
        return None
    
    def _compare_resource(self, resource_type: str, value1: str, value2: str, operator: str) -> bool:
        """Compare resource values"""
        # TODO: Implement resource comparison logic
        return True
    
    def validate(self, request: AdmissionReview) -> ValidationResult:
        """Validate resource requirements in admission request"""
        try:
            if request.request.kind.kind not in ["Pod", "Deployment"]:
                return ValidationResult(allowed=True)
                
            pod_spec = request.request.object.get("spec", {})
            if request.request.kind.kind == "Deployment":
                pod_spec = pod_spec.get("template", {}).get("spec", {})
                
            containers = pod_spec.get("containers", [])
            for container in containers:
                error = self.validate_resources(container)
                if error:
                    return ValidationResult(
                        allowed=False,
                        message=f"Container '{container.get('name')}': {error}"
                    )
                    
            return ValidationResult(allowed=True)
            
        except Exception as e:
            return ValidationResult(allowed=False, message=str(e))
