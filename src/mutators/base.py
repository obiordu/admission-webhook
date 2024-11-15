from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from ..schemas.admission import AdmissionReview
import json
import base64

class MutationPatch(BaseModel):
    """JSON Patch operation"""
    op: str
    path: str
    value: Optional[Any] = None

class MutationResult(BaseModel):
    """Result of a mutation operation"""
    mutated: bool
    patched: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class BaseMutator(ABC):
    """Base class for all mutators"""
    
    @abstractmethod
    def mutate(self, request: AdmissionReview) -> MutationResult:
        """
        Mutate the admission request
        
        Args:
            request: The admission request object
            
        Returns:
            MutationResult: The mutation result with patched object
        """
        pass
    
    def supports(self, request: AdmissionReview) -> bool:
        """
        Check if this mutator supports the given request
        
        Args:
            request: The admission request object
            
        Returns:
            bool: True if this mutator supports the request
        """
        return True
    
    def encode_patches(self, patches: List[MutationPatch]) -> str:
        """
        Encode patches as base64 string
        
        Args:
            patches: List of JSON patches
            
        Returns:
            str: Base64 encoded JSON patch string
        """
        patch_list = [patch.dict(exclude_none=True) for patch in patches]
        return base64.b64encode(json.dumps(patch_list).encode()).decode()

class MutatorChain:
    """Chain of mutators to be executed in sequence"""
    
    def __init__(self, mutators: List[BaseMutator]):
        self.mutators = mutators
    
    def mutate(self, request: AdmissionReview) -> MutationResult:
        """
        Run all mutators in sequence
        
        Args:
            request: The admission request object
            
        Returns:
            MutationResult: The combined mutation result
        """
        all_patches = []
        
        for mutator in self.mutators:
            if not mutator.supports(request):
                continue
                
            result = mutator.mutate(request)
            if not result.mutated:
                return result
            
            if result.patched:
                all_patches.append(result.patched)
        
        return MutationResult(mutated=True, patched=all_patches if all_patches else None)
