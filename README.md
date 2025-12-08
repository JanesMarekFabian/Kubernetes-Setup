# Kubernetes Infrastructure Deployment

This repository contains the base Kubernetes infrastructure deployment configuration for deploying essential add-ons using Helm charts with container image mirroring to Azure Container Registry (ACR).

## Overview

This project automates the deployment of:
- **NGINX Ingress Controller** - For ingress traffic management
- **Prometheus Stack** (kube-prometheus-stack) - Monitoring, alerting, and observability
- **Metrics Server** - For resource metrics (kubectl top, HPA)
- **Local Path Provisioner** - For local storage (k3s compatible)

All container images are automatically mirrored to Azure Container Registry (ACR) to work in air-gapped or firewall-restricted environments.

## Project Structure

```
.
├── .github/
│   ├── actions/
│   │   └── setup-cicd/          # GitHub Action for CI/CD cluster access setup
│   └── workflows/
│       └── build-push.yml        # Main CI/CD workflow
├── infra/
│   ├── addons/
│   │   └── values/              # Helm values files
│   │       ├── ingress-nginx.yaml
│   │       └── observability.yaml
│   └── rbac/
│       └── cicd-serviceaccount.yaml  # RBAC for CI/CD ServiceAccount
└── scripts/
    └── generate_addon_artifacts.py   # Script to generate image mapping and ACR values
```

## Prerequisites

- Kubernetes cluster (tested with k3s)
- Azure Container Registry (ACR) with credentials
- GitHub Actions secrets configured:
  - `ACR_REGISTRY` - ACR registry URL (e.g., `myregistry.azurecr.io`)
  - `ACR_USERNAME` - ACR username
  - `ACR_PASSWORD` - ACR password
  - `KUBECONFIG` - Base64-encoded kubeconfig for cluster access

## How It Works

### 1. Image Mirroring (`mirror` job)
- Generates `image-map.txt` with source→target image mappings
- Creates `observability.acr.yaml` with ACR registry rewrites
- Mirrors all container images to ACR
- Extracts additional images from Helm chart defaults using `helm template`

### 2. Infrastructure Deployment
The workflow deploys components in order:
1. **Local Path Provisioner** - Storage provisioner
2. **Metrics Server** - Resource metrics
3. **NGINX Ingress Controller** - Ingress traffic
4. **Monitoring Stack** - Prometheus, Grafana, Alertmanager

### 3. Image Registry Handling
- All images are rewritten to use ACR registry
- ServiceAccounts are patched with ACR pull secrets
- Helm Post-Renderer ensures all images use ACR (including nested structures)

## Usage

### Automatic Deployment (CI/CD)
The workflow triggers automatically on:
- Push to `main` branch when files in `infra/addons/**`, `infra/rbac/**`, or `.github/workflows/build-push.yml` change
- Manual trigger via `workflow_dispatch`

### Manual Deployment
For local testing or manual deployment:

1. Set environment variables:
```bash
export ACR_REGISTRY="myregistry.azurecr.io"
export ACR_USERNAME="myusername"
export ACR_PASSWORD="mypassword"
```

2. Generate artifacts:
```bash
python3 scripts/generate_addon_artifacts.py
```

3. Deploy using Helm (see individual component sections below)

## Components

### NGINX Ingress Controller
- **Namespace**: `ingress-nginx`
- **Service Type**: LoadBalancer
- **Values**: `infra/addons/values/ingress-nginx.yaml`

### Prometheus Stack
- **Namespace**: `monitoring`
- **Components**:
  - Prometheus (NodePort 30001)
  - Grafana (NodePort 30000, default credentials: admin/admin)
  - Alertmanager (NodePort 30002)
- **Values**: `infra/addons/values/observability.yaml` → `observability.acr.yaml` (generated)

### Metrics Server
- **Namespace**: `kube-system`
- Enables `kubectl top` and HorizontalPodAutoscaler

### Local Path Provisioner
- **Namespace**: `local-path-storage` (or `kube-system` for k3s)
- Provides local storage via StorageClass `local-path`

## Accessing Dashboards

After deployment, access dashboards via NodePort:

- **Grafana**: `http://<NODE_IP>:30000` (admin/admin)
- **Prometheus**: `http://<NODE_IP>:30001`
- **Alertmanager**: `http://<NODE_IP>:30002`

## Troubleshooting

### Image Pull Errors
If pods fail with `ImagePullBackOff`:
1. Verify ACR credentials are correct
2. Check ServiceAccounts have `acr-pull` ImagePullSecret
3. Ensure images were successfully mirrored to ACR

### Helm Deployment Issues
The workflow includes extensive cleanup logic for stuck Helm releases. If deployment fails:
1. Check workflow logs for cleanup steps
2. Manually clean up Helm secrets/configmaps if needed
3. Re-run the workflow

### Traefik Conflicts (k3s)
The workflow automatically removes Traefik (k3s default) to avoid port conflicts with NGINX. To permanently disable Traefik, add `--disable traefik` to k3s startup flags.

## Development

### Adding New Images
1. Add image configuration to values files (`observability.yaml` or `ingress-nginx.yaml`)
2. The Python script will automatically detect and add to `image-map.txt`
3. Workflow will mirror images to ACR

### Modifying Values
- Edit values files in `infra/addons/values/`
- Changes trigger automatic deployment on push to `main`

## License

[Add your license here]

