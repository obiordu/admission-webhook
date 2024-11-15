#!/bin/bash
set -euo pipefail

# Default values
REGIONS=("us-east-1" "us-west-2")
CLUSTER_PREFIX="webhook"
NAMESPACE="webhook-system"
DOMAIN="example.com"  # Update this with your actual domain

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --regions)
      IFS=',' read -ra REGIONS <<< "$2"
      shift 2
      ;;
    --cluster-prefix)
      CLUSTER_PREFIX="$2"
      shift 2
      ;;
    --namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    --domain)
      DOMAIN="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Function to install cluster components
install_cluster_components() {
  local region=$1
  local cluster_name="${CLUSTER_PREFIX}-${region}"

  echo "Installing components for cluster ${cluster_name} in ${region}..."

  # Update kubeconfig
  aws eks update-kubeconfig --name "${cluster_name}" --region "${region}"

  # Add Helm repos
  helm repo add jetstack https://charts.jetstack.io
  helm repo add eks https://aws.github.io/eks-charts
  helm repo add external-dns https://kubernetes-sigs.github.io/external-dns/
  helm repo update

  # Install cert-manager
  kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -
  kubectl label namespace cert-manager cert-manager.io/disable-validation=true --overwrite
  helm upgrade --install cert-manager jetstack/cert-manager \
    --namespace cert-manager \
    --version v1.12.0 \
    --set installCRDs=true

  # Install metrics-server
  kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

  # Create IAM service accounts and install components
  setup_aws_components "${region}" "${cluster_name}"
}

# Function to set up AWS-specific components
setup_aws_components() {
  local region=$1
  local cluster_name=$2

  # AWS Load Balancer Controller
  eksctl create iamserviceaccount \
    --cluster="${cluster_name}" \
    --namespace=kube-system \
    --name=aws-load-balancer-controller \
    --role-name="${cluster_name}-aws-load-balancer-controller" \
    --attach-policy-arn=arn:aws:iam::aws:policy/AWSLoadBalancerControllerIAMPolicy \
    --approve \
    --region "${region}"

  helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
    -n kube-system \
    --set clusterName="${cluster_name}" \
    --set serviceAccount.create=false \
    --set serviceAccount.name=aws-load-balancer-controller

  # External DNS
  setup_external_dns "${region}" "${cluster_name}"
}

# Function to set up external-dns
setup_external_dns() {
  local region=$1
  local cluster_name=$2

  # Create or get IAM policy
  local policy_arn
  policy_arn=$(aws iam list-policies --query 'Policies[?PolicyName==`external-dns-policy`].Arn' --output text)
  
  if [ -z "${policy_arn}" ]; then
    policy_arn=$(aws iam create-policy \
      --policy-name external-dns-policy \
      --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Action": ["route53:ChangeResourceRecordSets"],
            "Resource": ["arn:aws:route53:::hostedzone/*"]
          },
          {
            "Effect": "Allow",
            "Action": ["route53:ListHostedZones", "route53:ListResourceRecordSets"],
            "Resource": ["*"]
          }
        ]
      }' \
      --query 'Policy.Arn' \
      --output text)
  fi

  # Create service account
  eksctl create iamserviceaccount \
    --cluster="${cluster_name}" \
    --namespace=kube-system \
    --name=external-dns \
    --role-name="${cluster_name}-external-dns" \
    --attach-policy-arn="${policy_arn}" \
    --approve \
    --region "${region}"

  # Install external-dns
  helm upgrade --install external-dns external-dns/external-dns \
    --namespace kube-system \
    --set provider=aws \
    --set aws.zoneType=public \
    --set txtOwnerId="${cluster_name}" \
    --set domainFilters[0]="${DOMAIN}" \
    --set policy=sync \
    --set registry=txt \
    --set serviceAccount.create=false \
    --set serviceAccount.name=external-dns
}

# Function to deploy webhook
deploy_webhook() {
  local region=$1
  local cluster_name="${CLUSTER_PREFIX}-${region}"
  local cert_arn
  cert_arn=$(aws acm list-certificates --region "${region}" --query 'CertificateSummaryList[0].CertificateArn' --output text)

  echo "Deploying webhook to cluster ${cluster_name} in ${region}..."

  # Update kubeconfig
  aws eks update-kubeconfig --name "${cluster_name}" --region "${region}"

  # Create namespace
  kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

  # Create values override
  cat > "values-${region}.yaml" << EOF
image:
  repository: ${REGISTRY:-ghcr.io}/${IMAGE_NAME:-admission-webhook}
  tag: ${IMAGE_TAG:-latest}

ingress:
  annotations:
    alb.ingress.kubernetes.io/certificate-arn: ${cert_arn}
    external-dns.alpha.kubernetes.io/hostname: webhook-${region}.${DOMAIN}
  hosts:
    - host: webhook-${region}.${DOMAIN}
      paths:
        - path: /
          pathType: Prefix

webhook:
  config:
    region: ${region}
    logLevel: "info"
    metricsEnabled: true
    validationEnabled: true
    mutationEnabled: true
    imagePolicy:
      allowedRegistries:
        - docker.io
        - gcr.io
        - ghcr.io
      denyLatestTag: true
    securityPolicy:
      enforceNonRoot: true
      enforceReadOnlyRoot: true
      enforcePrivilegedContainers: false
    resourcePolicy:
      enforceResourceLimits: true
      defaultLimits:
        cpu: "1"
        memory: "1Gi"
      defaultRequests:
        cpu: "100m"
        memory: "128Mi"
EOF

  # Deploy webhook
  helm upgrade --install admission-webhook ./helm/admission-webhook \
    --namespace "${NAMESPACE}" \
    --values "values-${region}.yaml" \
    --wait \
    --timeout 10m

  # Clean up values file
  rm "values-${region}.yaml"
}

# Main execution
for region in "${REGIONS[@]}"; do
  echo "Processing region: ${region}"
  install_cluster_components "${region}"
  deploy_webhook "${region}"
done

echo "Deployment complete!"
