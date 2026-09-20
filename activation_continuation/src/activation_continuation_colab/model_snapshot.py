"""Explicit retrieval and provenance verification for the pinned Qwen3 snapshot."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .artifacts import ArtifactRoots
from .config import ModelConfig


class ModelSnapshotError(RuntimeError):
    """The requested model snapshot cannot be retrieved or verified safely."""


@dataclass(frozen=True)
class ModelSnapshot:
    """Private snapshot location plus public-safe immutable identity."""

    local_path: Path
    model_id: str
    requested_revision: str
    resolved_revision: str
    metadata_file_sha256: Mapping[str, str]

    def public_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "requested_revision": self.requested_revision,
            "resolved_revision": self.resolved_revision,
            "metadata_file_sha256": dict(self.metadata_file_sha256),
            "local_snapshot_path_omitted": True,
        }


def retrieve_and_verify_pinned_model(
    model: ModelConfig,
    roots: ArtifactRoots,
) -> ModelSnapshot:
    """Download only the exact immutable revision into private Drive storage.

    Importing this module has no network side effects. This function first
    resolves the server's commit SHA and rejects movement away from the frozen
    SHA. It then uses that same SHA for `snapshot_download` and records hashes
    of lightweight metadata files. Model weights never enter the repository or
    public-safe report.
    """

    try:
        hub = importlib.import_module("huggingface_hub")
    except Exception as error:
        raise ModelSnapshotError(
            f"huggingface-hub import failed: {type(error).__name__}: {error}"
        ) from error
    try:
        info = hub.HfApi().model_info(model.repo_id, revision=model.revision)
        resolved_revision = getattr(info, "sha", None)
    except Exception as error:
        raise ModelSnapshotError(
            f"cannot resolve pinned model revision: {type(error).__name__}: {error}"
        ) from error
    if resolved_revision != model.revision:
        raise ModelSnapshotError(
            "model registry resolved a revision different from the frozen SHA; refusing download"
        )
    slug = model.repo_id.replace("/", "--")
    destination = roots.model_cache / slug / model.revision
    try:
        local_path = Path(
            hub.snapshot_download(
                repo_id=model.repo_id,
                revision=model.revision,
                local_dir=str(destination),
            )
        )
    except Exception as error:
        raise ModelSnapshotError(
            f"pinned model snapshot retrieval failed: {type(error).__name__}: {error}"
        ) from error
    if local_path.resolve() != destination.resolve():
        # The hub may return a cache path only when `local_dir` is not honored.
        # Do not let a model cache escape the declared private Drive root.
        raise ModelSnapshotError("snapshot retrieval did not use the requested private artifact directory")
    required = ("config.json", "tokenizer_config.json", "model.safetensors.index.json")
    missing = [name for name in required if not (local_path / name).is_file()]
    if missing:
        raise ModelSnapshotError(f"pinned snapshot is missing required metadata: {missing}")
    metadata_hashes = {
        name: hashlib.sha256((local_path / name).read_bytes()).hexdigest() for name in required
    }
    snapshot = ModelSnapshot(
        local_path=local_path,
        model_id=model.repo_id,
        requested_revision=model.revision,
        resolved_revision=resolved_revision,
        metadata_file_sha256=metadata_hashes,
    )
    _write_private_provenance(roots, snapshot)
    return snapshot


def _write_private_provenance(roots: ArtifactRoots, snapshot: ModelSnapshot) -> None:
    """Write immutable provenance without copying any model content."""

    destination = roots.provenance / f"model_snapshot_{snapshot.resolved_revision}.json"
    payload = {
        "schema_version": 1,
        "model": snapshot.public_dict(),
        "private_snapshot_path": str(snapshot.local_path),
    }
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != encoded:
            raise ModelSnapshotError("existing model provenance conflicts with the frozen snapshot")
        return
    with destination.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
