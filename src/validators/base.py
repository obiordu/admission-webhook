from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from ..schemas.admission import ValidationResult

class BaseValidator(ABC):
    """Base class for all validators"""
    
    @abstractmethod
    def _validate(self, request: Dict[str, Any]) -> ValidationResult:
        """
        Validate the admission request
        
        Args:
            request: The admission request object
            
        Returns:
            ValidationResult: The validation result
        """
        pass
    
    def validate(self, admission_request: Dict[str, Any]) -> ValidationResult:
        """Validate the admission request"""
        try:
            if not admission_request or "request" not in admission_request:
                return ValidationResult(allowed=False, message="Invalid admission request format")
                
            request = admission_request.get("request", {})
            if not request or "object" not in request:
                return ValidationResult(allowed=False, message="Missing request object")

            if not self.supports(admission_request):
                return ValidationResult(allowed=True, message="Validator does not support this request type")

            return self._validate(request)
        except Exception as e:
            return ValidationResult(allowed=False, message=str(e))
    
    def supports(self, request: Dict[str, Any]) -> bool:
        """
        Check if this validator supports the given request
        
        Args:
            request: The admission request to check
            
        Returns:
            bool: True if the validator supports this request, False otherwise
        """
        return True  # Default implementation supports all requests

class ValidatorChain:
    """Chain of validators to be executed in sequence"""
    
    def __init__(self, validators: List[BaseValidator]):
        self.validators = validators
    
    def validate(self, request: Dict[str, Any]) -> ValidationResult:
        """
        Run all validators in sequence
        
        Args:
            request: The admission request object
            
        Returns:
            ValidationResult: The combined validation result
        """
        warnings = []
        
        for validator in self.validators:
            if not validator.supports(request):
                continue
                
            result = validator.validate(request)
            if not result.allowed:
                return result
            
            if result.warnings:
                warnings.extend(result.warnings)
        
        return ValidationResult(allowed=True, warnings=warnings if warnings else None)
