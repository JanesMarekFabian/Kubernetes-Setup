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
│       ├── longhorn-deploy.yml      # Longhorn Storage Deployment
│       ├── metrics-server-deploy.yml # Metrics Server Deployment
│       ├── ingress-deploy.yml       # NGINX Ingress Deployment
│       └── monitoring-deploy.yml    # Monitoring Stack Deployment
├── longhorn/                    # Storage-Komponente
│   ├── values.yaml
│   └── README.md
├── metrics-server/              # Metrics-Komponente
│   └── README.md
├── ingress/                    # NGINX Ingress Controller
│   ├── values.yaml
│   └── README.md
├── monitoring/                 # Prometheus/Grafana Stack
│   ├── values.yaml
│   ├── scripts/
│   │   └── generate_images.py
│   └── README.md
├── infra/
│   ├── charts/
│   │   └── cluster-storage/     # Helm chart for centralized storage config
│   ├── rbac/
│   │   └── cicd-serviceaccount.yaml  # RBAC for CI/CD ServiceAccount
│   └── templates/               # Templates for projects
│       ├── project-storage-rbac.yaml
│       └── project-storage-rbac-helm.yaml
└── docs/
    └── PROJECT_STANDARDS.md     # Standards for other projects
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

### 2. Component-Based Deployment
Each component has its own workflow and can be deployed independently:
1. **Longhorn Storage** - Enterprise-grade distributed storage
2. **Metrics Server** - Resource metrics (kubectl top, HPA)
3. **NGINX Ingress Controller** - Ingress traffic management
4. **Monitoring Stack** - Prometheus, Grafana, Alertmanager

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
Each component workflow triggers automatically on:
- Push to `main` branch when files in the respective component directory change (e.g., `longhorn/**`, `monitoring/**`)
- Manual trigger via `workflow_dispatch`

### Manual Deployment
Each component can be deployed manually. See the respective component README files:
- `longhorn/README.md` - Longhorn Storage
- `metrics-server/README.md` - Metrics Server
- `ingress/README.md` - NGINX Ingress Controller
- `monitoring/README.md` - Monitoring Stack

## Components

### Longhorn Storage
- **Namespace**: `longhorn-system`
- **StorageClass**: `longhorn` (default)
- **Features**: Replication, Snapshots, Backups, Web UI
- **Workflow**: `.github/workflows/longhorn-deploy.yml`
- **Configuration**: `longhorn/values.yaml`
- **Documentation**: `longhorn/README.md`

### Monitoring Stack
- **Namespace**: `monitoring`
- **Components**: Prometheus, Grafana, Alertmanager, Node Exporter, Kube State Metrics
- **Ports**: Grafana (30000), Prometheus (30001), Alertmanager (30002)
- **Workflow**: `.github/workflows/monitoring-deploy.yml`
- **Configuration**: `monitoring/values.yaml`
- **Documentation**: `monitoring/README.md`

### NGINX Ingress Controller
- **Namespace**: `ingress-nginx`
- **Service Type**: NodePort (HTTP: 80, HTTPS: 443)
- **Ingress Class**: `nginx`
- **Workflow**: `.github/workflows/ingress-deploy.yml`
- **Configuration**: `ingress/values.yaml`
- **Documentation**: `ingress/README.md`

### Metrics Server
- **Namespace**: `kube-system`
- **Function**: Enables `kubectl top` and HorizontalPodAutoscaler
- **Workflow**: `.github/workflows/metrics-server-deploy.yml`
- **Documentation**: `metrics-server/README.md`

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
3. Use `storageClassName: longhorn` in PVCs

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
1. Check StorageClass exists: `kubectl get storageclass longhorn`
2. Verify Longhorn pods: `kubectl get pods -n longhorn-system`
3. Check Longhorn manager logs: `kubectl logs -n longhorn-system -l app=longhorn-manager`
4. Verify RBAC: `kubectl get rolebinding longhorn-storage-reader -n <your-namespace>`

## Development

### Adding New Images
1. Add image configuration to component values files (e.g., `monitoring/values.yaml`)
2. Component-specific scripts will automatically detect and add to `image-map.txt`
3. Workflow will mirror images to ACR

### Modifying Component Values
- Edit values files in component directories (e.g., `longhorn/values.yaml`, `monitoring/values.yaml`)
- Changes trigger automatic deployment for that specific component on push to `main`

### Modifying Storage Configuration
- Edit `infra/charts/cluster-storage/values.yaml`
- Changes trigger automatic deployment on push to `main`

## License

Copyright (c) 2024 [Dein Name oder Unternehmen]. All rights reserved.

See [LICENSE](LICENSE) file for details.
