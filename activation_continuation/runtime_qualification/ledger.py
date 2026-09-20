"""Append-only evidence ledger and deterministic resume classification."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from .models import (
    IntentState,
    QualificationIntent,
    QualificationPlan,
    ResumeDecision,
    canonical_json,
    json_ready,
)


class LedgerIntegrityError(RuntimeError):
    """The existing qualification evidence cannot safely be interpreted."""


class PlanMismatchError(LedgerIntegrityError):
    """A caller tried to resume an output directory using a changed plan."""


class AppendOnlyLedger:
    """A JSONL ledger that never rewrites evidence.

    The ledger is deliberately conservative after a process interruption.  An
    intent with a declaration/start record but no terminal record is labelled
    ``interrupted_unknown`` and is never rerun automatically: the previous
    process may have reached the model even though it failed to persist its
    terminal evidence.
    """

    schema_version = 1

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    raise LedgerIntegrityError(
                        f"blank line in append-only ledger at {self.path}:{line_number}"
                    )
                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError as error:
                    raise LedgerIntegrityError(
                        f"invalid JSON in append-only ledger at {self.path}:{line_number}"
                    ) from error
                if not isinstance(record, dict):
                    raise LedgerIntegrityError(
                        f"non-object ledger record at {self.path}:{line_number}"
                    )
                if record.get("schema_version") != self.schema_version:
                    raise LedgerIntegrityError(
                        f"unexpected ledger schema at {self.path}:{line_number}"
                    )
                if not isinstance(record.get("event_type"), str):
                    raise LedgerIntegrityError(
                        f"missing event_type at {self.path}:{line_number}"
                    )
                records.append(record)
        return tuple(records)

    def append(
        self,
        event_type: str,
        *,
        plan_fingerprint: str,
        intent_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not event_type:
            raise ValueError("event_type is required")
        record: dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_type": event_type,
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            "plan_fingerprint": plan_fingerprint,
            "payload": json_ready(dict(payload or {})),
        }
        if intent_id is not None:
            record["intent_id"] = intent_id
        encoded = (canonical_json(record) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # O_APPEND makes each append-only write intent explicit; loop until
        # every byte is written because a single os.write is not guaranteed to
        # consume the full record on every filesystem.
        descriptor = os.open(
            self.path,
            os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, "O_BINARY", 0),
            0o600,
        )
        try:
            remaining = memoryview(encoded)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("append-only ledger write made no progress")
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return record


def freeze_or_validate_plan(output_dir: Path, plan: QualificationPlan) -> Path:
    """Create an immutable plan manifest, or reject a changed resume request."""

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "qualification_plan.json"
    expected = plan.to_manifest()
    expected["plan_fingerprint"] = plan.fingerprint
    encoded = (canonical_json(expected) + "\n").encode("utf-8")
    if not manifest_path.exists():
        try:
            with manifest_path.open("xb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            # A concurrent initializer won the race.  Validation below is the
            # only safe response; a second plan must never overwrite it.
            pass
    try:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LedgerIntegrityError(f"cannot read frozen plan {manifest_path}") from error
    if existing != expected:
        raise PlanMismatchError(
            "qualification output directory already contains a different frozen plan"
        )
    return manifest_path


def _events_by_intent(records: Iterable[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        intent_id = record.get("intent_id")
        if isinstance(intent_id, str):
            grouped[intent_id].append(record)
    return grouped


def intent_state(
    intent: QualificationIntent,
    records: Iterable[Mapping[str, Any]],
    *,
    plan_fingerprint: str,
) -> IntentState:
    """Classify one fixed intent from append-only evidence only."""

    records_for_intent = _events_by_intent(records).get(intent.intent_id, [])
    events: list[str] = []
    for record in records_for_intent:
        if record.get("plan_fingerprint") != plan_fingerprint:
            raise LedgerIntegrityError(
                f"intent {intent.intent_id} has evidence from a different plan"
            )
        event_type = record.get("event_type")
        if isinstance(event_type, str):
            events.append(event_type)
    if "intent_completed" in events:
        if "intent_failed" in events:
            raise LedgerIntegrityError(
                f"intent {intent.intent_id} has conflicting completed and failed records"
            )
        return IntentState.COMPLETED
    if "intent_failed" in events:
        return IntentState.FAILED
    if "intent_interrupted_unknown" in events:
        return IntentState.INTERRUPTED_UNKNOWN
    if "intent_declared" in events or "intent_started" in events:
        return IntentState.INTERRUPTED_UNKNOWN
    return IntentState.PENDING


def deterministic_resume_decisions(
    intents: Iterable[QualificationIntent],
    records: Iterable[Mapping[str, Any]],
    *,
    plan_fingerprint: str,
) -> tuple[ResumeDecision, ...]:
    """Return the same no-retry decision for the same plan and ledger."""

    records_tuple = tuple(records)
    decisions: list[ResumeDecision] = []
    for intent in intents:
        state = intent_state(intent, records_tuple, plan_fingerprint=plan_fingerprint)
        if state is IntentState.PENDING:
            action = "execute"
            reason = "no prior evidence exists for this planned intent"
        elif state is IntentState.COMPLETED:
            action = "skip_completed"
            reason = "completed evidence is retained and must not be replaced"
        elif state is IntentState.FAILED:
            action = "skip_failed"
            reason = "failure evidence is retained and automatic retries are prohibited"
        else:
            action = "preserve_interrupted_unknown"
            reason = (
                "a prior process may have reached the model without a terminal record; "
                "automatic retry would replace an ambiguous attempt"
            )
        decisions.append(
            ResumeDecision(
                intent_id=intent.intent_id,
                state=state,
                action=action,
                reason=reason,
            )
        )
    return tuple(decisions)
