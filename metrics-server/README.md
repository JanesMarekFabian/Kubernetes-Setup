# Metrics Server Component

Kubernetes Metrics Server for resource metrics collection.

## Features

- Enables `kubectl top` command
- Required for HorizontalPodAutoscaler (HPA)
- Collects CPU and memory metrics from nodes and pods

## Configuration

- **Namespace**: `kube-system`
- **Deployment**: Deployed via kubectl (no Helm chart)

## Deployment

The component is deployed via GitHub Actions workflow when files in `metrics-server/` change.

### Manual Deployment

```bash
# Get latest version
VERSION=$(curl -s https://api.github.com/repos/kubernetes-sigs/metrics-server/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

# Deploy with ACR image
curl -sL https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml | \
  sed "s|registry.k8s.io/metrics-server/metrics-server|${ACR_REGISTRY}/metrics-server/metrics-server|g" | \
  sed "s|:v[0-9.]*|:${VERSION}|g" | \
  kubectl apply -f -
```

## Verification

```bash
# Check if metrics-server is running
kubectl get pods -n kube-system -l k8s-app=metrics-server

# Check API service
kubectl get apiservice v1beta1.metrics.k8s.io

# Test metrics
kubectl top nodes
kubectl top pods
```

