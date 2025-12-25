#!/usr/bin/env python3
"""
Generate image mapping for monitoring component (Prometheus/Grafana stack).

Outputs:
  - image-map.txt (source|target|tag format)
  - monitoring/values.acr.yaml (registry rewritten to ACR)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[2]
MONITORING_DIR = ROOT / "monitoring"
VALUES_FILE = MONITORING_DIR / "values.yaml"
OUTPUT_IMAGE_MAP = MONITORING_DIR / "image-map.txt"
OUTPUT_VALUES_ACR = MONITORING_DIR / "values.acr.yaml"


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


def rewrite_values(acr_registry: str, data: Dict) -> None:
    def normalize_repo(repository: str) -> str:
        # Remove registry prefix if present, return only path
        parts = repository.split("/")
        if parts and (parts[0] in {"docker.io", "quay.io"} or "." in parts[0] or ":" in parts[0]):
            parts = parts[1:]
        return "/".join(parts)

    def patch(node):
        if isinstance(node, dict):
            # If repository is present, normalize it and set registry
            if "repository" in node and node["repository"]:
                # Normalize repository to remove registry prefix
                node["repository"] = normalize_repo(str(node["repository"]).strip())
                # Always set registry to ACR
                node["registry"] = acr_registry
            # Recursively process all values
            for value in node.values():
                patch(value)
        elif isinstance(node, list):
            for item in node:
                patch(item)

    patch(data)
    OUTPUT_VALUES_ACR.write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_VALUES_ACR}")


def main() -> None:
    acr_registry = os.environ.get("ACR_REGISTRY")
    if not acr_registry:
        raise RuntimeError(
            "ACR_REGISTRY environment variable is required (e.g. myregistry.azurecr.io). "
            "Set it in the workflow environment or export it locally before running this script."
        )

    values = load_yaml(VALUES_FILE)

    # Collect images from values file
    image_entries = list(collect_images(values))

    # Write image-map.txt
    write_image_map(image_entries)
    
    # Generate values.acr.yaml
    rewrite_values(acr_registry, values)
    
    print(f"✅ Generated {OUTPUT_IMAGE_MAP} and {OUTPUT_VALUES_ACR}")
    print(f"📦 Found {len(set(image_entries))} unique images in values file")


if __name__ == "__main__":
    main()

