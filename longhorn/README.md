# Longhorn Storage Component

Enterprise-grade distributed storage for Kubernetes.

## Features

- Replication between nodes (HA)
- Snapshots and backups
- Volume cloning
- Web UI for management
- Default StorageClass

## Configuration

- **Namespace**: `longhorn-system`
- **StorageClass**: `longhorn` (set as default)
- **Values File**: `longhorn/values.yaml`

## Deployment

The component is deployed via GitHub Actions workflow when files in `longhorn/` change.

### Manual Deployment

```bash
helm repo add longhorn https://charts.longhorn.io
helm repo update

helm upgrade --install longhorn longhorn/longhorn \
  --namespace longhorn-system \
  --create-namespace \
  --values longhorn/values.yaml \
  --set longhorn.image.longhorn.repository="${ACR_REGISTRY}/longhornio/longhorn-manager" \
  --set longhorn.image.longhorn.tag="v1.7.0"
```

## Access

- **Web UI**: Available via Ingress at `longhorn.local` (if ingress is enabled)
- **StorageClass**: `kubectl get storageclass longhorn`

