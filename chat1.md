# VMware Migration & Proxmox Setup Guide

## VMware Migration für 10-100 VMs

### Warum Migration sinnvoll ist

**Für 10-100 VMs ist VMware oft überdimensioniert:**
- Hohe Lizenzkosten (vSphere, vCenter, vSAN, Support)
- Broadcoms neue Lizenzpolitik trifft kleine Umgebungen hart
- 80% der Enterprise-Features werden nicht genutzt (NSX, DRS, Tanzu)
- Für Mittelstand zu teuer, zu komplex, zu Enterprise-lastig

**Migration ist technisch machbar:**
- 1-2 Wochen Aufwand für 10 VMs
- Tools: OVA/OVF Export, V2V Converter, Proxmox Importer
- Überschaubare Downtime, gut planbar

### Alternativen

**⭐ Proxmox VE (Empfehlung für 10-200 VMs)**
- Kostenlos (Open Source, AGPLv3)
- Optionaler Support via Subscription
- HA-Cluster, Live Migration, Ceph-Storage, Backup integriert
- API-fähig, Terraform-Provider vorhanden
- Migration von VMware → Proxmox einfach

**⭐ Hyper-V**
- Günstig, stabil, gut für Windows-Umgebungen
- Weniger flexibel als Proxmox

**⭐ MAAS + KVM**
- Moderner Ansatz, perfekt für Kubernetes
- Mehr Know-how nötig

**❌ OpenStack**
- Nur sinnvoll ab 200-300 VMs
- Für <100 VMs: zu komplex, zu teuer, zu personalintensiv

**❌ Public Cloud (Azure/AWS)**
- Für 10-100 VMs, die 24/7 laufen, oft teurer als On-Prem

---

## Proxmox Funktionsweise & Cloud-Readiness

### Technische Grundlagen

**Proxmox VE kombiniert:**
- **KVM**: Vollwertige VMs (Windows, Linux)
- **LXC**: Leichtgewichtige Container
- **Cluster-Funktionen**: Live Migration, HA, Shared Storage (Ceph, NFS, iSCSI), ZFS-Pools, Replikation
- **Web-GUI + REST-API**: Automatisierbar, skriptbar

### Cloud-Readiness Level

**Level 1: Virtualisierung (30% Cloud-Ready)**
- HA, Live Migration, API, Cluster, Storage-Cluster, Backups, Snapshots
- Vergleich: VMware ohne Lizenzstress

**Level 2: Private Cloud Light (60% Cloud-Ready)**
- Proxmox + Terraform + Ansible + Cloud-Init
- Automatisierte VM-Provisionierung, Infrastructure-as-Code, Self-Service-Workflows
- Vergleich: Azure VM-Deployment, aber On-Prem

**Level 3: Private Cloud Heavy (90% Cloud-Ready)**
- Proxmox + Ceph + MAAS + Kubernetes + GitOps + Monitoring
- API-driven Infrastructure, Self-Healing Workloads, Immutable Deployments
- Vergleich: OpenStack-Light oder Mini-Google-Cloud

**Was fehlt für "echte Cloud":**
- Multi-Tenant-Cloud-Portal, Self-Service-Portal, Billing-System, Identity-Federation
- Für 10-100 VMs meist nicht nötig

---

## Architektur für 2 Optiplex Nodes

### Empfohlene Architektur: Proxmox + Terraform + Kubernetes + GitOps

**Aufbau:**
- Beide Optiplex → Proxmox Cluster
- Shared Storage → ZFS Replikation (einfach, stabil) oder Ceph-Light (mit QDevice)
- Kubernetes → als VMs auf Proxmox
- Terraform → Infrastructure-as-Code für VMs, Netzwerke, Storage
- GitOps (ArgoCD/Flux) → Deployment-Engine

**Vorteile:**
- Cloud-Ready: 80-90% der Architektur einer echten Cloud
- Realistisch für Mittelstand
- Maximaler Lernwert
- Reproduzierbare Umgebungen
- Kubernetes beliebig oft neu aufsetzbar

**Alternativen:**
- **MAAS + Kubernetes**: Bare-Metal-Cloud-Feeling, höhere Komplexität
- **Harvester (Rancher)**: Kubernetes als Hypervisor, futuristisch, 95% Cloud-Ready

---

## GitOps vs. GitHub Actions

### GitOps ist NICHT GitHub Actions

**GitOps:**
- Pull-basiertes Deployment-Modell
- Läuft im Cluster (ArgoCD/Flux)
- Git ist Single Source of Truth
- Kubernetes synchronisiert automatisch mit Git-Zustand
- Rollbacks = Git revert, Audit = Git History

**GitHub Actions:**
- CI/CD-System (Build, Test, Lint, Security Scans)
- Push-basiert, führt Dinge aus wenn du pushst
- Baut Images, updated YAML-Manifeste

**Typischer Flow:**
```
Code → Git Push → GitHub Actions → Build Image → Push to Registry → Update Git Manifests → ArgoCD/Flux → Kubernetes
```

**GitHub Actions macht:** Build, Test, Image Push, YAML Update  
**GitOps macht:** Deployment, Sync, Drift Correction, Rollbacks, Health Monitoring

**Vorteile von GitOps:**
- 100% Reproduzierbarkeit
- Zero-Touch Deployments
- Versionierte Infrastruktur
- Automatische Rollbacks
- Self-Healing Deployments
- Cluster-Drift-Erkennung

---

## Proxmox Setup-Roadmap (6 Phasen)

### Phase 1: Hardware vorbereiten (Tag 0)
- BIOS aktualisieren
- Virtualisierung aktivieren (VT-x/VT-d)
- Boot-Reihenfolge auf USB setzen
- Netzwerk konfigurieren (statische IPs)

### Phase 2: Proxmox installieren (Tag 1)
- Proxmox ISO auf USB schreiben
- Auf beiden Nodes installieren
- **ZFS als Root-Filesystem wählen** (Snapshots, Replikation, Checksumming)
- Netzwerk konfigurieren (statische IPs, gleiche Subnetze)

### Phase 3: Proxmox Cluster bauen (Tag 1-2)
- Node 1 → Cluster erstellen
- Node 2 → Cluster beitreten
- **Quorum sichern** (QDevice oder NAS/VM als dritter "Stimme")
- Ermöglicht: Live Migration, HA, zentrale Verwaltung, Terraform-Provisioning

### Phase 4: Storage einrichten (Tag 2)
**Option A: ZFS-Replikation (empfohlen)**
- Auf beiden Nodes ZFS-Pools anlegen
- Replikation zwischen Nodes aktivieren
- Storage als "shared" markieren (für HA)

**Option B: Ceph-Light**
- Nur wenn du Ceph lernen willst
- Mit 2 Nodes + QDevice technisch möglich, aber nicht ideal

### Phase 5: Terraform-Integration (Tag 3)
- Terraform installieren
- Proxmox Terraform Provider konfigurieren
- API-Token in Proxmox erstellen
- Cloud-Init Templates anlegen (Ubuntu, Debian)

**Ergebnis:** Mit `terraform apply` kannst du:
- Master-VMs erzeugen
- Worker-VMs erzeugen
- Netzwerke anlegen
- Storage zuweisen
- Cloud-Init konfigurieren

### Phase 6: Kubernetes + GitOps (Tag 4-5)
**1. Kubernetes installieren**
- **k3s**: Leicht, perfekt für Demo
- **kubeadm**: Klassisch, realistisch
- **Talos Linux**: Ultra-modern, GitOps-native

**2. GitOps installieren**
- ArgoCD (visuell, Enterprise-ready) oder Flux (minimalistisch)
- Git-Repo für Deployments anlegen
- Cluster mit Git verbinden

**3. CI/CD anbinden**
- GitHub Actions: Build, Test, Image Push, YAML Update
- GitOps: Deployment, Sync, Rollbacks

---

## Endzustand: Mini-Cloud

**Infrastruktur:**
- Proxmox Cluster
- ZFS Replikation
- Terraform IaC
- API-driven Provisioning

**Kubernetes:**
- Multi-Node Cluster
- GitOps Deployment
- CI/CD Integration
- Self-Healing Workloads

**Cloud-Ready:**
- 80-90% der Architektur einer echten Cloud
- Auf 2 Optiplex-Kisten
- Ohne Kosten
- Ohne Overkill

**Vergleichbar mit:**
- Azure AKS
- AWS EKS
- Google GKE
- On-Prem Rancher
- OpenShift (light)
