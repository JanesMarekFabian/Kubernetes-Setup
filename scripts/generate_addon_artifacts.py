#!/usr/bin/env python3
"""
Generate supporting artifacts for mirroring base add-on images.

Outputs:
  - image-map.txt (source|target|tag format)
  - infra/addons/values/observability.acr.yaml (registry rewritten to ACR)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.request import urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
VALUES_DIR = ROOT / "infra" / "addons" / "values"
OBSERVABILITY_VALUES = VALUES_DIR / "observability.yaml"
INGRESS_VALUES = VALUES_DIR / "ingress-nginx.yaml"
OUTPUT_IMAGE_MAP = ROOT / "image-map.txt"
OUTPUT_OBSERVABILITY_ACR = VALUES_DIR / "observability.acr.yaml"


def get_latest_metrics_server_version() -> str:
    """Fetch the latest metrics-server version from GitHub releases."""
    try:
        with urlopen("https://api.github.com/repos/kubernetes-sigs/metrics-server/releases/latest", timeout=10) as response:
            data = json.loads(response.read())
            version = data.get("tag_name", "v0.8.0")
            print(f"📦 Latest metrics-server version: {version}")
            return version
    except Exception as e:
        print(f"⚠️ Failed to fetch latest metrics-server version: {e}, using fallback v0.8.0")
        return "v0.8.0"


def get_static_images() -> List[Tuple[str, str]]:
    """Get static images with dynamically fetched versions."""
    metrics_version = get_latest_metrics_server_version()
    return [
        ("registry.k8s.io/metrics-server/metrics-server", metrics_version),
        ("docker.io/rancher/local-path-provisioner", "v0.0.26"),
    ]


def load_yaml(path: Path) -> Dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def collect_images(data: Dict) -> Iterable[Tuple[str, str]]:
    def walk(node):
        if isinstance(node, dict):
            if "repository" in node and "tag" in node:
                repo = str(node["repository"]).strip()
                tag = str(node["tag"]).strip()
                if repo and tag:
                    yield (repo, tag)
            for value in node.values():
                yield from walk(value)
        elif isinstance(node, list):
            for item in node:
                yield from walk(item)

    yield from walk(data)


def normalize_target(repository: str) -> str:
    parts = repository.split("/")
    if not parts:
        return repository
    if parts[0] in {"docker.io", "quay.io"} or "." in parts[0] or ":" in parts[0]:
        parts = parts[1:]
    return "/".join(parts)


def write_image_map(image_entries: Iterable[Tuple[str, str]]) -> None:
    lines = []
    for repo, tag in sorted(set(image_entries)):
        target_repo = normalize_target(repo)
        if target_repo:
            lines.append(f"{repo}|{target_repo}|{tag}")
    OUTPUT_IMAGE_MAP.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"Wrote {OUTPUT_IMAGE_MAP} with {len(lines)} entries")


def rewrite_observability(acr_registry: str, data: Dict) -> None:
    def normalize_repo(repository: str) -> str:
        parts = repository.split("/")
        if parts and (parts[0] in {"docker.io", "quay.io"} or "." in parts[0] or ":" in parts[0]):
            parts = parts[1:]
        return f"{acr_registry}/{'/'.join(parts)}"

    def patch(node):
        if isinstance(node, dict):
            if "repository" in node and node["repository"]:
                node["repository"] = normalize_repo(str(node["repository"]).strip())
            if "registry" in node:
                node["registry"] = ""
            for value in node.values():
                patch(value)
        elif isinstance(node, list):
            for item in node:
                patch(item)

    patch(data)
    OUTPUT_OBSERVABILITY_ACR.write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_OBSERVABILITY_ACR}")


def main() -> None:
    acr_registry = os.environ.get("ACR_REGISTRY")
    if not acr_registry:
        raise RuntimeError(
            "ACR_REGISTRY environment variable is required (e.g. myregistry.azurecr.io). "
            "Set it in the workflow environment or export it locally before running this script."
        )

    observability = load_yaml(OBSERVABILITY_VALUES)
    ingress = load_yaml(INGRESS_VALUES)

    image_entries = list(collect_images(observability)) + list(collect_images(ingress))
    image_entries.extend(get_static_images())

    write_image_map(image_entries)
    rewrite_observability(acr_registry, observability)


if __name__ == "__main__":
    main()

