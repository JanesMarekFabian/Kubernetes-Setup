# Kubernetes Project Standards

Dieses Dokument beschreibt die Standards für Projekte, die auf diesem Kubernetes-Cluster deployed werden sollen.

## Übersicht

Dieser Cluster verwendet ein **zentralisiertes Management-System** für gemeinsame Infrastruktur-Komponenten. Projekte können diese Komponenten nutzen, müssen sich aber an bestimmte Standards halten.

## Architektur-Prinzipien

### 1. Separation of Concerns

```
┌─────────────────────────────────────────┐
│ Infrastructure Repo (dieses Repo)      │
│ - Cluster-weite Komponenten            │
│ - Base RBAC                             │
│ - Storage/Networking Setup              │
└─────────────────────────────────────────┘
           ↓ (deployed via CI/CD)
┌─────────────────────────────────────────┐
│ CLUSTER                                 │
│ ┌─────────────────────────────────────┐ │
│ │ kube-system/                       │ │
│ │   - local-path-provisioner          │ │
│ │   - ConfigMap: local-path-config   │ │ ← ZENTRAL
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ <your-project>/                    │ │
│ │   - App Components                  │ │
│ │   - RBAC für Storage-Zugriff       │ │ ← PROJEKT
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 2. RBAC: Least Privilege

- **ClusterRoles**: Werden zentral verwaltet (Infrastructure Repo)
- **RoleBindings**: Werden pro Projekt erstellt
- **ServiceAccounts**: Pro Projekt, mit minimalen Rechten

### 3. GitOps-Prinzipien

- ✅ Alles in Git versioniert
- ✅ Helm Charts für Deployments
- ✅ CI/CD für automatische Deployments
- ❌ Keine manuellen `kubectl apply` ohne Git-Commit

## Standards für Projekte

### 1. Namespace-Struktur

Jedes Projekt sollte einen eigenen Namespace haben:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: <project-name>
  labels:
    app.kubernetes.io/name: <project-name>
    app.kubernetes.io/managed-by: helm
```

### 2. ServiceAccount

Jedes Projekt benötigt einen ServiceAccount für CI/CD:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: <project>-deploy
  namespace: <project-name>
```

### 3. Storage-Zugriff (Local Path Provisioner)

#### Schritt 1: RBAC für Storage-Zugriff

Erstelle eine `RoleBinding` in deinem Projekt:

```yaml
# k8s/rbac/storage-access.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: local-path-config-reader
  namespace: <your-project-namespace>
roleRef:
  kind: ClusterRole
  name: local-path-config-reader  # Wird zentral erstellt
  apiGroup: rbac.authorization.k8s.io
subjects:
  - kind: ServiceAccount
    name: <your-service-account>
    namespace: <your-project-namespace>
```

#### Schritt 2: PVC mit StorageClass

Verwende die zentrale StorageClass:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: <your-pvc-name>
  namespace: <your-project-namespace>
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path  # Zentrale StorageClass
  resources:
    requests:
      storage: 10Gi
```

### 4. Helm Chart-Struktur

Projekte sollten Helm Charts verwenden:

```
your-project/
├── charts/
│   └── your-app/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── pvc.yaml
│           └── rbac/
│               └── storage-access.yaml
└── values/
    └── production.yaml
```

### 5. Image-Registry

**Wichtig**: Alle Images müssen über Azure Container Registry (ACR) bereitgestellt werden.

```yaml
# In values.yaml
image:
  registry: <your-acr-registry>.azurecr.io
  repository: <your-image>
  tag: "latest"
```

### 6. Labels und Annotations

Verwende standardisierte Labels:

```yaml
metadata:
  labels:
    app.kubernetes.io/name: <app-name>
    app.kubernetes.io/instance: <release-name>
    app.kubernetes.io/version: <version>
    app.kubernetes.io/managed-by: helm
    app.kubernetes.io/component: <component-type>
```

## Checkliste für neue Projekte

- [ ] Namespace erstellt
- [ ] ServiceAccount erstellt
- [ ] RBAC für Storage-Zugriff konfiguriert (`local-path-config-reader`)
- [ ] Helm Chart erstellt (falls nicht vorhanden)
- [ ] Images über ACR bereitgestellt
- [ ] Labels standardisiert
- [ ] CI/CD Pipeline konfiguriert
- [ ] Dokumentation erstellt

## Beispiel: Vollständiges Projekt-Setup

### 1. Namespace und ServiceAccount

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-project
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-project-deploy
  namespace: my-project
```

### 2. Storage-RBAC

```yaml
# k8s/rbac/storage-access.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: local-path-config-reader
  namespace: my-project
roleRef:
  kind: ClusterRole
  name: local-path-config-reader
  apiGroup: rbac.authorization.k8s.io
subjects:
  - kind: ServiceAccount
    name: my-project-deploy
    namespace: my-project
```

### 3. PVC-Beispiel

```yaml
# k8s/pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-project-data
  namespace: my-project
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 20Gi
```

### 4. Deployment mit PVC

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-project
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: my-project-deploy
      containers:
      - name: app
        image: <acr-registry>.azurecr.io/my-app:latest
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: my-project-data
```

## Troubleshooting

### PVC bleibt im Status "Pending"

1. Prüfe, ob StorageClass existiert:
   ```bash
   kubectl get storageclass local-path
   ```

2. Prüfe, ob RBAC korrekt konfiguriert ist:
   ```bash
   kubectl get rolebinding local-path-config-reader -n <your-namespace>
   ```

3. Prüfe Provisioner-Logs:
   ```bash
   kubectl logs -n kube-system -l app=local-path-provisioner
   ```

### ImagePullBackOff

1. Prüfe, ob Image in ACR vorhanden ist
2. Prüfe ServiceAccount ImagePullSecrets:
   ```bash
   kubectl get serviceaccount <sa-name> -n <namespace> -o yaml
   ```

## Weitere Ressourcen

- [Kubernetes RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Helm Documentation](https://helm.sh/docs/)
- [Local Path Provisioner](https://github.com/rancher/local-path-provisioner)

## Support

Bei Fragen oder Problemen:
1. Prüfe diese Dokumentation
2. Prüfe Cluster-Logs
3. Kontaktiere das Infrastructure-Team

