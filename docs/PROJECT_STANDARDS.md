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

### 2. ServiceAccounts

**Grundprinzip**: Verwende immer zuerst den **`default` ServiceAccount** (keine Cluster-Rechte). Nur wenn spezifische Rechte benötigt werden, erstelle eigene ServiceAccounts.

#### 2.0 Default ServiceAccount (Standard)

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

**Verwende `default`, wenn:**
- App braucht keine Kubernetes API-Zugriffe
- App braucht keine ConfigMaps/Secrets aus anderen Namespaces
- App braucht keine RBAC-Rechte

#### 2.1 Eigene ServiceAccounts (nur bei Bedarf)

**Erstelle eigene ServiceAccounts nur wenn:**
- App braucht spezifische RBAC-Rechte (z.B. Lesen von ConfigMaps)
- App braucht ImagePullSecrets
- App braucht Zugriff auf cluster-weite Ressourcen

**Für Cluster-Rechte**: Konsultiere das **Infrastructure Repo** - es stellt zentrale ClusterRoles bereit, die Projekte verwenden können.

#### 2.2 CI/CD ServiceAccount (für Deployments)

Dieser ServiceAccount wird **nur von der CI/CD-Pipeline** verwendet und hat hohe Rechte, um Ressourcen zu erstellen/löschen:

#### 2.1 CI/CD ServiceAccount (für Deployments)

Dieser ServiceAccount wird **nur von der CI/CD-Pipeline** verwendet und hat hohe Rechte, um Ressourcen zu erstellen/löschen:

```yaml
# k8s/serviceaccount-cicd.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: <project>-deploy
  namespace: <project-name>
  labels:
    app.kubernetes.io/name: <project>
    app.kubernetes.io/component: cicd
    app.kubernetes.io/managed-by: helm
```

**Sicherheitshinweise:**
- ⚠️ **NUR für CI/CD verwenden** - niemals für laufende Pods!
- ⚠️ Wird nur während Deployments aktiv verwendet
- ⚠️ Hat cluster-weite Rechte (via ClusterRoleBinding)

#### 2.3 Runtime ServiceAccount (nur wenn Rechte benötigt werden)

**WICHTIG**: Erstelle diesen ServiceAccount **nur**, wenn deine App spezifische Rechte benötigt. Für die meisten Apps reicht der `default` ServiceAccount!

**Erstelle einen Runtime ServiceAccount nur wenn:**
- App braucht Lesen von ConfigMaps/Secrets (über `get` hinaus)
- App braucht ImagePullSecrets
- App braucht Zugriff auf Storage-ConfigMaps (z.B. `local-path-config`)

```yaml
# k8s/serviceaccount-runtime.yaml
# NUR erstellen wenn wirklich benötigt!
apiVersion: v1
kind: ServiceAccount
metadata:
  name: <project>-app
  namespace: <project-name>
  labels:
    app.kubernetes.io/name: <project>
    app.kubernetes.io/component: runtime
    app.kubernetes.io/managed-by: helm
```

**Sicherheitshinweise:**
- ✅ **Nur für laufende Pods** verwenden
- ✅ Namespace-scoped Rechte (keine ClusterRoleBinding)
- ✅ Nur die Rechte, die die App tatsächlich braucht
- ⚠️ **Nicht erstellen**, wenn `default` ausreicht!

### 3. RBAC und Cluster-Rechte

#### 3.1 Grundprinzip: Default zuerst, Cluster-Rechte über Infrastructure Repo

**Entscheidungsbaum:**

```
Braucht deine App Kubernetes API-Zugriffe?
├─ NEIN → Verwende default ServiceAccount (keine RBAC nötig)
└─ JA → Braucht sie Cluster-weite Rechte?
    ├─ NEIN → Erstelle namespace-scoped Role + RoleBinding
    └─ JA → Konsultiere Infrastructure Repo für zentrale ClusterRoles
```

**Wichtig**: 
- ✅ **Default ServiceAccount** ist die erste Wahl (keine Cluster-Rechte)
- ✅ Für **Cluster-Rechte**: Das **Infrastructure Repo** stellt zentrale ClusterRoles bereit
- ❌ **Keine eigenen ClusterRoles** erstellen - verwende die zentralen!

#### 3.2 CI/CD RBAC (Zentrale ClusterRole)

**Wichtig**: Der Cluster stellt eine zentrale `cicd-deploy-role` bereit, die alle notwendigen Rechte für CI/CD-Deployments enthält. Projekte müssen **keine eigenen ClusterRoles** erstellen, sondern binden ihren **CI/CD ServiceAccount** an diese zentrale Role.

**⚠️ KRITISCH**: Diese Role hat **hohe Rechte** und sollte **NUR für CI/CD-Deployments** verwendet werden, **NICHT für laufende Pods**!

**Für Cluster-Rechte**: Wenn deine App cluster-weite Rechte braucht, konsultiere das **Infrastructure Repo**. Es stellt zentrale ClusterRoles bereit (z.B. `local-path-config-reader`), die Projekte verwenden können.

#### Schritt 1: ClusterRoleBinding erstellen

Erstelle ein `ClusterRoleBinding` in deinem Projekt, das deinen ServiceAccount an die zentrale `cicd-deploy-role` bindet:

```yaml
# k8s/rbac/cicd-binding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: <project>-cicd-deploy-binding
  labels:
    app.kubernetes.io/name: <project>
    app.kubernetes.io/component: cicd-rbac
    app.kubernetes.io/managed-by: helm
roleRef:
  kind: ClusterRole
  name: cicd-deploy-role  # Zentrale ClusterRole (wird vom Infrastructure Repo bereitgestellt)
  apiGroup: rbac.authorization.k8s.io
subjects:
  - kind: ServiceAccount
    name: <project>-deploy  # ← CI/CD ServiceAccount (NICHT Runtime!)
    namespace: <project-namespace>
```

**⚠️ Wichtig**: Binde hier **NUR** den CI/CD ServiceAccount (`<project>-deploy`), **NICHT** den Runtime ServiceAccount!

#### Was die `cicd-deploy-role` enthält

Die zentrale `cicd-deploy-role` gewährt folgende Rechte:

- ✅ **RBAC Management**: Erstellen/Verwalten von Roles und RoleBindings
- ✅ **Storage Classes**: Lesen/Verwalten von StorageClasses
- ✅ **Namespaces**: Erstellen/Lesen von Namespaces
- ✅ **Core Resources**: ConfigMaps, Secrets, Services, Pods, Endpoints
- ✅ **Persistent Volume Claims**: Vollständige PVC-Verwaltung (CRITICAL für PVC-basierte Deployments)
- ✅ **Apps Resources**: Deployments, StatefulSets, DaemonSets
- ✅ **Ingress Resources**: Ingresses und IngressClasses
- ✅ **Service Accounts**: Erstellen/Verwalten von ServiceAccounts
- ✅ **Nodes**: Lesen von Node-Informationen (für Debugging)
- ✅ **Metrics**: Lesen von Metriken (für Monitoring)

**Vorteile der zentralen Role:**
- ✅ Konsistente Rechte für alle Projekte
- ✅ Zentrale Verwaltung und Updates
- ✅ Keine Duplikation von RBAC-Konfigurationen
- ✅ Einfacheres Troubleshooting

**Sicherheitshinweise:**
- ⚠️ Diese Role hat **cluster-weite Rechte** (ClusterRoleBinding)
- ⚠️ Projekte können Ressourcen in **allen Namespaces** sehen/manipulieren
- ⚠️ **NUR für CI/CD verwenden** - niemals für Runtime-Pods!
- ✅ CI/CD-Systeme sind vertrauenswürdig (GitHub Actions mit Secrets)
- ✅ Runtime-Pods verwenden separate ServiceAccounts mit minimalen Rechten

#### Helm Template-Beispiel

Für Helm Charts kannst du die RBAC-Binding als Template erstellen:

```yaml
# charts/<your-app>/templates/cicd-binding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: {{ include "<your-app>.fullname" . }}-cicd-deploy
  labels:
    {{- include "<your-app>.labels" . | nindent 4 }}
    app.kubernetes.io/component: cicd-rbac
roleRef:
  kind: ClusterRole
  name: cicd-deploy-role
  apiGroup: rbac.authorization.k8s.io
subjects:
  - kind: ServiceAccount
    name: {{ include "<your-app>.serviceAccountName" . }}
    namespace: {{ .Release.Namespace }}
```

### 4. Runtime RBAC (nur wenn Rechte benötigt werden)

**Wichtig**: Die meisten Apps brauchen **keine RBAC** und können den `default` ServiceAccount verwenden. Erstelle RBAC **nur**, wenn deine App wirklich Rechte benötigt.

**Erstelle Runtime RBAC nur wenn:**
- App braucht Lesen von ConfigMaps/Secrets (über `get` hinaus)
- App braucht Zugriff auf Storage-ConfigMaps
- App braucht andere namespace-scoped Rechte

**Für Cluster-Rechte**: Konsultiere das **Infrastructure Repo** - es stellt zentrale ClusterRoles bereit.

#### Beispiel: Namespace-scoped Role (nur wenn benötigt)

```yaml
# k8s/rbac/runtime-role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: <project>-app-role
  namespace: <project-namespace>
  labels:
    app.kubernetes.io/name: <project>
    app.kubernetes.io/component: runtime-rbac
    app.kubernetes.io/managed-by: helm
rules:
  # Beispiel: Nur was die App wirklich braucht
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]  # ← Nur Lesen, kein Erstellen/Löschen!
  # Weitere Rechte je nach Anforderung der App
```

```yaml
# k8s/rbac/runtime-binding.yaml
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
    name: <project>-app  # ← Runtime ServiceAccount
    namespace: <project-namespace>
```

**Sicherheitsprinzipien für Runtime RBAC:**
- ✅ **Default zuerst**: Verwende `default` ServiceAccount wenn möglich
- ✅ **Least Privilege**: Nur die Rechte, die die App wirklich braucht
- ✅ **Namespace-scoped**: Keine ClusterRoleBinding für Runtime (außer zentrale ClusterRoles vom Infrastructure Repo)
- ✅ **Read-only wo möglich**: ConfigMaps/Secrets nur lesen, nicht schreiben
- ✅ **Keine RBAC-Verwaltung**: Runtime-Pods können keine Roles/RoleBindings erstellen
- ✅ **Zentrale ClusterRoles**: Für Cluster-Rechte immer das Infrastructure Repo konsultieren

### 5. Storage-Zugriff (Local Path Provisioner)

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

### 6. Helm Chart-Struktur

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
│               ├── cicd-binding.yaml      # CI/CD RBAC (ClusterRoleBinding)
│               └── storage-access.yaml    # Storage RBAC (RoleBinding)
└── values/
    └── production.yaml
```

### 7. Image-Registry

**Wichtig**: Alle Images müssen über Azure Container Registry (ACR) bereitgestellt werden.

```yaml
# In values.yaml
image:
  registry: <your-acr-registry>.azurecr.io
  repository: <your-image>
  tag: "latest"
```

### 8. Labels und Annotations

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
- [ ] **Default ServiceAccount geprüft** - reicht er für die App aus?
- [ ] **CI/CD ServiceAccount erstellt** (`<project>-deploy`) - für Deployments
- [ ] **Runtime ServiceAccount erstellt** (`<project>-app`) - **NUR wenn Rechte benötigt werden**
- [ ] **CI/CD RBAC konfiguriert** (`ClusterRoleBinding` an `cicd-deploy-role`) - nur für CI/CD!
- [ ] **Runtime RBAC konfiguriert** (`Role` + `RoleBinding`) - **NUR wenn Rechte benötigt werden**
- [ ] **Cluster-Rechte**: Infrastructure Repo konsultiert für zentrale ClusterRoles (z.B. `local-path-config-reader`)
- [ ] Deployment verwendet korrekten ServiceAccount:
  - `default` (Standard, keine Rechte) ODER
  - `<project>-app` (nur wenn Rechte benötigt werden)
- [ ] Helm Chart erstellt (falls nicht vorhanden)
- [ ] Images über ACR bereitgestellt
- [ ] Labels standardisiert
- [ ] CI/CD Pipeline konfiguriert
- [ ] Dokumentation erstellt

## Beispiel: Vollständiges Projekt-Setup

### 1. Namespace und ServiceAccounts

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-project
---
# CI/CD ServiceAccount (für Deployments) - IMMER benötigt
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-project-deploy
  namespace: my-project
  labels:
    app.kubernetes.io/name: my-project
    app.kubernetes.io/component: cicd
---
# Runtime ServiceAccount (NUR wenn Rechte benötigt werden)
# Für die meisten Apps reicht der default ServiceAccount!
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-project-app
  namespace: my-project
  labels:
    app.kubernetes.io/name: my-project
    app.kubernetes.io/component: runtime
```

**Hinweis**: Der `default` ServiceAccount wird automatisch erstellt - du musst ihn nicht explizit definieren. Verwende ihn einfach, indem du `serviceAccountName` im Deployment weglässt.

### 2. CI/CD RBAC

```yaml
# k8s/rbac/cicd-binding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: my-project-cicd-deploy-binding
  labels:
    app.kubernetes.io/name: my-project
    app.kubernetes.io/component: cicd-rbac
    app.kubernetes.io/managed-by: helm
roleRef:
  kind: ClusterRole
  name: cicd-deploy-role  # Zentrale ClusterRole
  apiGroup: rbac.authorization.k8s.io
subjects:
  - kind: ServiceAccount
    name: my-project-deploy
    namespace: my-project
```

### 3. Runtime RBAC (nur wenn benötigt)

**Wichtig**: Erstelle diese RBAC-Konfiguration **nur**, wenn deine App wirklich Rechte benötigt. Für die meisten Apps reicht der `default` ServiceAccount ohne RBAC.

**Beispiel**: App braucht Lesen von Storage-ConfigMap (konsultiere Infrastructure Repo für zentrale ClusterRole):

```yaml
# k8s/rbac/storage-access.yaml
# Verwendet zentrale ClusterRole vom Infrastructure Repo
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: local-path-config-reader
  namespace: my-project
roleRef:
  kind: ClusterRole
  name: local-path-config-reader  # ← Zentrale ClusterRole vom Infrastructure Repo
  apiGroup: rbac.authorization.k8s.io
subjects:
  - kind: ServiceAccount
    name: my-project-app  # ODER default, wenn kein eigener ServiceAccount
    namespace: my-project
```

**Für eigene namespace-scoped Rechte** (nur wenn wirklich benötigt):

```yaml
# k8s/rbac/runtime-role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: my-project-app-role
  namespace: my-project
rules:
  # Beispiel: App braucht nur Lesen von ConfigMaps/Secrets
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]
---
# k8s/rbac/runtime-binding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: my-project-app-binding
  namespace: my-project
roleRef:
  kind: Role
  name: my-project-app-role
  apiGroup: rbac.authorization.k8s.io
subjects:
  - kind: ServiceAccount
    name: my-project-app
    namespace: my-project
```

### 4. Storage-RBAC

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

### 5. PVC-Beispiel

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

### 6. Deployment mit PVC

**Beispiel 1: Mit default ServiceAccount (Standard, keine Rechte)**

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
      # Kein serviceAccountName = verwendet default (keine Cluster-Rechte)
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

**Beispiel 2: Mit eigenem Runtime ServiceAccount (nur wenn Rechte benötigt)**

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
      serviceAccountName: my-project-app  # ← NUR wenn Rechte benötigt werden!
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

**⚠️ Wichtig**: 
- ✅ **Standard**: Verwende `default` ServiceAccount (kein `serviceAccountName` nötig)
- ⚠️ **Nur bei Bedarf**: Verwende eigenen Runtime ServiceAccount (`my-project-app`)
- ❌ **NIEMALS**: Verwende CI/CD ServiceAccount (`my-project-deploy`) für laufende Pods!

## Sicherheit: ServiceAccount-Strategie

### Entscheidungsbaum für ServiceAccounts

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
    │   └─ Nur namespace-scoped Rechte
    │
    └─ JA → Konsultiere Infrastructure Repo
        └─ Verwende zentrale ClusterRoles (z.B. local-path-config-reader)
        └─ Erstelle ClusterRoleBinding ODER RoleBinding (je nach ClusterRole)
```

### Warum verschiedene ServiceAccounts?

**Default ServiceAccount** (Standard):
- ✅ **Keine Cluster-Rechte** - sicherste Option
- ✅ **Automatisch vorhanden** - keine Konfiguration nötig
- ✅ **Für die meisten Apps ausreichend** - keine Kubernetes API-Zugriffe
- ✅ **Empfohlene erste Wahl** - verwende immer zuerst

**CI/CD ServiceAccount** (`<project>-deploy`):
- ✅ **Hohe Rechte notwendig** - muss Ressourcen erstellen/löschen
- ✅ **Nur während Deployments aktiv** - nicht dauerhaft laufend
- ✅ **Vertrauenswürdiges System** - GitHub Actions mit Secrets
- ⚠️ **Cluster-weite Rechte** - kann Ressourcen in allen Namespaces sehen/manipulieren

**Runtime ServiceAccount** (`<project>-app` - nur wenn benötigt):
- ✅ **Minimale Rechte** - nur was die App wirklich braucht
- ✅ **Namespace-scoped** - kann nur eigene Namespace-Ressourcen sehen
- ✅ **Dauerhaft laufend** - Pods laufen kontinuierlich
- ✅ **Least Privilege** - minimiert Angriffsfläche bei Kompromittierung
- ⚠️ **Nur erstellen wenn wirklich benötigt** - default zuerst verwenden!

### Sicherheitsbest Practices

1. **Default zuerst verwenden**:
   ```yaml
   # ✅ RICHTIG: Deployment verwendet default (keine Rechte)
   spec:
     template:
       spec:
         # Kein serviceAccountName = verwendet default
         containers: [...]
   
   # ⚠️ NUR wenn Rechte benötigt werden: Eigener ServiceAccount
   spec:
     template:
       spec:
         serviceAccountName: my-project-app  # ← NUR wenn wirklich benötigt
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

5. **Cluster-Rechte über Infrastructure Repo**:
   - Für Cluster-Rechte immer das Infrastructure Repo konsultieren
   - Verwende zentrale ClusterRoles (z.B. `local-path-config-reader`)
   - Erstelle keine eigenen ClusterRoles

4. **Monitoring**:
   - Überwache, welche ServiceAccounts von Pods verwendet werden
   - Alarme bei Verwendung von CI/CD ServiceAccounts in Deployments

### Risikobewertung

| Aspekt | Default ServiceAccount | CI/CD ServiceAccount | Runtime ServiceAccount |
|--------|----------------------|---------------------|------------------------|
| **Rechte** | Keine (sicherste Option) | Hoch (cluster-weit) | Minimal (namespace-scoped) |
| **Lebensdauer** | Lang (dauerhaft laufend) | Kurz (nur während Deployment) | Lang (dauerhaft laufend) |
| **Risiko bei Kompromittierung** | Sehr niedrig (keine Rechte) | Mittel (nur während Deployment) | Mittel-Hoch (dauerhaft aktiv) |
| **Verwendung** | Laufende Pods (Standard) | GitHub Actions / CI/CD | Laufende Pods (nur wenn Rechte benötigt) |
| **Empfohlen** | ✅ **Erste Wahl** | ✅ Für CI/CD OK | ⚠️ Nur wenn Rechte benötigt |

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

