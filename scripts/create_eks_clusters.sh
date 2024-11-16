#!/bin/bash

# Configuration
CLUSTER_NAME_PREFIX="webhook"
REGIONS=("us-east-1" "us-west-2")  # Virginia and Oregon
NODE_TYPE="t3.medium"
NODES_PER_CLUSTER=2
NODE_MIN=2
NODE_MAX=4

# Function to check command existence
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: $1 is required but not installed."
        exit 1
    fi
}

# Check required tools
check_command eksctl
check_command aws
check_command kubectl

# Function to create cluster in a region
create_cluster() {
    local region=$1
    local cluster_name="${CLUSTER_NAME_PREFIX}-${region}"
    
    echo "Creating EKS cluster: ${cluster_name} in ${region}"
    
    eksctl create cluster \
        --name "${cluster_name}" \
        --region "${region}" \
        --version 1.27 \
        --nodegroup-name "standard-workers" \
        --node-type "${NODE_TYPE}" \
        --nodes "${NODES_PER_CLUSTER}" \
        --nodes-min "${NODE_MIN}" \
        --nodes-max "${NODE_MAX}" \
        --managed \
        --asg-access \
        --enable-ssm \
        --with-oidc \
        --alb-ingress-access \
        --full-ecr-access \
        --node-private-networking \
        --tags "Environment=production,Component=admission-webhook" \
        --dry-run=false

    # Create namespace
    kubectl create namespace webhook-system

    # Add required labels for cert-manager
    kubectl label namespace webhook-system cert-manager.io/disable-validation=true

    # Install cert-manager
    helm repo add jetstack https://charts.jetstack.io
    helm repo update
    helm install cert-manager jetstack/cert-manager \
        --namespace cert-manager \
        --create-namespace \
        --version v1.12.0 \
        --set installCRDs=true

    # Install metrics server
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

    # Install AWS Load Balancer Controller
    eksctl create iamserviceaccount \
        --cluster="${cluster_name}" \
        --namespace=kube-system \
        --name=aws-load-balancer-controller \
        --role-name="${cluster_name}-aws-load-balancer-controller" \
        --attach-policy-arn=arn:aws:iam::aws:policy/AWSLoadBalancerControllerIAMPolicy \
        --approve \
        --region "${region}"

    helm repo add eks https://aws.github.io/eks-charts
    helm repo update
    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set clusterName="${cluster_name}" \
        --set serviceAccount.create=false \
        --set serviceAccount.name=aws-load-balancer-controller

    echo "Cluster ${cluster_name} setup completed in ${region}"
}

# Main execution
for region in "${REGIONS[@]}"; do
    create_cluster "${region}"
done

echo "All clusters created successfully!"
