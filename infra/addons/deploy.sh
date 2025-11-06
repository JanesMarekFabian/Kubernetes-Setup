#!/usr/bin/env bash
set -euo pipefail

# Netzwerk: NGINX Ingress Controller
kubectl get ns ingress-nginx >/dev/null 2>&1 || kubectl create namespace ingress-nginx
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  -n ingress-nginx \
  -f infra/addons/values/ingress-nginx.yaml \
  --wait

# Monitoring: kube-prometheus-stack (Prometheus, Alertmanager, Grafana)
kubectl get ns monitoring >/dev/null 2>&1 || kubectl create namespace monitoring
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring \
  -f infra/addons/values/observability.yaml \
  --wait

# Extra: metrics-server (ermöglicht kubectl top / HPA)
if ! kubectl -n kube-system get deploy metrics-server >/dev/null 2>&1; then
  kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
fi

# Speicher: k3s hat local-path-provisioner bereits; für Nicht-k3s optional aktivieren
# Hinweis: Wenn nicht k3s, kann folgender Block genutzt werden (auskommentiert lassen, falls k3s):
# kubectl get ns storage >/dev/null 2>&1 || kubectl create namespace storage
# helm repo add rancher-lpp https://rancher.github.io/local-path-provisioner/
# helm upgrade --install local-path-provisioner rancher-lpp/local-path-provisioner \
#   -n storage --wait

echo "Add-ons deployed: ingress-nginx, kube-prometheus-stack, metrics-server"


