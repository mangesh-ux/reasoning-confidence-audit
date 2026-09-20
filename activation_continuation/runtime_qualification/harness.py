"""Isolated, append-only synthetic runtime qualification orchestration."""

from __future__ import annotations

import hashlib
import math
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .ledger import AppendOnlyLedger, deterministic_resume_decisions, freeze_or_validate_plan
from .models import (
    ActivationArtifact,
    ActivationVector,
    CudaAvailability,
    IntentState,
    MemorySnapshot,
    QualificationIntent,
    QualificationPlan,
    ResumeDecision,
    RuntimeProjection,
    SyntheticExecution,
    canonical_json,
    json_ready,
    planned_intents,
)
from .runner import MemoryProbe, SyntheticRunner


class ActivationSerializationError(RuntimeError):
    pass


class ActivationSerializer:
    """Write one compact, private float16 vector file per layer without replacement."""

    magic = b"ACRQ1\x00"

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def write(
        self, intent_id: str, vector: ActivationVector
    ) -> ActivationArtifact:
        relative_path = (
            Path("activations") / intent_id / f"layer-{vector.layer_index:03d}.acrq"
        )
        destination = self.output_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        header = {
            "schema_version": 1,
            "intent_id": intent_id,
            "layer_index": vector.layer_index,
            "vector_length": len(vector.values),
            "source_dtype": vector.source_dtype,
            "stored_dtype": vector.stored_dtype,
            "byte_order": "little",
        }
        header_bytes = canonical_json(header).encode("utf-8")
        try:
            raw = struct.pack(f"<{len(vector.values)}e", *vector.values)
        except (OverflowError, struct.error) as error:
            raise ActivationSerializationError(
                f"cannot encode layer {vector.layer_index} as float16"
            ) from error
        if not all(math.isfinite(value) for value in vector.values):
            raise ActivationSerializationError(
                f"layer {vector.layer_index} contains non-finite activation values"
            )
        payload = self.magic + struct.pack("<I", len(header_bytes)) + header_bytes + raw
        try:
            with destination.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as error:
            raise ActivationSerializationError(
                f"refusing to replace existing activation artifact {destination}"
            ) from error
        return ActivationArtifact(
            relative_path=relative_path.as_posix(),
            layer_index=vector.layer_index,
            vector_length=len(vector.values),
            source_dtype=vector.source_dtype,
            stored_dtype=vector.stored_dtype,
            byte_count=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
        )


def inspect_activation_artifact(path: Path) -> dict[str, Any]:
    """Validate a stored artifact without needing Torch or NumPy."""

    payload = path.read_bytes()
    if not payload.startswith(ActivationSerializer.magic):
        raise ActivationSerializationError(f"unexpected activation artifact magic: {path}")
    start = len(ActivationSerializer.magic)
    if len(payload) < start + 4:
        raise ActivationSerializationError(f"truncated activation artifact header: {path}")
    header_length = struct.unpack("<I", payload[start : start + 4])[0]
    header_start = start + 4
    header_end = header_start + header_length
    try:
        header = __import__("json").loads(payload[header_start:header_end].decode("utf-8"))
    except Exception as error:
        raise ActivationSerializationError(f"invalid activation artifact header: {path}") from error
    vector_length = header.get("vector_length")
    if not isinstance(vector_length, int) or vector_length <= 0:
        raise ActivationSerializationError(f"invalid vector length in activation artifact: {path}")
    expected_length = header_end + 2 * vector_length
    if len(payload) != expected_length:
        raise ActivationSerializationError(f"activation artifact byte length mismatch: {path}")
    return {
        "header": header,
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


@dataclass(frozen=True)
class QualificationReport:
    plan_fingerprint: str
    execution_requested: bool
    execution_status: str
    cuda: CudaAvailability
    decisions: tuple[ResumeDecision, ...]
    summary: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_fingerprint": self.plan_fingerprint,
            "execution_requested": self.execution_requested,
            "execution_status": self.execution_status,
            "cuda": self.cuda.to_dict(),
            "resume_decisions": [decision.to_dict() for decision in self.decisions],
            "summary": json_ready(self.summary),
        }


class RuntimeQualificationHarness:
    """Runs only a frozen synthetic plan, and only after explicit opt-in.

    The safe default is ``execute_synthetic=False``.  It freezes/validates the
    plan and reports CUDA/resume state, but never calls the runner and therefore
    cannot load a model, call a benchmark, or initiate generation.
    """

    def __init__(
        self,
        *,
        output_dir: Path,
        plan: QualificationPlan,
        memory_probe: MemoryProbe,
        runner: SyntheticRunner | None = None,
    ) -> None:
        self.output_dir = output_dir
        self.plan = plan
        self.memory_probe = memory_probe
        self.runner = runner
        self.ledger = AppendOnlyLedger(output_dir / "qualification_ledger.jsonl")
        self.serializer = ActivationSerializer(output_dir)

    def run(self, *, execute_synthetic: bool = False) -> QualificationReport:
        """Execute a resume-safe synthetic qualification only on explicit request."""

        freeze_or_validate_plan(self.output_dir, self.plan)
        records = self.ledger.read()
        self._validate_ledger_plan(records)
        if not any(record.get("event_type") == "run_initialized" for record in records):
            self.ledger.append(
                "run_initialized",
                plan_fingerprint=self.plan.fingerprint,
                payload={"run_id": self.plan.run_id, "mode": "synthetic_qualification"},
            )
        cuda = self.memory_probe.availability()
        self.ledger.append(
            "cuda_detection",
            plan_fingerprint=self.plan.fingerprint,
            payload=cuda.to_dict(),
        )
        initial_decisions = self._resume_decisions()
        if not execute_synthetic:
            return self._report(
                execution_requested=False,
                execution_status="dry_run_no_model_calls",
                cuda=cuda,
                decisions=initial_decisions,
            )
        if self.runner is None:
            raise ValueError("a runner is required when execute_synthetic=True")
        if not cuda.cuda_available:
            self.ledger.append(
                "execution_blocked_cuda",
                plan_fingerprint=self.plan.fingerprint,
                payload={"cuda": cuda.to_dict()},
            )
            return self._report(
                execution_requested=True,
                execution_status="blocked_cuda_unavailable",
                cuda=cuda,
                decisions=initial_decisions,
            )
        if not any(decision.state is IntentState.PENDING for decision in initial_decisions):
            self.ledger.append(
                "execution_not_started_no_pending_intents",
                plan_fingerprint=self.plan.fingerprint,
                payload={"resume_actions": [decision.action for decision in initial_decisions]},
            )
            return self._report(
                execution_requested=True,
                execution_status="no_pending_intents",
                cuda=cuda,
                decisions=initial_decisions,
            )
        prepared = False
        try:
            self.memory_probe.reset_peak()
            self.ledger.append(
                "model_load_started",
                plan_fingerprint=self.plan.fingerprint,
                payload={"local_files_only": self.plan.local_files_only},
            )
            provenance = self.runner.prepare(self.plan)
            prepared = True
            self.ledger.append(
                "model_load_completed",
                plan_fingerprint=self.plan.fingerprint,
                payload={
                    "runner_provenance": json_ready(provenance),
                    "memory_after_load": self.memory_probe.snapshot().to_dict(),
                },
            )
        except Exception as error:
            self.ledger.append(
                "model_load_failed",
                plan_fingerprint=self.plan.fingerprint,
                payload=_error_payload(error),
            )
            return self._report(
                execution_requested=True,
                execution_status="model_load_failed",
                cuda=cuda,
                decisions=self._resume_decisions(),
            )
        try:
            decisions = self._resume_decisions()
            for decision, intent in zip(decisions, planned_intents(self.plan), strict=True):
                self.ledger.append(
                    "resume_decision",
                    plan_fingerprint=self.plan.fingerprint,
                    intent_id=intent.intent_id,
                    payload=decision.to_dict(),
                )
                if decision.state is IntentState.PENDING:
                    self._execute_pending_intent(intent)
            return self._report(
                execution_requested=True,
                execution_status="synthetic_execution_finished",
                cuda=cuda,
                decisions=self._resume_decisions(),
            )
        finally:
            if prepared:
                self.runner.close()

    def _execute_pending_intent(self, intent: QualificationIntent) -> None:
        self.ledger.append(
            "intent_declared",
            plan_fingerprint=self.plan.fingerprint,
            intent_id=intent.intent_id,
            payload={
                "case_id": intent.case.case_id,
                "cycle_index": intent.cycle_index,
                "seed": intent.seed,
            },
        )
        self.ledger.append(
            "intent_started",
            plan_fingerprint=self.plan.fingerprint,
            intent_id=intent.intent_id,
            payload={},
        )
        try:
            self.memory_probe.reset_peak()
            before = self.memory_probe.snapshot()
            assert self.runner is not None
            execution = self.runner.execute(intent, self.plan)
            after = self.memory_probe.snapshot()
            artifacts = tuple(
                self.serializer.write(intent.intent_id, vector) for vector in execution.activations
            )
            self.ledger.append(
                "intent_completed",
                plan_fingerprint=self.plan.fingerprint,
                intent_id=intent.intent_id,
                payload=_completed_payload(intent, execution, before, after, artifacts, self.plan),
            )
        except Exception as error:
            self.ledger.append(
                "intent_failed",
                plan_fingerprint=self.plan.fingerprint,
                intent_id=intent.intent_id,
                payload=_error_payload(error),
            )

    def _resume_decisions(self) -> tuple[ResumeDecision, ...]:
        return deterministic_resume_decisions(
            planned_intents(self.plan),
            self.ledger.read(),
            plan_fingerprint=self.plan.fingerprint,
        )

    def _report(
        self,
        *,
        execution_requested: bool,
        execution_status: str,
        cuda: CudaAvailability,
        decisions: tuple[ResumeDecision, ...],
    ) -> QualificationReport:
        return QualificationReport(
            plan_fingerprint=self.plan.fingerprint,
            execution_requested=execution_requested,
            execution_status=execution_status,
            cuda=cuda,
            decisions=decisions,
            summary=summarize_evidence(self.ledger.read(), self.plan),
        )

    def _validate_ledger_plan(self, records: Iterable[Mapping[str, Any]]) -> None:
        for record in records:
            fingerprint = record.get("plan_fingerprint")
            if fingerprint != self.plan.fingerprint:
                raise RuntimeError(
                    "append-only ledger contains evidence from a different frozen plan"
                )


def _error_payload(error: Exception) -> dict[str, str]:
    message = str(error).replace("\n", " ")[:1000]
    return {"error_type": type(error).__name__, "message": message}


def _completed_payload(
    intent: QualificationIntent,
    execution: SyntheticExecution,
    before: MemorySnapshot,
    after: MemorySnapshot,
    artifacts: tuple[ActivationArtifact, ...],
    plan: QualificationPlan,
) -> dict[str, Any]:
    required_context = execution.prompt_token_count + plan.generation.max_new_tokens
    context_safe = (
        required_context <= execution.context_limit_tokens
        if execution.context_limit_tokens is not None
        else None
    )
    return {
        "case_id": intent.case.case_id,
        "cycle_index": intent.cycle_index,
        "seed": intent.seed,
        "prompt_token_count": execution.prompt_token_count,
        "generated_token_count": execution.generated_token_count,
        "generated_token_ids_sha256": hashlib.sha256(
            canonical_json(list(execution.generated_token_ids)).encode("utf-8")
        ).hexdigest(),
        "generated_text_sha256": execution.generated_text_sha256,
        "elapsed_seconds": execution.elapsed_seconds,
        "tokens_per_second": execution.tokens_per_second,
        "context": {
            "context_limit_tokens": execution.context_limit_tokens,
            "prompt_plus_required_generation_tokens": required_context,
            "safe_for_4096_generation": context_safe,
        },
        "memory_before": before.to_dict(),
        "memory_after": after.to_dict(),
        "activation_artifacts": [artifact.to_dict() for artifact in artifacts],
        "activation_total_bytes": sum(artifact.byte_count for artifact in artifacts),
        "runner_provenance": json_ready(execution.runner_provenance),
    }


def summarize_evidence(
    records: Iterable[Mapping[str, Any]], plan: QualificationPlan
) -> dict[str, Any]:
    """Summarize only recorded synthetic evidence; never invent a pass verdict."""

    records_tuple = tuple(records)
    completions = [
        record.get("payload", {})
        for record in records_tuple
        if record.get("event_type") == "intent_completed"
    ]
    failures = sum(record.get("event_type") == "intent_failed" for record in records_tuple)
    ambiguous = sum(
        record.get("event_type") == "intent_interrupted_unknown" for record in records_tuple
    )
    # Declarations without terminal evidence are also unknown.  This reports
    # the count without appending a terminal event and therefore preserves
    # interruption semantics.
    terminal_ids = {
        record.get("intent_id")
        for record in records_tuple
        if record.get("event_type") in {"intent_completed", "intent_failed"}
    }
    declared_ids = {
        record.get("intent_id")
        for record in records_tuple
        if record.get("event_type") in {"intent_declared", "intent_started"}
    }
    ambiguous += len({item for item in declared_ids - terminal_ids if item is not None})
    total_elapsed = sum(
        float(payload.get("elapsed_seconds", 0.0))
        for payload in completions
        if isinstance(payload, Mapping)
    )
    total_tokens = sum(
        int(payload.get("generated_token_count", 0))
        for payload in completions
        if isinstance(payload, Mapping)
    )
    total_activation_bytes = sum(
        int(payload.get("activation_total_bytes", 0))
        for payload in completions
        if isinstance(payload, Mapping)
    )
    generated_counts = [
        int(payload.get("generated_token_count", 0))
        for payload in completions
        if isinstance(payload, Mapping)
    ]
    tokens_per_second = total_tokens / total_elapsed if total_elapsed > 0 else None
    mean_wall_seconds = total_elapsed / len(completions) if completions else None
    mean_activation_bytes = (
        total_activation_bytes / len(completions) if completions else None
    )
    projections = tuple(
        RuntimeProjection(
            target_trajectories=count,
            estimated_wall_seconds=(mean_wall_seconds * count if mean_wall_seconds else None),
            estimated_activation_bytes=(
                int(math.ceil(mean_activation_bytes * count))
                if mean_activation_bytes is not None
                else None
            ),
        ).to_dict()
        for count in plan.projected_trajectory_counts
    )
    contexts = [
        payload.get("context", {}) for payload in completions if isinstance(payload, Mapping)
    ]
    peak_values = [
        after.get("peak_allocated_bytes")
        for payload in completions
        if isinstance(payload, Mapping)
        for after in (payload.get("memory_after"),)
        if isinstance(after, Mapping) and isinstance(after.get("peak_allocated_bytes"), int)
    ]
    context_values = [
        context.get("safe_for_4096_generation")
        for context in contexts
        if isinstance(context, Mapping)
    ]
    if not context_values:
        context_status = "not_evaluated"
    elif all(value is True for value in context_values):
        context_status = "all_recorded_cycles_safe"
    elif any(value is False for value in context_values):
        context_status = "unsafe_recorded_cycle"
    else:
        context_status = "context_limit_unavailable"
    return {
        "planned_intent_count": len(planned_intents(plan)),
        "completed_intent_count": len(completions),
        "failed_intent_count": failures,
        "interrupted_unknown_intent_count": ambiguous,
        "generated_tokens_recorded": total_tokens,
        "minimum_generated_token_count": min(generated_counts) if generated_counts else None,
        "all_cycles_reached_generation_cap": bool(generated_counts)
        and all(count >= plan.generation.max_new_tokens for count in generated_counts),
        "generation_cap_tokens": plan.generation.max_new_tokens,
        "generation_wall_seconds_recorded": total_elapsed,
        "aggregate_tokens_per_second": tokens_per_second,
        "activation_bytes_recorded": total_activation_bytes,
        "activation_storage_projection_only": projections,
        "context_safety_status": context_status,
        "memory_stability": memory_stability(completions, plan.memory_growth_tolerance_bytes),
        "peak_allocated_bytes_recorded": max(peak_values) if peak_values else None,
        "scope_note": (
            "Projection uses completed synthetic cycles only and covers activation artifacts only; "
            "it is not a benchmark runtime, full-study disk, latency, or scientific-result estimate."
        ),
    }


def memory_stability(
    completion_payloads: Iterable[Mapping[str, Any]], tolerance_bytes: int
) -> dict[str, Any]:
    """Describe post-cycle CUDA memory growth without declaring a leak diagnosis."""

    reserved_values: list[int] = []
    allocated_values: list[int] = []
    for payload in completion_payloads:
        after = payload.get("memory_after")
        if not isinstance(after, Mapping):
            continue
        reserved = after.get("reserved_bytes")
        allocated = after.get("allocated_bytes")
        if isinstance(reserved, int):
            reserved_values.append(reserved)
        if isinstance(allocated, int):
            allocated_values.append(allocated)
    if len(reserved_values) < 2 and len(allocated_values) < 2:
        return {
            "status": "not_evaluable",
            "reason": "fewer than two CUDA post-cycle memory snapshots",
        }
    first_reserved = reserved_values[0] if reserved_values else None
    last_reserved = reserved_values[-1] if reserved_values else None
    reserved_growth = (
        last_reserved - first_reserved
        if first_reserved is not None and last_reserved is not None
        else None
    )
    first_allocated = allocated_values[0] if allocated_values else None
    last_allocated = allocated_values[-1] if allocated_values else None
    allocated_growth = (
        last_allocated - first_allocated
        if first_allocated is not None and last_allocated is not None
        else None
    )
    observed_growth = max(
        0,
        reserved_growth if reserved_growth is not None else 0,
        allocated_growth if allocated_growth is not None else 0,
    )
    return {
        "status": "within_tolerance" if observed_growth <= tolerance_bytes else "growth_observed",
        "tolerance_bytes": tolerance_bytes,
        "reserved_first_bytes": first_reserved,
        "reserved_last_bytes": last_reserved,
        "reserved_growth_bytes": reserved_growth,
        "allocated_first_bytes": first_allocated,
        "allocated_last_bytes": last_allocated,
        "allocated_growth_bytes": allocated_growth,
        "max_positive_growth_bytes": observed_growth,
    }
