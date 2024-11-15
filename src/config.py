from typing import List, Optional
from pydantic_settings import BaseSettings

class WebhookConfig(BaseSettings):
    """Configuration for the admission webhook"""
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8443
    CERT_FILE: str = "/etc/webhook/certs/tls.crt"
    KEY_FILE: str = "/etc/webhook/certs/tls.key"
    
    # Validation settings
    ENFORCE_PRIVILEGED: bool = True
    ENFORCE_NON_ROOT: bool = True
    ENFORCE_READONLY_ROOT: bool = True
    ENFORCE_HOST_NETWORK: bool = True
    ENFORCE_RESOURCE_LIMITS: bool = True
    
    # Resource defaults
    DEFAULT_CPU_REQUEST: str = "100m"
    DEFAULT_CPU_LIMIT: str = "1"
    DEFAULT_MEMORY_REQUEST: str = "128Mi"
    DEFAULT_MEMORY_LIMIT: str = "512Mi"
    
    # Image policy settings
    ALLOWED_REGISTRIES: List[str] = ["docker.io", "gcr.io"]
    DENY_LATEST_TAG: bool = True
    
    # Logging and metrics
    LOG_LEVEL: str = "INFO"
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090

    class Config:
        env_prefix = "WEBHOOK_"
