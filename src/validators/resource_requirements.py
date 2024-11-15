from typing import Dict, Any, Optional
from .base import BaseValidator, ValidationResult

class ResourceRequirementsValidator(BaseValidator):
    """Validator for container resource requirements"""

    def __init__(
        self,
        enforce_limits: bool = True,
        default_cpu_request: str = "100m",
        default_cpu_limit: str = "1",
        default_memory_request: str = "128Mi",
        default_memory_limit: str = "512Mi"
    ):
        self.enforce_limits = enforce_limits
        self.default_cpu_request = default_cpu_request
        self.default_cpu_limit = default_cpu_limit
        self.default_memory_request = default_memory_request
        self.default_memory_limit = default_memory_limit

    def _validate(self, request: Dict[str, Any]) -> ValidationResult:
        """Validate container resource requirements"""
        try:
            pod = request.get("object", {})
            if not pod or "spec" not in pod:
                return ValidationResult(allowed=False, message="Invalid pod specification")

            spec = pod.get("spec", {})
            containers = spec.get("containers", [])

            for container in containers:
                resources = container.get("resources", {})
                
                if not resources and self.enforce_limits:
                    return ValidationResult(
                        allowed=False,
                        message=f"Container {container.get('name')} must specify resource requirements"
                    )

                limits = resources.get("limits", {})
                requests = resources.get("requests", {})

                if self.enforce_limits:
                    # Check CPU limits
                    if "cpu" not in limits:
                        return ValidationResult(
                            allowed=False,
                            message=f"Container {container.get('name')} must specify CPU limits"
                        )

                    # Check memory limits
                    if "memory" not in limits:
                        return ValidationResult(
                            allowed=False,
                            message=f"Container {container.get('name')} must specify memory limits"
                        )

                    # Check CPU requests
                    if "cpu" not in requests:
                        return ValidationResult(
                            allowed=False,
                            message=f"Container {container.get('name')} must specify CPU requests"
                        )

                    # Check memory requests
                    if "memory" not in requests:
                        return ValidationResult(
                            allowed=False,
                            message=f"Container {container.get('name')} must specify memory requests"
                        )

            return ValidationResult(allowed=True, message="Resource requirements validation passed")

        except Exception as e:
            return ValidationResult(
                allowed=False,
                message=f"Resource requirements validation error: {str(e)}"
            )

    def supports(self, request: Dict[str, Any]) -> bool:
        """Check if this validator supports the request"""
        try:
            kind = request.get("request", {}).get("kind", {}).get("kind", "")
            return kind in ["Pod", "Deployment"]
        except Exception:
            return False
