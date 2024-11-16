from typing import Dict, Any, List
from .base import BaseValidator, ValidationResult

class ImagePolicyValidator(BaseValidator):
    """Validator for container image policies"""

    def __init__(self, allowed_registries: List[str] = None, deny_latest_tag: bool = True):
        self.allowed_registries = allowed_registries or ["docker.io"]
        self.deny_latest_tag = deny_latest_tag

    def _validate(self, request: Dict[str, Any]) -> ValidationResult:
        """Validate container images against policy"""
        try:
            pod = request.get("object", {})
            if not pod or "spec" not in pod:
                return ValidationResult(allowed=False, message="Invalid pod specification")

            spec = pod.get("spec", {})
            containers = spec.get("containers", [])

            for container in containers:
                image = container.get("image", "")
                if not image:
                    return ValidationResult(
                        allowed=False,
                        message=f"Container {container.get('name')} has no image specified"
                    )

                # Check registry
                registry = image.split("/")[0] if "/" in image else "docker.io"
                if registry not in self.allowed_registries:
                    return ValidationResult(
                        allowed=False,
                        message=f"Registry {registry} is not allowed. Allowed registries: {', '.join(self.allowed_registries)}"
                    )

                # Check latest tag
                if self.deny_latest_tag and (":latest" in image or ":" not in image):
                    return ValidationResult(
                        allowed=False,
                        message=f"Latest tag is not allowed for image {image}"
                    )

            return ValidationResult(allowed=True, message="Image policy validation passed")

        except Exception as e:
            return ValidationResult(
                allowed=False,
                message=f"Image policy validation error: {str(e)}"
            )

    def supports(self, request: Dict[str, Any]) -> bool:
        """Check if this validator supports the request"""
        try:
            kind = request.get("request", {}).get("kind", {}).get("kind", "")
            return kind in ["Pod", "Deployment"]
        except Exception:
            return False
