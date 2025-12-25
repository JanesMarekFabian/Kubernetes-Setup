# Monitoring Stack Component

Prometheus, Grafana, and Alertmanager monitoring stack for Kubernetes.

## Components

- **Prometheus** - Metrics collection and storage
- **Grafana** - Visualization and dashboards
- **Alertmanager** - Alert management
- **Node Exporter** - Node metrics
- **Kube State Metrics** - Kubernetes object metrics

## Configuration

- **Namespace**: `monitoring`
- **Values File**: `monitoring/values.yaml`
- **Generated Values**: `monitoring/values.acr.yaml` (auto-generated with ACR registry)

## Ports

- **Grafana**: NodePort 30000 (http://<NODE_IP>:30000)
- **Prometheus**: NodePort 30001 (http://<NODE_IP>:30001)
- **Alertmanager**: NodePort 30002 (http://<NODE_IP>:30002)

## Default Credentials

- **Grafana**: admin/admin (change in values.yaml)

## Deployment

The component is deployed via GitHub Actions workflow when files in `monitoring/` change.

### Manual Deployment

1. Generate ACR values:
```bash
export ACR_REGISTRY="myregistry.azurecr.io"
python3 monitoring/scripts/generate_images.py
```

2. Deploy with Helm:
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  -f monitoring/values.acr.yaml \
  --set prometheusOperator.image.repository="${ACR_REGISTRY}/prometheus-community/kube-prometheus-stack-prometheus-operator" \
  --set prometheusOperator.image.tag="v0.79.2"
```

## Access

- **Grafana**: `http://<NODE_IP>:30000` (admin/admin)
- **Prometheus**: `http://<NODE_IP>:30001`
- **Alertmanager**: `http://<NODE_IP>:30002`

## Image Mirroring

The workflow automatically:
1. Generates `image-map.txt` from values.yaml
2. Extracts additional images from Helm chart defaults
3. Mirrors all images to ACR
4. Generates `values.acr.yaml` with ACR registry rewrites

