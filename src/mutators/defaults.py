from typing import Dict, Any, Optional, List
from .base import BaseMutator, MutationResult
from ..schemas.admission import AdmissionReview

class DefaultLabelsAnnotationsMutator(BaseMutator):
    """Adds default labels and annotations to resources"""
    
    def __init__(self, default_labels: Optional[Dict[str, str]] = None,
                 default_annotations: Optional[Dict[str, str]] = None):
        self.default_labels = default_labels or {}
        self.default_annotations = default_annotations or {}
    
    def mutate(self, request: AdmissionReview) -> MutationResult:
        """Add default labels and annotations"""
        try:
            if request.request.kind.kind not in ["Pod", "Deployment"]:
                return MutationResult(mutated=False)
                
            obj = request.request.object
            metadata = obj.get("metadata", {})
            
            # Add default labels
            if self.default_labels:
                labels = metadata.get("labels", {})
                labels.update(self.default_labels)
                metadata["labels"] = labels
                
            # Add default annotations
            if self.default_annotations:
                annotations = metadata.get("annotations", {})
                annotations.update(self.default_annotations)
                metadata["annotations"] = annotations
                
            obj["metadata"] = metadata
            
            # For Deployments, also update pod template
            if request.request.kind.kind == "Deployment":
                template = obj.get("spec", {}).get("template", {})
                template_metadata = template.get("metadata", {})
                
                if self.default_labels:
                    template_labels = template_metadata.get("labels", {})
                    template_labels.update(self.default_labels)
                    template_metadata["labels"] = template_labels
                    
                if self.default_annotations:
                    template_annotations = template_metadata.get("annotations", {})
                    template_annotations.update(self.default_annotations)
                    template_metadata["annotations"] = template_annotations
                    
                template["metadata"] = template_metadata
                obj["spec"]["template"] = template
                
            return MutationResult(mutated=True, patched=obj)
            
        except Exception as e:
            return MutationResult(mutated=False, message=str(e))

class DefaultSecurityContextMutator(BaseMutator):
    """Adds default security context settings"""
    
    def __init__(self, run_as_non_root: bool = True,
                 read_only_root_filesystem: bool = True,
                 run_as_user: Optional[int] = None,
                 run_as_group: Optional[int] = None,
                 fs_group: Optional[int] = None):
        self.run_as_non_root = run_as_non_root
        self.read_only_root_filesystem = read_only_root_filesystem
        self.run_as_user = run_as_user
        self.run_as_group = run_as_group
        self.fs_group = fs_group
    
    def get_default_container_security_context(self) -> Dict[str, Any]:
        """Get default container security context"""
        context = {
            "runAsNonRoot": self.run_as_non_root,
            "readOnlyRootFilesystem": self.read_only_root_filesystem,
            "allowPrivilegeEscalation": False
        }
        
        if self.run_as_user is not None:
            context["runAsUser"] = self.run_as_user
            
        if self.run_as_group is not None:
            context["runAsGroup"] = self.run_as_group
            
        return context
    
    def get_default_pod_security_context(self) -> Dict[str, Any]:
        """Get default pod security context"""
        context = {
            "runAsNonRoot": self.run_as_non_root
        }
        
        if self.run_as_user is not None:
            context["runAsUser"] = self.run_as_user
            
        if self.run_as_group is not None:
            context["runAsGroup"] = self.run_as_group
            
        if self.fs_group is not None:
            context["fsGroup"] = self.fs_group
            
        return context
    
    def mutate(self, request: AdmissionReview) -> MutationResult:
        """Add default security context settings"""
        try:
            if request.request.kind.kind not in ["Pod", "Deployment"]:
                return MutationResult(mutated=False)
                
            obj = request.request.object
            pod_spec = obj.get("spec", {})
            
            if request.request.kind.kind == "Deployment":
                pod_spec = pod_spec.get("template", {}).get("spec", {})
                
            # Add pod security context
            pod_spec["securityContext"] = self.get_default_pod_security_context()
            
            # Add container security contexts
            containers = pod_spec.get("containers", [])
            for container in containers:
                container["securityContext"] = self.get_default_container_security_context()
                
            if request.request.kind.kind == "Pod":
                obj["spec"] = pod_spec
            else:
                obj["spec"]["template"]["spec"] = pod_spec
                
            return MutationResult(mutated=True, patched=obj)
            
        except Exception as e:
            return MutationResult(mutated=False, message=str(e))

class DefaultResourcesMutator(BaseMutator):
    """Adds default resource requirements"""
    
    def __init__(self, default_requests: Optional[Dict[str, str]] = None,
                 default_limits: Optional[Dict[str, str]] = None):
        self.default_requests = default_requests or {}
        self.default_limits = default_limits or {}
    
    def get_default_resources(self) -> Dict[str, Any]:
        """Get default resource requirements"""
        resources = {}
        
        if self.default_requests:
            resources["requests"] = self.default_requests
            
        if self.default_limits:
            resources["limits"] = self.default_limits
            
        return resources
    
    def mutate(self, request: AdmissionReview) -> MutationResult:
        """Add default resource requirements"""
        try:
            if request.request.kind.kind not in ["Pod", "Deployment"]:
                return MutationResult(mutated=False)
                
            obj = request.request.object
            pod_spec = obj.get("spec", {})
            
            if request.request.kind.kind == "Deployment":
                pod_spec = pod_spec.get("template", {}).get("spec", {})
                
            # Add resource requirements to containers
            containers = pod_spec.get("containers", [])
            for container in containers:
                if "resources" not in container:
                    container["resources"] = self.get_default_resources()
                    
            if request.request.kind.kind == "Pod":
                obj["spec"] = pod_spec
            else:
                obj["spec"]["template"]["spec"] = pod_spec
                
            return MutationResult(mutated=True, patched=obj)
            
        except Exception as e:
            return MutationResult(mutated=False, message=str(e))
