from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class GroupVersionKind(BaseModel):
    """Kubernetes GroupVersionKind schema"""
    group: str
    version: str
    kind: str

class ValidationResult(BaseModel):
    """Validation result model"""
    allowed: bool
    message: Optional[str] = None
    warnings: Optional[List[str]] = None

class AdmissionRequest(BaseModel):
    """Admission request model"""
    uid: str
    kind: Dict[str, str]
    resource: Dict[str, str]
    operation: str
    userInfo: Dict[str, Any]
    object: Dict[str, Any]
    oldObject: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None
    dryRun: Optional[bool] = None

class AdmissionResponse(BaseModel):
    """Admission response model"""
    uid: str
    allowed: bool
    status: Optional[Dict[str, str]] = None
    patch: Optional[str] = None
    patchType: Optional[str] = None
    auditAnnotations: Optional[Dict[str, str]] = None
    warnings: Optional[List[str]] = None

class AdmissionReview(BaseModel):
    """Admission review model"""
    apiVersion: str = Field(default="admission.k8s.io/v1")
    kind: str = Field(default="AdmissionReview")
    request: AdmissionRequest
    response: Optional[AdmissionResponse] = None
