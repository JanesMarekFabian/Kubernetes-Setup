# Project Templates

Diese Templates helfen anderen Projekten, sich an die Cluster-Standards anzupassen.

## Storage RBAC Template

### Für kubectl-basierte Deployments

Verwende `project-storage-rbac.yaml`:

1. Kopiere die Datei in dein Projekt
2. Ersetze die Platzhalter:
   - `${PROJECT_NAMESPACE}` → Dein Namespace
   - `${PROJECT_SERVICE_ACCOUNT}` → Dein ServiceAccount
3. Apply via `kubectl apply -f k8s/rbac/storage-access.yaml`

### Für Helm-basierte Deployments

Verwende `project-storage-rbac-helm.yaml`:

1. Kopiere die Datei in `charts/<your-chart>/templates/rbac/storage-access.yaml`
2. Füge in `values.yaml` hinzu:
   ```yaml
   storageAccess:
     enabled: true
     serviceAccount: your-service-account-name
   ```
3. Helm wird die RBAC automatisch erstellen

## Beispiel-Integration

Siehe `docs/PROJECT_STANDARDS.md` für vollständige Beispiele.

