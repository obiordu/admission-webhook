import pytest
import yaml
import os
import subprocess
import json
from typing import Dict, Any

def test_helm_chart_validation():
    """Test Helm chart validation"""
    chart_dir = "./helm/admission-webhook"
    
    # Validate chart
    result = subprocess.run(
        ["helm", "lint", chart_dir],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Helm lint failed: {result.stderr}"
    
    # Check required files exist
    required_files = [
        "Chart.yaml",
        "values.yaml",
        "templates/deployment.yaml",
        "templates/service.yaml",
        "templates/ingress.yaml",
        "templates/serviceaccount.yaml",
        "templates/clusterrole.yaml",
        "templates/clusterrolebinding.yaml",
        "templates/secret.yaml",
        "templates/_helpers.tpl"
    ]
    
    for file in required_files:
        assert os.path.exists(os.path.join(chart_dir, file)), f"Missing {file}"

def test_helm_chart_rendering():
    """Test Helm chart rendering"""
    chart_dir = "./helm/admission-webhook"
    
    # Create test values
    test_values = {
        "image": {
            "repository": "ghcr.io/test/webhook",
            "tag": "latest"
        },
        "ingress": {
            "annotations": {
                "alb.ingress.kubernetes.io/scheme": "internet-facing",
                "external-dns.alpha.kubernetes.io/hostname": "webhook.example.com"
            },
            "hosts": [{
                "host": "webhook.example.com",
                "paths": [{
                    "path": "/",
                    "pathType": "Prefix"
                }]
            }]
        },
        "webhook": {
            "config": {
                "logLevel": "info",
                "metricsEnabled": True,
                "validationEnabled": True,
                "mutationEnabled": True
            }
        }
    }
    
    # Write test values to file
    with open("test-values.yaml", "w") as f:
        yaml.dump(test_values, f)
    
    try:
        # Render templates
        result = subprocess.run(
            ["helm", "template", "test", chart_dir, "-f", "test-values.yaml"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Helm template failed: {result.stderr}"
        
        # Parse rendered templates
        rendered = yaml.safe_load_all(result.stdout)
        resources = list(rendered)
        
        # Verify required resources
        resource_kinds = [r["kind"] for r in resources]
        assert "Deployment" in resource_kinds
        assert "Service" in resource_kinds
        assert "Ingress" in resource_kinds
        assert "ServiceAccount" in resource_kinds
        assert "ClusterRole" in resource_kinds
        assert "ClusterRoleBinding" in resource_kinds
        assert "Secret" in resource_kinds
        
        # Verify deployment configuration
        deployment = next(r for r in resources if r["kind"] == "Deployment")
        assert deployment["spec"]["template"]["spec"]["containers"][0]["image"] == \
            f"{test_values['image']['repository']}:{test_values['image']['tag']}"
        
        # Verify ingress configuration
        ingress = next(r for r in resources if r["kind"] == "Ingress")
        assert ingress["spec"]["rules"][0]["host"] == \
            test_values["ingress"]["hosts"][0]["host"]
        
    finally:
        # Clean up
        os.remove("test-values.yaml")

def test_deployment_script():
    """Test deployment script functionality"""
    script_path = "./scripts/deploy_webhook.sh"
    
    # Test script help/usage
    result = subprocess.run(
        ["bash", script_path, "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Script help failed"
    
    # Test argument parsing
    test_args = [
        "--regions", "us-east-1",
        "--cluster-prefix", "test-webhook",
        "--namespace", "test-system",
        "--domain", "test.example.com"
    ]
    
    result = subprocess.run(
        ["bash", "-n", script_path] + test_args,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Script syntax check failed"

def test_ci_cd_pipeline():
    """Test CI/CD pipeline configuration"""
    workflow_file = ".github/workflows/ci-cd.yaml"
    
    with open(workflow_file) as f:
        workflow = yaml.safe_load(f)
    
    # Verify required jobs
    required_jobs = ["test", "lint", "build", "deploy"]
    for job in required_jobs:
        assert job in workflow["jobs"], f"Missing job: {job}"
    
    # Verify job dependencies
    assert "needs" in workflow["jobs"]["build"]
    assert set(workflow["jobs"]["build"]["needs"]) == {"test", "lint"}
    
    assert "needs" in workflow["jobs"]["deploy"]
    assert workflow["jobs"]["deploy"]["needs"] == ["build"]
    
    # Verify required secrets
    deploy_job = workflow["jobs"]["deploy"]
    aws_credentials_step = next(
        step for step in deploy_job["steps"] 
        if step.get("name") == "Configure AWS credentials"
    )
    assert "AWS_ACCESS_KEY_ID" in aws_credentials_step["with"]["aws-access-key-id"]
    assert "AWS_SECRET_ACCESS_KEY" in aws_credentials_step["with"]["aws-secret-access-key"]

def test_metrics_server_installation():
    """Test metrics-server installation in deployment script"""
    script_path = "./scripts/deploy_webhook.sh"
    
    with open(script_path) as f:
        script_content = f.read()
    
    # Verify metrics-server installation
    assert "metrics-server" in script_content
    assert "components.yaml" in script_content

def test_cert_manager_installation():
    """Test cert-manager installation in deployment script"""
    script_path = "./scripts/deploy_webhook.sh"
    
    with open(script_path) as f:
        script_content = f.read()
    
    # Verify cert-manager installation
    assert "cert-manager" in script_content
    assert "jetstack" in script_content
    assert "installCRDs=true" in script_content

def test_load_balancer_installation():
    """Test AWS Load Balancer Controller installation in deployment script"""
    script_path = "./scripts/deploy_webhook.sh"
    
    with open(script_path) as f:
        script_content = f.read()
    
    # Verify AWS Load Balancer Controller installation
    assert "aws-load-balancer-controller" in script_content
    assert "AWSLoadBalancerControllerIAMPolicy" in script_content

def test_external_dns_installation():
    """Test external-dns installation in deployment script"""
    script_path = "./scripts/deploy_webhook.sh"
    
    with open(script_path) as f:
        script_content = f.read()
    
    # Verify external-dns installation
    assert "external-dns" in script_content
    assert "route53:ChangeResourceRecordSets" in script_content
    assert "route53:ListHostedZones" in script_content
