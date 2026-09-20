"""Stable data contracts for the non-benchmark runtime qualification harness.

The contracts deliberately contain no model imports.  This lets tests and a
dry-run plan execute on a machine with neither CUDA nor Transformers installed.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence


_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
MIB = 1024 * 1024


def require_safe_identifier(value: str, field_name: str) -> None:
    if not _SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(
            f"{field_name} must use only letters, digits, '.', '_' or '-': {value!r}"
        )


def json_ready(value: Any) -> Any:
    """Convert the small, explicit contract types into canonical JSON values."""

    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return json_ready(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_ready(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        json_ready(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class GenerationSpec:
    """Pinned synthetic generation settings used solely for qualification.

    The qualification is a GPU stress gate, not a scientific prompt-quality
    test.  Each fixed synthetic cycle therefore forces the full 4,096-token
    ceiling so the measured memory, throughput, and resume evidence actually
    cover the declared reasoning-budget path.
    """

    max_new_tokens: int = 4096
    min_new_tokens: int = 4096
    do_sample: bool = True
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int = 20
    min_p: float = 0.0

    def __post_init__(self) -> None:
        if self.max_new_tokens != 4096:
            raise ValueError(
                "runtime qualification must exercise the predeclared 4096-token design"
            )
        if self.min_new_tokens != self.max_new_tokens:
            raise ValueError(
                "runtime qualification must force every synthetic cycle through the 4096-token ceiling"
            )
        if self.do_sample and self.temperature <= 0:
            raise ValueError("temperature must be positive when sampling is enabled")
        if not 0 < self.top_p <= 1:
            raise ValueError("top_p must be in (0, 1]")
        if self.top_k < 0:
            raise ValueError("top_k must be non-negative")
        if not 0 <= self.min_p <= 1:
            raise ValueError("min_p must be in [0, 1]")


@dataclass(frozen=True)
class SyntheticCase:
    """A hand-written, non-benchmark prompt and a synthetic prefix."""

    case_id: str
    user_prompt: str
    reasoning_prefix: str
    seed: int

    def __post_init__(self) -> None:
        require_safe_identifier(self.case_id, "case_id")
        if not self.user_prompt.strip():
            raise ValueError("synthetic user_prompt must not be blank")
        if not self.reasoning_prefix.strip():
            raise ValueError("synthetic reasoning_prefix must not be blank")


DEFAULT_SYNTHETIC_CASES: tuple[SyntheticCase, ...] = (
    SyntheticCase(
        case_id="synthetic_arithmetic",
        user_prompt=(
            "This is a synthetic runtime check, not a benchmark question. "
            "Starting at 7, add 4 and then multiply the result by 3. "
            "Explain the calculation briefly."
        ),
        reasoning_prefix="We can compute this deterministically: first add 4 to 7. ",
        seed=1101,
    ),
    SyntheticCase(
        case_id="synthetic_symbolic",
        user_prompt=(
            "This is a synthetic runtime check, not a benchmark question. "
            "If a fictional machine maps f(n) to n plus 2, state f(9) and "
            "give one sentence of explanation."
        ),
        reasoning_prefix="The rule is stated directly, so substitute the supplied input. ",
        seed=2203,
    ),
)


@dataclass(frozen=True)
class QualificationPlan:
    """Immutable plan for a local-only Qwen3/Transformers qualification run.

    ``model_source`` may be a local snapshot directory or a cache-resolvable
    identifier.  ``local_files_only`` is intentionally fixed to true: this
    harness must never download a model as an incidental qualification action.
    """

    run_id: str
    model_id: str
    model_revision: str
    tokenizer_revision: str
    synthetic_cases: tuple[SyntheticCase, ...] = DEFAULT_SYNTHETIC_CASES
    cycles_per_case: int = 3
    generation: GenerationSpec = GenerationSpec()
    chat_template_kwargs: Mapping[str, Any] | None = None
    activation_layers: tuple[int, ...] | None = None
    local_files_only: bool = True
    required_device: str = "cuda"
    memory_growth_tolerance_bytes: int = 512 * MIB
    projected_trajectory_counts: tuple[int, ...] = (1800, 1200, 800)

    def __post_init__(self) -> None:
        require_safe_identifier(self.run_id, "run_id")
        if not self.model_id.strip() or not self.model_revision.strip():
            raise ValueError("model_id and model_revision are required provenance fields")
        if not self.tokenizer_revision.strip():
            raise ValueError("tokenizer_revision is required provenance")
        if not self.local_files_only:
            raise ValueError("qualification runner is local-files-only by design")
        if self.required_device != "cuda":
            raise ValueError("native BF16 qualification requires the CUDA device")
        if self.cycles_per_case < 2:
            raise ValueError("at least two synthetic cycles are required for repeatability")
        if not self.synthetic_cases:
            raise ValueError("at least one synthetic case is required")
        case_ids = [case.case_id for case in self.synthetic_cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("synthetic case IDs must be unique")
        if self.activation_layers is not None:
            if not self.activation_layers:
                raise ValueError("activation_layers must be null (all layers) or non-empty")
            if min(self.activation_layers) < 0:
                raise ValueError("activation layer indexes must be non-negative")
            if len(set(self.activation_layers)) != len(self.activation_layers):
                raise ValueError("activation layer indexes must be unique")
        if self.memory_growth_tolerance_bytes < 0:
            raise ValueError("memory_growth_tolerance_bytes must be non-negative")
        if not self.projected_trajectory_counts or min(self.projected_trajectory_counts) <= 0:
            raise ValueError("projected trajectory counts must be positive")

    @property
    def activation_layer_policy(self) -> str:
        return "all_transformer_layers" if self.activation_layers is None else "predeclared_subset"

    @property
    def fingerprint(self) -> str:
        return sha256_json(self.to_manifest())

    def to_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "tokenizer_revision": self.tokenizer_revision,
            "synthetic_cases": json_ready(self.synthetic_cases),
            "cycles_per_case": self.cycles_per_case,
            "generation": json_ready(self.generation),
            "chat_template_kwargs": json_ready(self.chat_template_kwargs or {}),
            "activation_layers": list(self.activation_layers)
            if self.activation_layers is not None
            else None,
            "activation_layer_policy": self.activation_layer_policy,
            "local_files_only": self.local_files_only,
            "required_device": self.required_device,
            "memory_growth_tolerance_bytes": self.memory_growth_tolerance_bytes,
            "projected_trajectory_counts": list(self.projected_trajectory_counts),
            "failure_policy": {
                "retry_completed": False,
                "retry_failed": False,
                "retry_interrupted_unknown": False,
                "replace_cases": False,
            },
        }


@dataclass(frozen=True)
class QualificationIntent:
    """One planned cycle with an immutable ID and deterministic seed."""

    intent_id: str
    case: SyntheticCase
    cycle_index: int
    seed: int

    def __post_init__(self) -> None:
        require_safe_identifier(self.intent_id, "intent_id")
        if self.cycle_index < 0:
            raise ValueError("cycle_index must be non-negative")


def planned_intents(plan: QualificationPlan) -> tuple[QualificationIntent, ...]:
    intents: list[QualificationIntent] = []
    for case in plan.synthetic_cases:
        for cycle_index in range(plan.cycles_per_case):
            seed = case.seed + cycle_index
            intent_id = f"{case.case_id}--cycle-{cycle_index:02d}--seed-{seed}"
            intents.append(
                QualificationIntent(
                    intent_id=intent_id,
                    case=case,
                    cycle_index=cycle_index,
                    seed=seed,
                )
            )
    return tuple(intents)


@dataclass(frozen=True)
class CudaAvailability:
    torch_available: bool
    cuda_available: bool
    device_count: int | None
    device_name: str | None
    cuda_version: str | None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return json_ready(self)


@dataclass(frozen=True)
class MemorySnapshot:
    """Memory values are nullable when CUDA cannot be queried."""

    cuda_available: bool
    device: str
    allocated_bytes: int | None
    reserved_bytes: int | None
    peak_allocated_bytes: int | None
    free_bytes: int | None
    total_bytes: int | None

    def to_dict(self) -> dict[str, Any]:
        return json_ready(self)


@dataclass(frozen=True)
class ActivationVector:
    """A single last-token residual activation stored in reduced precision."""

    layer_index: int
    values: tuple[float, ...]
    source_dtype: str
    stored_dtype: str = "float16"

    def __post_init__(self) -> None:
        if self.layer_index < 0:
            raise ValueError("layer_index must be non-negative")
        if not self.values:
            raise ValueError("activation vector must not be empty")
        if self.stored_dtype != "float16":
            raise ValueError("the private qualification format currently stores float16 vectors")


@dataclass(frozen=True)
class ActivationArtifact:
    relative_path: str
    layer_index: int
    vector_length: int
    source_dtype: str
    stored_dtype: str
    byte_count: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return json_ready(self)


@dataclass(frozen=True)
class SyntheticExecution:
    """Runner output intentionally contains hashes rather than raw generated text."""

    prompt_token_count: int
    generated_token_ids: tuple[int, ...]
    generated_text_sha256: str
    elapsed_seconds: float
    context_limit_tokens: int | None
    activations: tuple[ActivationVector, ...]
    runner_provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.prompt_token_count <= 0:
            raise ValueError("prompt_token_count must be positive")
        if self.elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be non-negative")
        if not self.generated_text_sha256:
            raise ValueError("generated_text_sha256 is required")
        if not self.activations:
            raise ValueError("synthetic execution must extract at least one activation")

    @property
    def generated_token_count(self) -> int:
        return len(self.generated_token_ids)

    @property
    def tokens_per_second(self) -> float | None:
        if self.elapsed_seconds <= 0:
            return None
        return self.generated_token_count / self.elapsed_seconds


class IntentState(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED_UNKNOWN = "interrupted_unknown"


@dataclass(frozen=True)
class ResumeDecision:
    intent_id: str
    state: IntentState
    action: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return json_ready(self)


@dataclass(frozen=True)
class RuntimeProjection:
    target_trajectories: int
    estimated_wall_seconds: float | None
    estimated_activation_bytes: int | None

    def to_dict(self) -> dict[str, Any]:
        return json_ready(self)
