#!/usr/bin/env bash
set -euo pipefail

NAMESPACE=${1:-apps}
SECRET_NAME=${2:-acr-pull}
REGISTRY=${ACR_REGISTRY:?ACR_REGISTRY not set}
USERNAME=${ACR_USERNAME:?ACR_USERNAME not set}
PASSWORD=${ACR_PASSWORD:?ACR_PASSWORD not set}

kubectl get ns "$NAMESPACE" >/dev/null 2>&1 || kubectl create namespace "$NAMESPACE"

if kubectl -n "$NAMESPACE" get secret "$SECRET_NAME" >/dev/null 2>&1; then
  kubectl -n "$NAMESPACE" delete secret "$SECRET_NAME"
fi

kubectl -n "$NAMESPACE" create secret docker-registry "$SECRET_NAME" \
  --docker-server="${REGISTRY}" \
  --docker-username="${USERNAME}" \
  --docker-password="${PASSWORD}"

kubectl -n "$NAMESPACE" patch serviceaccount default \
  -p "{\"imagePullSecrets\":[{\"name\":\"$SECRET_NAME\"}]}"

echo "imagePullSecret '$SECRET_NAME' ensured in namespace '$NAMESPACE'"


