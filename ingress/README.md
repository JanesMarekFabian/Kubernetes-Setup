# NGINX Ingress Controller Component

NGINX Ingress Controller for managing ingress traffic in Kubernetes.

## Features

- Load balancing
- SSL/TLS termination
- Name-based virtual hosting
- Metrics enabled for Prometheus

## Configuration

- **Namespace**: `ingress-nginx`
- **Service Type**: NodePort
- **Ports**: HTTP (80), HTTPS (443)
- **Values File**: `ingress/values.yaml`

## Deployment

The component is deployed via GitHub Actions workflow when files in `ingress/` change.

### Manual Deployment

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --values ingress/values.yaml \
  --set controller.image.repository="${ACR_REGISTRY}/ingress-nginx/controller" \
  --set controller.image.tag="v1.11.1"
```

## Access

- **Service**: `kubectl get svc -n ingress-nginx`
- **Ingress Class**: `nginx` (default)

## Notes

- Traefik (k3s default) is automatically removed during deployment to avoid port conflicts
- The ingress controller uses NodePort for external access

