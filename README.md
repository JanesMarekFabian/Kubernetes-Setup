# Kubernetes Infrastructure Deployment

This repository contains the base Kubernetes infrastructure deployment configuration for deploying essential add-ons using Helm charts with container image mirroring to Azure Container Registry (ACR).

## Overview

This project automates the deployment of:
- **NGINX Ingress Controller** - For ingress traffic management
- **Prometheus Stack** (kube-prometheus-stack) - Monitoring, alerting, and observability
- **Metrics Server** - For resource metrics (kubectl top, HPA)
- **Local Path Provisioner** - For local storage (k3s compatible)
- **Cluster Storage Configuration** - Centralized storage management via Helm

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
│   ├── charts/
│   │   └── cluster-storage/     # Helm chart for centralized storage config
│   ├── rbac/
│   │   └── cicd-serviceaccount.yaml  # RBAC for CI/CD ServiceAccount
│   └── templates/               # Templates for projects
│       ├── project-storage-rbac.yaml
│       └── project-storage-rbac-helm.yaml
├── docs/
│   └── PROJECT_STANDARDS.md     # Standards for other projects
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
2. **Cluster Storage Configuration** - Centralized ConfigMap via Helm Chart
3. **Metrics Server** - Resource metrics
4. **NGINX Ingress Controller** - Ingress traffic
5. **Monitoring Stack** - Prometheus, Grafana, Alertmanager

### 3. Image Registry Handling
- All images are rewritten to use ACR registry
- ServiceAccounts are patched with ACR pull secrets
- Helm Post-Renderer ensures all images use ACR (including nested structures)

### 4. Centralized Storage Management
- Storage configuration is managed via Helm Chart (`cluster-storage`)
- Projects can access storage configuration via RBAC (`local-path-config-reader` ClusterRole)
- See [PROJECT_STANDARDS.md](docs/PROJECT_STANDARDS.md) for project integration

## Usage

### Automatic Deployment (CI/CD)
The workflow triggers automatically on:
- Push to `main` branch when files in `infra/addons/**`, `infra/rbac/**`, `infra/charts/**`, or `.github/workflows/build-push.yml` change
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

### Cluster Storage Configuration
- **Helm Chart**: `infra/charts/cluster-storage`
- **ConfigMap**: `local-path-config` (in provisioner namespace)
- **ClusterRole**: `local-path-config-reader` (for project access)
- **Purpose**: Centralized management of storage configuration

## Accessing Dashboards

After deployment, access dashboards via NodePort:

- **Grafana**: `http://<NODE_IP>:30000` (admin/admin)
- **Prometheus**: `http://<NODE_IP>:30001`
- **Alertmanager**: `http://<NODE_IP>:30002`

## For Other Projects

If you're deploying a project to this cluster, see **[PROJECT_STANDARDS.md](docs/PROJECT_STANDARDS.md)** for:
- How to configure storage access
- RBAC requirements
- Helm Chart standards
- Best practices

Quick start for projects:
1. Create namespace and ServiceAccount
2. Add RBAC for storage access (see `infra/templates/project-storage-rbac.yaml`)
3. Use `storageClassName: local-path` in PVCs

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

### Storage Issues
If PVCs remain in "Pending" state:
1. Check StorageClass exists: `kubectl get storageclass local-path`
2. Verify RBAC: `kubectl get clusterrole local-path-config-reader`
3. Check provisioner logs: `kubectl logs -n kube-system -l app=local-path-provisioner`

## Development

### Adding New Images
1. Add image configuration to values files (`observability.yaml` or `ingress-nginx.yaml`)
2. The Python script will automatically detect and add to `image-map.txt`
3. Workflow will mirror images to ACR

### Modifying Values
- Edit values files in `infra/addons/values/`
- Changes trigger automatic deployment on push to `main`

### Modifying Storage Configuration
- Edit `infra/charts/cluster-storage/values.yaml`
- Changes trigger automatic deployment on push to `main`
- Provisioner will be restarted automatically to pick up changes

## License

Copyright (c) 2024 [Dein Name oder Unternehmen]. All rights reserved.

See [LICENSE](LICENSE) file for details.
