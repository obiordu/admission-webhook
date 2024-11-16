#!/bin/bash

# Configuration
SERVICE_NAME="admission-webhook"
NAMESPACE="webhook-system"
SECRET_NAME="webhook-tls"

# Create a temporary directory for certificates
CERT_DIR=$(mktemp -d)
echo "Creating certificates in: $CERT_DIR"

# Generate the CA key and certificate
openssl genrsa -out "${CERT_DIR}/ca.key" 2048
openssl req -x509 -new -nodes -key "${CERT_DIR}/ca.key" -days 365 -out "${CERT_DIR}/ca.crt" -subj "/CN=admission-webhook-ca"

# Generate the server key and certificate signing request (CSR)
openssl genrsa -out "${CERT_DIR}/tls.key" 2048
openssl req -new -key "${CERT_DIR}/tls.key" -out "${CERT_DIR}/tls.csr" -subj "/CN=${SERVICE_NAME}.${NAMESPACE}.svc" \
    -config <(cat <<EOF
[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = ${SERVICE_NAME}
DNS.2 = ${SERVICE_NAME}.${NAMESPACE}
DNS.3 = ${SERVICE_NAME}.${NAMESPACE}.svc
EOF
    )

# Sign the server certificate with the CA
openssl x509 -req -in "${CERT_DIR}/tls.csr" \
    -CA "${CERT_DIR}/ca.crt" \
    -CAkey "${CERT_DIR}/ca.key" \
    -CAcreateserial \
    -out "${CERT_DIR}/tls.crt" \
    -days 365 \
    -extensions v3_req \
    -extfile <(cat <<EOF
[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = ${SERVICE_NAME}
DNS.2 = ${SERVICE_NAME}.${NAMESPACE}
DNS.3 = ${SERVICE_NAME}.${NAMESPACE}.svc
EOF
    )

# Create the certs directory if it doesn't exist
mkdir -p certs

# Copy the certificates to the certs directory
cp "${CERT_DIR}/tls.crt" "certs/tls.crt"
cp "${CERT_DIR}/tls.key" "certs/tls.key"
cp "${CERT_DIR}/ca.crt" "certs/ca.crt"

# Create base64 encoded versions for Kubernetes secrets
TLS_CRT=$(cat "${CERT_DIR}/tls.crt" | base64 -w 0)
TLS_KEY=$(cat "${CERT_DIR}/tls.key" | base64 -w 0)
CA_CRT=$(cat "${CERT_DIR}/ca.crt" | base64 -w 0)

# Create Kubernetes secret manifest
cat > "kubernetes/base/tls-secret.yaml" << EOF
apiVersion: v1
kind: Secret
metadata:
  name: ${SECRET_NAME}
  namespace: ${NAMESPACE}
type: kubernetes.io/tls
data:
  tls.crt: ${TLS_CRT}
  tls.key: ${TLS_KEY}
  ca.crt: ${CA_CRT}
EOF

# Clean up the temporary directory
rm -rf "${CERT_DIR}"

echo "Certificates generated successfully!"
echo "- TLS certificate and key are in the certs directory"
echo "- Kubernetes secret manifest created in kubernetes/base/tls-secret.yaml"
