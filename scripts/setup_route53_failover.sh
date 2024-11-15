#!/bin/bash

# Configuration
DOMAIN="webhook.example.com"
PRIMARY_ENDPOINT="webhook-primary.example.com"
SECONDARY_ENDPOINT="webhook-secondary.example.com"
HEALTH_CHECK_PATH="/health"
REGION="us-west-2"
HOSTED_ZONE_ID=""
TTL=60

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required commands
if ! command_exists aws; then
    echo "Error: AWS CLI is not installed"
    exit 1
fi

# Ensure AWS credentials are configured
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "Error: AWS credentials not configured"
    exit 1
fi

echo "Creating health checks..."

# Create health check for primary endpoint
PRIMARY_HEALTH_CHECK_ID=$(aws route53 create-health-check \
    --caller-reference "primary-$(date +%s)" \
    --health-check-config "{
        \"Port\": 443,
        \"Type\": \"HTTPS\",
        \"ResourcePath\": \"${HEALTH_CHECK_PATH}\",
        \"FullyQualifiedDomainName\": \"${PRIMARY_ENDPOINT}\",
        \"RequestInterval\": 30,
        \"FailureThreshold\": 3,
        \"EnableSNI\": true
    }" \
    --query 'HealthCheck.Id' \
    --output text)

echo "Primary health check created: ${PRIMARY_HEALTH_CHECK_ID}"

# Create health check for secondary endpoint
SECONDARY_HEALTH_CHECK_ID=$(aws route53 create-health-check \
    --caller-reference "secondary-$(date +%s)" \
    --health-check-config "{
        \"Port\": 443,
        \"Type\": \"HTTPS\",
        \"ResourcePath\": \"${HEALTH_CHECK_PATH}\",
        \"FullyQualifiedDomainName\": \"${SECONDARY_ENDPOINT}\",
        \"RequestInterval\": 30,
        \"FailureThreshold\": 3,
        \"EnableSNI\": true
    }" \
    --query 'HealthCheck.Id' \
    --output text)

echo "Secondary health check created: ${SECONDARY_HEALTH_CHECK_ID}"

# Create DNS records
echo "Creating DNS records..."

# Create primary record
aws route53 change-resource-record-sets \
    --hosted-zone-id "${HOSTED_ZONE_ID}" \
    --change-batch "{
        \"Changes\": [{
            \"Action\": \"CREATE\",
            \"ResourceRecordSet\": {
                \"Name\": \"${DOMAIN}\",
                \"Type\": \"A\",
                \"SetIdentifier\": \"primary\",
                \"Failover\": \"PRIMARY\",
                \"TTL\": ${TTL},
                \"ResourceRecords\": [{
                    \"Value\": \"$(dig +short ${PRIMARY_ENDPOINT})\"
                }],
                \"HealthCheckId\": \"${PRIMARY_HEALTH_CHECK_ID}\"
            }
        }]
    }"

# Create secondary record
aws route53 change-resource-record-sets \
    --hosted-zone-id "${HOSTED_ZONE_ID}" \
    --change-batch "{
        \"Changes\": [{
            \"Action\": \"CREATE\",
            \"ResourceRecordSet\": {
                \"Name\": \"${DOMAIN}\",
                \"Type\": \"A\",
                \"SetIdentifier\": \"secondary\",
                \"Failover\": \"SECONDARY\",
                \"TTL\": ${TTL},
                \"ResourceRecords\": [{
                    \"Value\": \"$(dig +short ${SECONDARY_ENDPOINT})\"
                }]
            }
        }]
    }"

echo "Route53 DNS failover setup completed!"
echo "Primary endpoint: ${PRIMARY_ENDPOINT}"
echo "Secondary endpoint: ${SECONDARY_ENDPOINT}"
echo "Health check IDs:"
echo "- Primary: ${PRIMARY_HEALTH_CHECK_ID}"
echo "- Secondary: ${SECONDARY_HEALTH_CHECK_ID}"

# Save configuration for future reference
cat > "route53_config.json" << EOF
{
    "domain": "${DOMAIN}",
    "primary_endpoint": "${PRIMARY_ENDPOINT}",
    "secondary_endpoint": "${SECONDARY_ENDPOINT}",
    "primary_health_check_id": "${PRIMARY_HEALTH_CHECK_ID}",
    "secondary_health_check_id": "${SECONDARY_HEALTH_CHECK_ID}",
    "hosted_zone_id": "${HOSTED_ZONE_ID}"
}
EOF

echo "Configuration saved to route53_config.json"
