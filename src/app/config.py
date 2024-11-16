from pydantic import BaseSettings
from typing import List, Optional

class WebhookConfig(BaseSettings):
    """Webhook configuration"""
    
    # Server settings
    PORT: int = 8443
    HOST: str = "0.0.0.0"
    TLS_CERT_FILE: Optional[str] = None
    TLS_KEY_FILE: Optional[str] = None
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Logging and metrics
    LOG_LEVEL: str = "INFO"
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9090
    
    # Validation settings
    VALIDATION_ENABLED: bool = True
    MUTATION_ENABLED: bool = True
    
    # Security settings
    ENFORCE_NON_ROOT: bool = True
    ENFORCE_READONLY_ROOT: bool = True
    ENFORCE_PRIVILEGED: bool = True
    ENFORCE_HOST_NETWORK: bool = True
    
    # Image policy settings
    ALLOWED_REGISTRIES: List[str] = ["docker.io", "gcr.io"]
    DENY_LATEST_TAG: bool = True
    
    # Resource settings
    ENFORCE_RESOURCE_LIMITS: bool = True
    DEFAULT_CPU_REQUEST: str = "100m"
    DEFAULT_CPU_LIMIT: str = "1"
    DEFAULT_MEMORY_REQUEST: str = "128Mi"
    DEFAULT_MEMORY_LIMIT: str = "512Mi"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

webhook_config = WebhookConfig()
