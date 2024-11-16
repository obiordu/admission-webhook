from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, start_http_server
import time
import logging
import uvicorn
import signal
from typing import Callable
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.schemas.admission import AdmissionReview, AdmissionResponse
from app.validators.security import SecurityContextValidator
from app.validators.base import ValidatorChain
from app.mutators.base import MutatorChain
from app.mutators.defaults import (
    DefaultLabelsAnnotationsMutator,
    DefaultSecurityContextMutator,
    DefaultResourcesMutator
)
from app.config import WebhookConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="Kubernetes Admission Webhook",
    description="Kubernetes admission webhook for validating and mutating admission requests",
    version="1.0.0"
)

# Load configuration
config = WebhookConfig()

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=config.ALLOWED_HOSTS
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Prometheus metrics
VALIDATION_COUNTER = Counter(
    "admission_webhook_validations_total",
    "Total number of admission validations",
    ["result"]
)
VALIDATION_LATENCY = Histogram(
    "admission_webhook_validation_latency_seconds",
    "Validation request latency in seconds"
)
MUTATION_COUNTER = Counter(
    "admission_webhook_mutations_total",
    "Total number of admission mutations",
    ["result"]
)
MUTATION_LATENCY = Histogram(
    "admission_webhook_mutation_latency_seconds",
    "Mutation request latency in seconds"
)

@app.on_event("startup")
async def startup_event():
    """Start Prometheus metrics server on startup"""
    if config.METRICS_ENABLED:
        start_http_server(config.METRICS_PORT)
        logger.info(f"Started metrics server on port {config.METRICS_PORT}")
    logger.info("Webhook server started")

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown handler"""
    logger.info("Shutting down webhook server...")
    # Add cleanup tasks here if needed

@app.get("/health")
@limiter.limit("60/minute")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/ready")
@limiter.limit("60/minute")
async def readiness_check():
    """Readiness check endpoint"""
    return {"status": "ready"}

@app.exception_handler(Exception)
async def validation_exception_handler(request: Request, exc: Exception):
    """Handle validation exceptions"""
    logger.error(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={"allowed": False, "message": str(exc)}
    )

@app.post("/validate")
@limiter.limit("60/minute")
async def validate(review: AdmissionReview) -> AdmissionResponse:
    """
    Validate admission requests
    """
    start_time = time.time()
    
    try:
        # Create validator chain
        validators = [
            SecurityContextValidator(
                enforce_privileged=config.ENFORCE_PRIVILEGED,
                enforce_non_root=config.ENFORCE_NON_ROOT,
                enforce_readonly_root=config.ENFORCE_READONLY_ROOT,
                enforce_host_network=config.ENFORCE_HOST_NETWORK
            )
        ]
        
        validator_chain = ValidatorChain(validators)
        result = validator_chain.validate(review.dict())
        
        # Record metrics
        VALIDATION_COUNTER.labels(result="success" if result.allowed else "failure").inc()
        VALIDATION_LATENCY.observe(time.time() - start_time)
        
        return AdmissionResponse(
            apiVersion=review.apiVersion,
            kind=review.kind,
            response={
                "uid": review.request.uid,
                "allowed": result.allowed,
                "status": {"message": result.message} if result.message else None
            }
        )
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        # Record metrics for errors
        VALIDATION_COUNTER.labels(result="error").inc()
        VALIDATION_LATENCY.observe(time.time() - start_time)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/mutate")
@limiter.limit("60/minute")
async def mutate(review: AdmissionReview) -> AdmissionResponse:
    """
    Mutate admission requests
    """
    start_time = time.time()
    
    try:
        # Create mutator chain with default mutators
        mutators = [
            DefaultLabelsAnnotationsMutator(
                default_labels=config.DEFAULT_LABELS,
                default_annotations=config.DEFAULT_ANNOTATIONS
            ),
            DefaultSecurityContextMutator(
                run_as_non_root=config.ENFORCE_NON_ROOT,
                read_only_root_filesystem=config.ENFORCE_READONLY_ROOT,
                run_as_user=config.DEFAULT_RUN_AS_USER,
                run_as_group=config.DEFAULT_RUN_AS_GROUP,
                fs_group=config.DEFAULT_FS_GROUP
            ),
            DefaultResourcesMutator(
                default_requests=config.DEFAULT_RESOURCE_REQUESTS,
                default_limits=config.DEFAULT_RESOURCE_LIMITS
            )
        ]
        
        mutator_chain = MutatorChain(mutators)
        result = mutator_chain.mutate(review.dict())
        
        # Record metrics
        MUTATION_COUNTER.labels(result="success" if result.mutated else "skipped").inc()
        MUTATION_LATENCY.observe(time.time() - start_time)
        
        return AdmissionResponse(
            apiVersion=review.apiVersion,
            kind=review.kind,
            response={
                "uid": review.request.uid,
                "allowed": True,
                "patch": result.patches if result.mutated else None,
                "patchType": "JSONPatch" if result.mutated else None,
                "status": {"message": result.message} if result.message else None
            }
        )
        
    except Exception as e:
        logger.error(f"Mutation error: {str(e)}")
        # Record metrics for errors
        MUTATION_COUNTER.labels(result="error").inc()
        MUTATION_LATENCY.observe(time.time() - start_time)
        raise HTTPException(status_code=400, detail=str(e))

def run_server():
    """Run the webhook server"""
    def handle_sigterm(signum: int, frame: Callable) -> None:
        logger.info("Received SIGTERM signal, initiating graceful shutdown...")
        raise SystemExit(0)

    # Register SIGTERM handler for graceful shutdown
    signal.signal(signal.SIGTERM, handle_sigterm)

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        ssl_keyfile=config.TLS_KEY_FILE,
        ssl_certfile=config.TLS_CERT_FILE,
        log_level=config.LOG_LEVEL.lower(),
        proxy_headers=True,
        forwarded_allow_ips="*"
    )

if __name__ == "__main__":
    run_server()
