"""Drive-backed artifact layout and append-only trajectory checkpoint primitives.

The repository never writes large or private runtime output into its checkout.
This module accepts a user-supplied private root at execution time; it does not
embed a Drive path in repository code or reports.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .config import ArtifactConfig


class ArtifactIntegrityError(RuntimeError):
    """Private artifact evidence is incomplete, malformed, or conflicting."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def _safe_id(value: str, field: str) -> str:
    if not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{field} must be a safe identifier")
    return value


def _write_exclusive(path: Path, payload: bytes) -> None:
    """Persist bytes once. Existing artifacts are evidence, never replaceable."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("exclusive artifact write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _canonical_json(value)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("ledger append made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@dataclass(frozen=True)
class ArtifactRoots:
    """Private and public-safe folders under a caller-provided Drive root."""

    private_root: Path
    model_cache: Path
    qualification: Path
    private_study: Path
    public_safe: Path
    provenance: Path

    @classmethod
    def from_private_root(cls, private_root: Path, config: ArtifactConfig) -> "ArtifactRoots":
        if not private_root.is_absolute():
            raise ValueError("private artifact root must be absolute at execution time")
        root = private_root.resolve()
        return cls(
            private_root=root,
            model_cache=root / config.model_cache_dir,
            qualification=root / config.qualification_dir,
            private_study=root / config.private_study_dir,
            public_safe=root / config.public_safe_dir,
            provenance=root / config.provenance_dir,
        )

    def ensure(self) -> None:
        for path in (
            self.private_root,
            self.model_cache,
            self.qualification,
            self.private_study,
            self.public_safe,
            self.provenance,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def public_layout(self) -> dict[str, str]:
        """Directory labels only; never serialize private absolute paths."""

        return {
            "repository": "repository checkout (code/config/manifests only)",
            "model_cache": "private model cache",
            "qualification": "private synthetic qualification evidence",
            "private_study": "private benchmark trajectories and activations",
            "public_safe": "aggregate, path-free summaries only",
            "provenance": "private execution provenance",
        }


class ImmediateTrajectoryCheckpointStore:
    """Write each completed trajectory before the caller may move to the next.

    A completed file is created with exclusive creation and fsync before an
    append-only completion event is written. Any partial, malformed, or
    unindexed existing file is `interrupted_unknown`, never an excuse to
    regenerate the corresponding problem/seed.
    """

    schema_version = 1

    def __init__(self, private_study_root: Path) -> None:
        self.root = private_study_root / "trajectory_checkpoints"
        self.declarations_dir = self.root / "declarations"
        self.records_dir = self.root / "records"
        self.ledger_path = self.root / "completion_ledger.jsonl"
        # This in-memory capability is intentionally not recoverable after a
        # disconnect.  A fresh process sees a declaration without completion
        # as interrupted/unknown and is prohibited from replacing it.
        self._active_declarations: set[str] = set()

    @staticmethod
    def intent_id(problem_id: str, rollout_seed: int) -> str:
        _safe_id(problem_id, "problem_id")
        if type(rollout_seed) is not int:
            raise ValueError("rollout_seed must be an integer")
        return f"{problem_id}--seed-{rollout_seed}"

    def state(self, problem_id: str, rollout_seed: int) -> str:
        intent_id = self.intent_id(problem_id, rollout_seed)
        declaration_path = self.declarations_dir / f"{intent_id}.json"
        record_path = self.records_dir / f"{intent_id}.json"
        digest_path = self.records_dir / f"{intent_id}.sha256"
        if not declaration_path.exists() and not record_path.exists() and not digest_path.exists():
            return "interrupted_unknown" if self._ledger_mentions(intent_id) else "pending"
        if not declaration_path.exists() or not self._valid_declaration(
            declaration_path, problem_id, rollout_seed, intent_id
        ):
            return "interrupted_unknown"
        if not record_path.exists() and not digest_path.exists():
            # The declaration is committed before model generation.  After a
            # process boundary, its lack of terminal evidence is deliberately
            # ambiguous rather than pending.
            return "interrupted_unknown"
        if not record_path.exists() or not digest_path.exists():
            return "interrupted_unknown"
        try:
            payload = record_path.read_bytes()
            parsed = json.loads(payload.decode("utf-8"))
            declared_digest = digest_path.read_text(encoding="ascii").strip()
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return "interrupted_unknown"
        if not isinstance(parsed, Mapping) or declared_digest != hashlib.sha256(payload).hexdigest():
            return "interrupted_unknown"
        return "completed" if self._ledger_has_completion(intent_id, declared_digest) else "interrupted_unknown"

    def declare_intent(self, *, problem_id: str, rollout_seed: int) -> dict[str, str]:
        """Durably declare an attempt before the caller may invoke a model.

        The returned in-process declaration capability must be followed by
        :meth:`write_completed` immediately after successful generation.  A
        disconnect at any later point leaves the declaration on Drive and
        conservatively blocks regeneration on resume.
        """

        intent_id = self.intent_id(problem_id, rollout_seed)
        if self.state(problem_id, rollout_seed) != "pending":
            raise ArtifactIntegrityError(
                f"refusing to declare non-pending trajectory intent {intent_id!r}"
            )
        document = {
            "schema_version": self.schema_version,
            "event_type": "trajectory_intent_declared",
            "intent_id": intent_id,
            "problem_id": problem_id,
            "rollout_seed": rollout_seed,
        }
        payload = _canonical_json(document)
        declaration_sha256 = hashlib.sha256(payload).hexdigest()
        declaration_path = self.declarations_dir / f"{intent_id}.json"
        try:
            _write_exclusive(declaration_path, payload)
            _append_jsonl(
                self.ledger_path,
                {
                    "schema_version": self.schema_version,
                    "event_type": "trajectory_intent_declared",
                    "intent_id": intent_id,
                    "declaration_sha256": declaration_sha256,
                },
            )
        except Exception:
            # An exclusive declaration file that was written before a later
            # failure remains evidence.  It becomes interrupted_unknown and
            # cannot be silently retried.
            raise
        self._active_declarations.add(intent_id)
        return {"intent_id": intent_id, "declaration_sha256": declaration_sha256}

    def write_completed(
        self,
        *,
        problem_id: str,
        rollout_seed: int,
        record: Mapping[str, Any],
    ) -> dict[str, str]:
        """Durably checkpoint one declared private trajectory exactly once."""

        intent_id = self.intent_id(problem_id, rollout_seed)
        if intent_id not in self._active_declarations:
            raise ArtifactIntegrityError(
                "a trajectory must be declared in this process before generation and completion"
            )
        declaration_path = self.declarations_dir / f"{intent_id}.json"
        record_path = self.records_dir / f"{intent_id}.json"
        digest_path = self.records_dir / f"{intent_id}.sha256"
        if (
            not self._valid_declaration(declaration_path, problem_id, rollout_seed, intent_id)
            or record_path.exists()
            or digest_path.exists()
        ):
            raise ArtifactIntegrityError(
                f"refusing to replace trajectory intent {intent_id!r} after declaration"
            )
        document = {
            "schema_version": self.schema_version,
            "intent_id": intent_id,
            "problem_id": problem_id,
            "rollout_seed": rollout_seed,
            "record": record,
        }
        payload = _canonical_json(document)
        digest = hashlib.sha256(payload).hexdigest()
        try:
            _write_exclusive(record_path, payload)
            _write_exclusive(digest_path, (digest + "\n").encode("ascii"))
            _append_jsonl(
                self.ledger_path,
                {
                    "schema_version": self.schema_version,
                    "event_type": "trajectory_completed",
                    "intent_id": intent_id,
                    "record_sha256": digest,
                    "record_relative_path": f"records/{intent_id}.json",
                },
            )
        except Exception:
            # Any partially persisted file remains evidence and produces the
            # conservative interrupted_unknown state on resume.
            raise
        self._active_declarations.remove(intent_id)
        return {
            "intent_id": intent_id,
            "record_sha256": digest,
            "record_relative_path": f"records/{intent_id}.json",
        }

    def resume_action(self, problem_id: str, rollout_seed: int) -> str:
        state = self.state(problem_id, rollout_seed)
        return {
            "pending": "declare_then_execute",
            "completed": "skip_completed",
            "interrupted_unknown": "preserve_interrupted_unknown",
        }[state]

    def _valid_declaration(
        self,
        declaration_path: Path,
        problem_id: str,
        rollout_seed: int,
        intent_id: str,
    ) -> bool:
        try:
            document = json.loads(declaration_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False
        return (
            isinstance(document, Mapping)
            and document.get("schema_version") == self.schema_version
            and document.get("event_type") == "trajectory_intent_declared"
            and document.get("intent_id") == intent_id
            and document.get("problem_id") == problem_id
            and document.get("rollout_seed") == rollout_seed
        )

    def _ledger_mentions(self, intent_id: str) -> bool:
        if not self.ledger_path.exists():
            return False
        try:
            return any(
                json.loads(line).get("intent_id") == intent_id
                for line in self.ledger_path.read_text(encoding="utf-8").splitlines()
                if line
            )
        except (OSError, json.JSONDecodeError):
            return True

    def _ledger_has_completion(self, intent_id: str, digest: str) -> bool:
        if not self.ledger_path.exists():
            return False
        try:
            lines = self.ledger_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                return False
            if (
                event.get("event_type") == "trajectory_completed"
                and event.get("intent_id") == intent_id
                and event.get("record_sha256") == digest
            ):
                return True
        return False


def write_public_safe_json(public_root: Path, filename: str, value: Mapping[str, Any]) -> Path:
    """Write a public-safe aggregate file with a conservative name policy.

    The caller is responsible for supplying an aggregate, path-free payload.
    The function rejects common absolute POSIX, Windows, UNC, and Drive path
    forms so an error message cannot accidentally turn a private report into a
    public artifact.
    """

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.json", filename):
        raise ValueError("public-safe report filename must be a safe .json name")
    payload = _canonical_json(value)
    decoded = payload.decode("utf-8")
    if _contains_private_path_marker(decoded):
        raise ArtifactIntegrityError("public-safe report contains a user-specific path marker")
    destination = public_root / filename
    _write_exclusive(destination, payload)
    return destination


def _contains_private_path_marker(value: str) -> bool:
    """Conservatively detect filesystem paths in a public-safe JSON payload."""

    markers = (
        "/content/",
        "/home/",
        "/root/",
        "/tmp/",
        "/Users/",
        "MyDrive",
        "\\\\",
    )
    if any(marker in value for marker in markers):
        return True
    return re.search(r"(?<![A-Za-z0-9])[A-Za-z]:[\\\\/]", value) is not None
