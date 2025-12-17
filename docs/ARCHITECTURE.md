# Cluster Architecture

Dieses Dokument beschreibt die Architektur des Kubernetes-Clusters und die Design-Entscheidungen.

## Überblick

Der Cluster verwendet ein **zentralisiertes Management-System** für gemeinsame Infrastruktur-Komponenten, während Projekte ihre eigenen Namespaces und RBAC haben.

## Architektur-Schichten

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
│ │ kube-system/                                        │ │
│ │   - local-path-provisioner                          │ │
│ │   - ConfigMap: local-path-config (via Helm)        │ │
│ │   - ClusterRole: local-path-config-reader          │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ monitoring/                                         │ │
│ │   - Prometheus, Grafana, Alertmanager               │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ingress-nginx/                                      │ │
│ │   - NGINX Ingress Controller                        │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                    ↓ (projects deploy here)
┌─────────────────────────────────────────────────────────┐
│ LAYER 3: PROJECT NAMESPACES                             │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ <project-namespace>/                              │ │
│ │   - App Components                                 │ │
│ │   - RoleBinding: local-path-config-reader         │ │
│ │   - PVCs (storageClassName: local-path)           │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Design-Prinzipien

### 1. Separation of Concerns

- **Infrastructure Repo**: Verwaltet Cluster-weite Ressourcen
- **Project Repos**: Verwalten nur ihre eigenen Ressourcen
- **RBAC**: Projekte erhalten minimale, spezifische Rechte

### 2. GitOps

- Alles ist in Git versioniert
- CI/CD automatisiert Deployments
- Keine manuellen `kubectl apply` ohne Git-Commit

### 3. Helm als Package Manager

- Infrastructure-Komponenten als Helm Charts
- Projekte können Helm Charts verwenden
- Versionierung und Rollback möglich

### 4. RBAC: Least Privilege

- ClusterRoles für gemeinsame Ressourcen
- RoleBindings pro Projekt
- ServiceAccounts mit minimalen Rechten

## Komponenten-Details

### Storage Management

**Problem**: Storage-Konfiguration muss zentral verwaltet werden, aber Projekte müssen darauf zugreifen können.

**Lösung**: 
- Helm Chart (`cluster-storage`) verwaltet ConfigMap zentral
- ClusterRole (`local-path-config-reader`) ermöglicht Projekten Lesezugriff
- Projekte erstellen RoleBinding in ihrem Namespace

**Vorteile**:
- Zentrale Verwaltung
- Projekte können ConfigMap lesen (für Debugging)
- Keine direkten Schreibrechte für Projekte

### Image Registry

**Problem**: Alle Images müssen über ACR bereitgestellt werden.

**Lösung**:
- Image-Mirroring zu ACR im CI/CD
- ServiceAccounts erhalten ImagePullSecrets
- Helm Post-Renderer stellt sicher, dass alle Images ACR verwenden

### Monitoring

**Problem**: Alle Projekte sollten observability haben.

**Lösung**:
- Zentraler Prometheus Stack
- Projekte können ServiceMonitors erstellen
- Grafana Dashboards können pro Projekt erstellt werden

## RBAC-Struktur

```
ClusterRole (zentral):
  - local-path-config-reader
    └─> ConfigMap: local-path-config (get, list, watch)

RoleBinding (pro Projekt):
  - Namespace: <project-namespace>
  - Subject: <project-serviceaccount>
  - RoleRef: ClusterRole local-path-config-reader
```

## Workflow

### Infrastructure Deployment

1. **Image Mirroring**: Alle Images zu ACR spiegeln
2. **Base Components**: Provisioner, Ingress, Monitoring deployen
3. **Storage Config**: Helm Chart deployen
4. **RBAC**: ClusterRoles erstellen

### Project Deployment

1. **Namespace**: Projekt erstellt Namespace
2. **ServiceAccount**: Projekt erstellt ServiceAccount
3. **RBAC**: Projekt erstellt RoleBinding für Storage-Zugriff
4. **Resources**: Projekt deployed App-Komponenten

## Erweiterungen

### Zukünftige Verbesserungen

- **Network Policies**: Namespace-Isolation
- **Resource Quotas**: Ressourcen-Limits pro Namespace
- **Operators**: Automatische Reconciliation für komplexe Workloads
- **GitOps Operator**: ArgoCD oder Flux für automatische Deployments

## Sicherheit

### Best Practices

- ✅ ServiceAccounts mit minimalen Rechten
- ✅ Secrets in Kubernetes Secrets (nicht in Git)
- ✅ Image Pull Secrets für ACR
- ✅ RBAC für alle Zugriffe
- ⚠️ Network Policies (geplant)
- ⚠️ Pod Security Standards (geplant)

## Troubleshooting

Siehe [PROJECT_STANDARDS.md](PROJECT_STANDARDS.md) für Troubleshooting-Guides.

