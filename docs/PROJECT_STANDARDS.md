# Kubernetes Infrastructure & Project Standards

Dieses Dokument beschreibt die Architektur des Kubernetes-Clusters, die Infrastruktur-Komponenten und die Standards für Projekte, die auf diesem Cluster deployed werden sollen.

## Inhaltsverzeichnis

1. [Cluster-Architektur](#cluster-architektur)
2. [Infrastruktur-Komponenten](#infrastruktur-komponenten)
3. [Projekt-Standards](#projekt-standards)
4. [RBAC & ServiceAccounts](#rbac--serviceaccounts)
5. [Storage-Verwaltung](#storage-verwaltung)
6. [CI/CD & Deployment](#cicd--deployment)
7. [Troubleshooting](#troubleshooting)

---

## Cluster-Architektur

### Architektur-Schichten

```
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: INFRASTRUCTURE (Dieses Repo)                  │
│ - Cluster-weite Komponenten                             │
│ - Base RBAC                                             │
│ - Storage/Networking Setup                              │
│ - Monitoring Stack                                      │
└─────────────────────────────────────────────────────────┘
                    ↓ (deployed via CI/CD)
┌─────────────────────────────────────────────────────────┐
│ LAYER 2: CLUSTER RESOURCES                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ longhorn-system/                                    │ │
│ │   - Longhorn Storage                                │ │
│ │   - StorageClass: longhorn                          │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ monitoring/                                         │ │
│ │   - Prometheus, Grafana, Alertmanager               │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ingress-nginx/                                      │ │
│ │   - NGINX Ingress Controller                        │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ kube-system/                                        │ │
│ │   - Metrics Server                                  │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                    ↓ (projects deploy here)
┌─────────────────────────────────────────────────────────┐
│ LAYER 3: PROJECT NAMESPACES                             │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ <project-namespace>/                                │ │
│ │   - App Components                                   │ │
│ │   - PVCs (storageClassName: longhorn)               │ │
│ │   - RBAC für Storage-Zugriff                        │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Design-Prinzipien

1. **Separation of Concerns**
   - Infrastructure Repo: Verwaltet Cluster-weite Ressourcen
   - Project Repos: Verwalten nur ihre eigenen Ressourcen
   - RBAC: Projekte erhalten minimale, spezifische Rechte

2. **GitOps**
   - Alles ist in Git versioniert
   - CI/CD automatisiert Deployments
   - Keine manuellen `kubectl apply` ohne Git-Commit

3. **Komponentenbasierte Struktur**
   - Jede Komponente hat eigenen Ordner und Workflow
   - Unabhängige Deployments pro Komponente
   - Helm Charts für alle Komponenten

4. **RBAC: Least Privilege**
   - ClusterRoles für gemeinsame Ressourcen
   - RoleBindings pro Projekt
   - ServiceAccounts mit minimalen Rechten

---

## Infrastruktur-Komponenten

### Projekt-Struktur

```
.
├── .github/
│   ├── actions/
│   │   └── setup-cicd/          # GitHub Action für CI/CD Setup
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
│   │   └── cluster-storage/    # Helm Chart für Storage-Konfiguration
│   ├── rbac/
│   │   └── cicd-serviceaccount.yaml  # CI/CD RBAC
│   └── templates/              # Templates für Projekte
└── docs/
    └── PROJECT_STANDARDS.md    # Dieses Dokument
```

### Komponenten-Übersicht

#### Longhorn Storage
- **Namespace**: `longhorn-system`
- **StorageClass**: `longhorn` (default)
- **Features**: Replikation, Snapshots, Backups, Web UI
- **Workflow**: `.github/workflows/longhorn-deploy.yml`
- **Konfiguration**: `longhorn/values.yaml`

#### Monitoring Stack
- **Namespace**: `monitoring`
- **Komponenten**: Prometheus, Grafana, Alertmanager, Node Exporter, Kube State Metrics
- **Ports**: Grafana (30000), Prometheus (30001), Alertmanager (30002)
- **Workflow**: `.github/workflows/monitoring-deploy.yml`
- **Konfiguration**: `monitoring/values.yaml`

#### NGINX Ingress Controller
- **Namespace**: `ingress-nginx`
- **Service Type**: NodePort (HTTP: 80, HTTPS: 443)
- **Ingress Class**: `nginx`
- **Workflow**: `.github/workflows/ingress-deploy.yml`
- **Konfiguration**: `ingress/values.yaml`

#### Metrics Server
- **Namespace**: `kube-system`
- **Funktion**: Ermöglicht `kubectl top` und HorizontalPodAutoscaler
- **Workflow**: `.github/workflows/metrics-server-deploy.yml`

---

## Projekt-Standards

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

### 2. ServiceAccounts

#### Entscheidungsbaum

```
Braucht deine App Kubernetes API-Zugriffe?
│
├─ NEIN → Verwende default ServiceAccount
│   └─ Keine RBAC-Konfiguration nötig
│   └─ Sicherste Option (keine Cluster-Rechte)
│
└─ JA → Braucht sie Cluster-weite Rechte?
    │
    ├─ NEIN → Erstelle namespace-scoped Role + RoleBinding
    │   └─ Verwende default ODER eigenen ServiceAccount
    │
    └─ JA → Konsultiere Infrastructure Repo
        └─ Verwende zentrale ClusterRoles (z.B. longhorn-storage-reader)
```

#### Default ServiceAccount (Standard)

**Empfehlung**: Die meisten Pods können den `default` ServiceAccount verwenden:

```yaml
# Deployment ohne serviceAccountName = verwendet automatisch default
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      # Kein serviceAccountName = verwendet default (keine Cluster-Rechte)
      containers:
      - name: app
        image: ...
```

**Vorteile:**
- ✅ Keine zusätzliche Konfiguration nötig
- ✅ Keine Cluster-Rechte (sicher)
- ✅ Funktioniert für die meisten einfachen Anwendungen

#### CI/CD ServiceAccount (für Deployments)

**Wichtig**: Dieser ServiceAccount wird **nur von der CI/CD-Pipeline** verwendet:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: <project>-deploy
  namespace: <project-name>
  labels:
    app.kubernetes.io/name: <project>
    app.kubernetes.io/component: cicd
```

**Sicherheitshinweise:**
- ⚠️ **NUR für CI/CD verwenden** - niemals für laufende Pods!
- ⚠️ Hat cluster-weite Rechte (via ClusterRoleBinding)

#### Runtime ServiceAccount (nur wenn Rechte benötigt werden)

**WICHTIG**: Erstelle diesen ServiceAccount **nur**, wenn deine App spezifische Rechte benötigt:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: <project>-app
  namespace: <project-name>
  labels:
    app.kubernetes.io/name: <project>
    app.kubernetes.io/component: runtime
```

---

## RBAC & ServiceAccounts

### CI/CD RBAC

**Wichtig**: Der Cluster stellt eine zentrale `cicd-deploy-role` bereit. Projekte müssen **keine eigenen ClusterRoles** erstellen.

#### Projekt-spezifische ClusterRoleBinding

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: <project>-cicd-deploy-binding
  labels:
    app.kubernetes.io/name: <project>
    app.kubernetes.io/component: cicd-rbac
roleRef:
  kind: ClusterRole
  name: cicd-deploy-role  # Zentrale ClusterRole
  apiGroup: rbac.authorization.k8s.io
subjects:
  - kind: ServiceAccount
    name: <project>-deploy  # CI/CD ServiceAccount
    namespace: <project-namespace>
```

**⚠️ Wichtig**: 
- Binde hier **NUR** den CI/CD ServiceAccount (`<project>-deploy`), **NICHT** den Runtime ServiceAccount!
- Verwende einen **eindeutigen Namen**: `<project>-cicd-deploy-binding`
- **NICHT** `cicd-deploy-binding` verwenden - dieser Name ist für das Infrastructure Repo reserviert!

### Runtime RBAC (nur wenn Rechte benötigt werden)

**Wichtig**: Die meisten Apps brauchen **keine RBAC** und können den `default` ServiceAccount verwenden.

#### Beispiel: Namespace-scoped Role

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: <project>-app-role
  namespace: <project-namespace>
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]  # Nur Lesen!
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: <project>-app-binding
  namespace: <project-namespace>
roleRef:
  kind: Role
  name: <project>-app-role
  apiGroup: rbac.authorization.k8s.io
subjects:
  - kind: ServiceAccount
    name: <project>-app
    namespace: <project-namespace>
```

**Sicherheitsprinzipien:**
- ✅ **Default zuerst**: Verwende `default` ServiceAccount wenn möglich
- ✅ **Least Privilege**: Nur die Rechte, die die App wirklich braucht
- ✅ **Namespace-scoped**: Keine ClusterRoleBinding für Runtime
- ✅ **Read-only wo möglich**: ConfigMaps/Secrets nur lesen

---

## Storage-Verwaltung

### Longhorn StorageClass

Der Cluster verwendet **Longhorn** als Standard-StorageClass:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: <your-pvc-name>
  namespace: <your-project-namespace>
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn  # Zentrale StorageClass
  resources:
    requests:
      storage: 10Gi
```

### Storage RBAC (nur wenn benötigt)

Falls deine App Zugriff auf Storage-ConfigMaps benötigt:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: longhorn-storage-reader
  namespace: <your-project-namespace>
roleRef:
  kind: ClusterRole
  name: longhorn-storage-reader  # Zentrale ClusterRole
  apiGroup: rbac.authorization.k8s.io
subjects:
  - kind: ServiceAccount
    name: <your-service-account>
    namespace: <your-project-namespace>
```

**Templates**: Siehe `infra/templates/project-storage-rbac.yaml` oder `infra/templates/project-storage-rbac-helm.yaml`

---

## CI/CD & Deployment

### GitHub Actions Workflows

Jede Komponente hat einen eigenen Workflow:
- **Trigger**: Push zu `main` Branch wenn Dateien in der Komponente geändert werden
- **Manuell**: Via `workflow_dispatch`
- **Schritte**: Image Mirroring → Deployment

### Image Registry

**Wichtig**: Alle Images müssen über Azure Container Registry (ACR) bereitgestellt werden.

```yaml
image:
  registry: <your-acr-registry>.azurecr.io
  repository: <your-image>
  tag: "latest"
```

### Helm Chart-Struktur

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
│               ├── cicd-binding.yaml      # CI/CD RBAC
│               └── storage-access.yaml    # Storage RBAC (optional)
└── values/
    └── production.yaml
```

### Labels und Annotations

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

---

## Checkliste für neue Projekte

- [ ] Namespace erstellt
- [ ] **Default ServiceAccount geprüft** - reicht er für die App aus?
- [ ] **CI/CD ServiceAccount erstellt** (`<project>-deploy`) - für Deployments
- [ ] **Runtime ServiceAccount erstellt** (`<project>-app`) - **NUR wenn Rechte benötigt werden**
- [ ] **CI/CD RBAC konfiguriert** (`ClusterRoleBinding` an `cicd-deploy-role`)
- [ ] **Runtime RBAC konfiguriert** (`Role` + `RoleBinding`) - **NUR wenn Rechte benötigt werden**
- [ ] **Storage RBAC konfiguriert** (nur wenn Storage-ConfigMap-Zugriff benötigt)
- [ ] Deployment verwendet korrekten ServiceAccount:
  - `default` (Standard, keine Rechte) ODER
  - `<project>-app` (nur wenn Rechte benötigt werden)
- [ ] Helm Chart erstellt (falls nicht vorhanden)
- [ ] Images über ACR bereitgestellt
- [ ] Labels standardisiert
- [ ] CI/CD Pipeline konfiguriert
- [ ] Dokumentation erstellt

---

## Troubleshooting

### PVC bleibt im Status "Pending"

1. Prüfe, ob StorageClass existiert:
   ```bash
   kubectl get storageclass longhorn
   ```

2. Prüfe, ob RBAC korrekt konfiguriert ist:
   ```bash
   kubectl get rolebinding longhorn-storage-reader -n <your-namespace>
   ```

3. Prüfe Longhorn Pods:
   ```bash
   kubectl get pods -n longhorn-system
   kubectl logs -n longhorn-system -l app=longhorn-manager
   ```

### ImagePullBackOff

1. Prüfe, ob Image in ACR vorhanden ist
2. Prüfe ServiceAccount ImagePullSecrets:
   ```bash
   kubectl get serviceaccount <sa-name> -n <namespace> -o yaml
   ```

### RBAC-Probleme

1. Prüfe ClusterRole:
   ```bash
   kubectl get clusterrole cicd-deploy-role
   kubectl get clusterrole longhorn-storage-reader
   ```

2. Prüfe ClusterRoleBinding:
   ```bash
   kubectl get clusterrolebinding <project>-cicd-deploy-binding
   ```

3. Teste Zugriff:
   ```bash
   kubectl auth can-i create namespaces --as=system:serviceaccount:<namespace>:<serviceaccount>
   ```

---

## Sicherheitsbest Practices

### ServiceAccount-Strategie

1. **Default zuerst verwenden**:
   ```yaml
   # ✅ RICHTIG: Deployment verwendet default (keine Rechte)
   spec:
     template:
       spec:
         # Kein serviceAccountName = verwendet default
         containers: [...]
   ```

2. **Trennung strikt einhalten**:
   ```yaml
   # ✅ RICHTIG: Deployment verwendet Runtime ServiceAccount ODER default
   spec:
     serviceAccountName: my-project-app  # ODER weglassen für default
   
   # ❌ FALSCH: Deployment verwendet CI/CD ServiceAccount
   spec:
     serviceAccountName: my-project-deploy  # ← NIEMALS!
   ```

3. **CI/CD RBAC nur für CI/CD**:
   - ClusterRoleBinding nur für `<project>-deploy` ServiceAccount
   - Niemals für Runtime-Pods verwenden

4. **Runtime RBAC minimieren**:
   - **Default zuerst**: Verwende `default` ServiceAccount wenn möglich
   - Nur Lesen wo möglich (`get`, `list` statt `create`, `delete`)
   - Keine RBAC-Verwaltung für Runtime-Pods
   - Keine eigenen ClusterRoles - verwende zentrale vom Infrastructure Repo

### Risikobewertung

| Aspekt | Default ServiceAccount | CI/CD ServiceAccount | Runtime ServiceAccount |
|--------|----------------------|---------------------|------------------------|
| **Rechte** | Keine (sicherste Option) | Hoch (cluster-weit) | Minimal (namespace-scoped) |
| **Lebensdauer** | Lang (dauerhaft laufend) | Kurz (nur während Deployment) | Lang (dauerhaft laufend) |
| **Risiko bei Kompromittierung** | Sehr niedrig | Mittel | Mittel-Hoch |
| **Verwendung** | Laufende Pods (Standard) | GitHub Actions / CI/CD | Laufende Pods (nur wenn Rechte benötigt) |
| **Empfohlen** | ✅ **Erste Wahl** | ✅ Für CI/CD OK | ⚠️ Nur wenn Rechte benötigt |

---

## Weitere Ressourcen

- [Kubernetes RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Helm Documentation](https://helm.sh/docs/)
- [Longhorn Documentation](https://longhorn.io/docs/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [Prometheus Stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)

---

## Support

Bei Fragen oder Problemen:
1. Prüfe diese Dokumentation
2. Prüfe Cluster-Logs
3. Kontaktiere das Infrastructure-Team
