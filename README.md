# Kubernetes Admission Webhook Server

A high-availability Kubernetes admission webhook server built with FastAPI for validating and mutating admission requests across multiple clusters.

## Features

### Core Validation Features
- Security Context Validation
  - Privileged container restrictions
  - Root user access prevention
  - Host network usage control
  - Read-only root filesystem enforcement
- Image Policy Validation
  - Allowed registry enforcement
  - Image tag policy (prevent 'latest')
  - Image format validation
- Resource Requirements Validation
  - CPU/Memory limits enforcement
  - Resource requests validation
  - Default resource settings

### Infrastructure Features
- High-availability deployment support
- Prometheus metrics for monitoring
- Structured JSON logging
- Health check endpoints for AWS Route53 DNS failover
- TLS support for secure communication
- Stateless design for scalability
- Multi-cluster support

## Prerequisites

- Python 3.11+
- Docker
- Kubernetes cluster access
- Helm 3.x+
- AWS account for Route53 DNS failover (optional)

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   .\venv\Scripts\activate   # Windows
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[test]"
   ```

3. Generate development certificates:
   ```bash
   ./scripts/generate_certs.sh
   ```

4. Run the server locally:
   ```bash
   python -m src.app.main
   ```

## Configuration

Configuration is managed through environment variables:

### Server Settings
- `WEBHOOK_HOST`: Server host (default: "0.0.0.0")
- `WEBHOOK_PORT`: Server port (default: 8443)
- `WEBHOOK_CERT_FILE`: TLS certificate path
- `WEBHOOK_KEY_FILE`: TLS key path

### Validation Settings
- `WEBHOOK_ENFORCE_PRIVILEGED`: Enforce privileged container restrictions (default: True)
- `WEBHOOK_ENFORCE_NON_ROOT`: Prevent root user access (default: True)
- `WEBHOOK_ENFORCE_HOST_NETWORK`: Control host network access (default: True)
- `WEBHOOK_ENFORCE_RESOURCE_LIMITS`: Enforce resource limits (default: True)

### Resource Defaults
- `WEBHOOK_DEFAULT_CPU_REQUEST`: Default CPU request (default: "100m")
- `WEBHOOK_DEFAULT_CPU_LIMIT`: Default CPU limit (default: "1")
- `WEBHOOK_DEFAULT_MEMORY_REQUEST`: Default memory request (default: "128Mi")
- `WEBHOOK_DEFAULT_MEMORY_LIMIT`: Default memory limit (default: "512Mi")

### Image Policy Settings
- `WEBHOOK_ALLOWED_REGISTRIES`: Allowed image registries (default: ["docker.io", "gcr.io"])
- `WEBHOOK_DENY_LATEST_TAG`: Prevent 'latest' tag usage (default: True)

## Deployment

### Local Kubernetes Deployment

1. Install using Helm:
   ```bash
   helm install admission-webhook ./helm/admission-webhook \
     --namespace webhook-system \
     --create-namespace
   ```

### Production Deployment

1. Generate production certificates:
   ```bash
   ./scripts/generate_certs.sh --prod
   ```

2. Deploy to primary cluster:
   ```bash
   ./scripts/deploy_webhook.sh --cluster primary
   ```

3. (Optional) Configure high availability:
   ```bash
   ./scripts/setup_route53_failover.sh
   ```

## Monitoring

### Metrics
Available at `:9090/metrics`:
- `admission_webhook_validations_total`: Total validation requests
- `admission_webhook_validation_latency_seconds`: Validation latency

### Health Checks
- Liveness: `/health`
- Readiness: `/ready`

## Testing

Run the test suite:
```bash
pytest
```

Generate coverage report:
```bash
pytest --cov=src --cov-report=html
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## License

MIT License

## Security

Report security issues to [security@your-domain.com]
