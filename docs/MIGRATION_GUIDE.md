# Migration Guide: Von manueller ConfigMap zu Helm Chart

Dieses Dokument beschreibt die Änderungen am Storage-Management-System.

## Was hat sich geändert?

### Vorher
- ConfigMap wurde manuell via `kubectl apply` erstellt
- Keine Versionierung der Storage-Konfiguration
- Projekte hatten keinen standardisierten Zugriff

### Nachher
- ConfigMap wird via Helm Chart (`cluster-storage`) verwaltet
- Versionierung und Rollback möglich
- Projekte können über RBAC (`local-path-config-reader`) auf ConfigMap zugreifen
- Standardisierte Templates für Projekte

## Für Infrastructure-Team

### Workflow-Änderungen

Der Workflow wurde refactored:

**Alt:**
```yaml
- name: Configure Helper-Pod Image
  run: |
    # Manuelle ConfigMap-Erstellung
    kubectl apply -f - <<EOF
    ...
    EOF
```

**Neu:**
```yaml
- name: Deploy Cluster Storage Configuration
  run: |
    # Helm Chart Deployment
    helm upgrade --install cluster-storage ./infra/charts/cluster-storage \
      --set localPathProvisioner.configMap.helperPod.image="${ACR_REGISTRY}/busybox:1.36"
```

### Neue Dateien

- `infra/charts/cluster-storage/` - Helm Chart für Storage-Konfiguration
- `infra/templates/` - Templates für Projekte
- `docs/PROJECT_STANDARDS.md` - Dokumentation für Projekte
- `docs/ARCHITECTURE.md` - Architektur-Dokumentation

### Migration

Keine manuelle Migration nötig! Der Workflow migriert automatisch:
1. Helm Chart erstellt/aktualisiert ConfigMap
2. ClusterRole wird erstellt
3. Provisioner wird automatisch neu gestartet

## Für Projekte

### Neue Projekte

Folge den Schritten in [PROJECT_STANDARDS.md](PROJECT_STANDARDS.md):

1. Erstelle Namespace und ServiceAccount
2. Füge RBAC hinzu (siehe `infra/templates/project-storage-rbac.yaml`)
3. Verwende `storageClassName: local-path` in PVCs

### Bestehende Projekte

**Option 1: Minimal (nur RBAC hinzufügen)**

Füge diese Datei zu deinem Projekt hinzu:

```yaml
# k8s/rbac/storage-access.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: local-path-config-reader
  namespace: <your-namespace>
roleRef:
  kind: ClusterRole
  name: local-path-config-reader
  apiGroup: rbac.authorization.k8s.io
subjects:
  - kind: ServiceAccount
    name: <your-service-account>
    namespace: <your-namespace>
```

**Option 2: Helm Chart (empfohlen)**

Füge das Template aus `infra/templates/project-storage-rbac-helm.yaml` zu deinem Helm Chart hinzu.

## Vorteile

1. **Versionierung**: Storage-Konfiguration ist jetzt versioniert
2. **Rollback**: Helm ermöglicht einfaches Rollback
3. **Standardisierung**: Projekte folgen einem Standard
4. **RBAC**: Projekte können ConfigMap lesen (für Debugging)
5. **Wartbarkeit**: Zentrale Verwaltung vereinfacht Updates

## Troubleshooting

### ConfigMap wird nicht aktualisiert

1. Prüfe Helm Release:
   ```bash
   helm list -n kube-system
   helm get values cluster-storage -n kube-system
   ```

2. Prüfe ConfigMap:
   ```bash
   kubectl get configmap local-path-config -n kube-system -o yaml
   ```

3. Prüfe Provisioner-Logs:
   ```bash
   kubectl logs -n kube-system -l app=local-path-provisioner
   ```

### Projekte können ConfigMap nicht lesen

1. Prüfe ClusterRole:
   ```bash
   kubectl get clusterrole local-path-config-reader
   ```

2. Prüfe RoleBinding im Projekt-Namespace:
   ```bash
   kubectl get rolebinding local-path-config-reader -n <project-namespace>
   ```

3. Teste Zugriff:
   ```bash
   kubectl auth can-i get configmap/local-path-config -n kube-system --as=system:serviceaccount:<namespace>:<serviceaccount>
   ```

## Rollback

Falls Probleme auftreten:

```bash
# Helm Rollback
helm rollback cluster-storage -n kube-system

# Oder manuell ConfigMap wiederherstellen (nur im Notfall)
kubectl apply -f <backup-configmap.yaml>
```

## Support

Bei Fragen siehe:
- [PROJECT_STANDARDS.md](PROJECT_STANDARDS.md) - Für Projekte
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architektur-Übersicht
- Workflow-Logs für Deployment-Details

