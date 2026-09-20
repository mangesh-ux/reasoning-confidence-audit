"""Strict, data-free configuration loading for the Colab execution layer."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class ColabConfigurationError(ValueError):
    """A Colab configuration does not preserve the frozen execution contract."""


_RELATIVE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_FROZEN_QWEN_REVISION = "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e"
_FROZEN_RUNTIME_PACKAGES = {
    "accelerate": "1.12.0",
    "datasets": "3.6.0",
    "huggingface-hub": "0.36.2",
    "latex2sympy2_extended": "1.11.0",
    "math-verify": "0.9.0",
    "numpy": "2.5.2",
    "packaging": "26.3",
    "safetensors": "0.8.0",
    "sympy": "1.14.0",
    "tokenizers": "0.21.4",
    "torch": "2.9.1+cu128",
    "transformers": "4.51.3",
}


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ColabConfigurationError(f"{field} must be an object")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ColabConfigurationError(f"{field} must be a non-empty string")
    return value


def _integer(value: object, field: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ColabConfigurationError(f"{field} must be an integer >= {minimum}")
    return value


def _number(value: object, field: str, *, minimum: float | None = None) -> float:
    if type(value) not in {int, float}:
        raise ColabConfigurationError(f"{field} must be numeric")
    converted = float(value)
    if minimum is not None and converted < minimum:
        raise ColabConfigurationError(f"{field} must be >= {minimum}")
    return converted


def _boolean(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise ColabConfigurationError(f"{field} must be a boolean")
    return value


def _relative_component(value: object, field: str) -> str:
    name = _string(value, field)
    if not _RELATIVE_COMPONENT.fullmatch(name):
        raise ColabConfigurationError(
            f"{field} must be a single safe relative path component, not {name!r}"
        )
    return name


@dataclass(frozen=True)
class ModelConfig:
    repo_id: str
    revision: str
    tokenizer_revision: str
    trust_remote_code: bool
    dtype: str

    def __post_init__(self) -> None:
        if self.repo_id != "Qwen/Qwen3-1.7B":
            raise ColabConfigurationError("the frozen primary model is Qwen/Qwen3-1.7B")
        if not _GIT_SHA.fullmatch(self.revision):
            raise ColabConfigurationError("model.revision must be a 40-character commit SHA")
        if self.revision != _FROZEN_QWEN_REVISION:
            raise ColabConfigurationError("model.revision must remain the frozen Qwen3-1.7B commit")
        if self.tokenizer_revision != self.revision:
            raise ColabConfigurationError(
                "model.tokenizer_revision must equal model.revision for this frozen study"
            )
        if self.trust_remote_code:
            raise ColabConfigurationError("trust_remote_code must remain false")
        if self.dtype != "bfloat16":
            raise ColabConfigurationError("the authorized primary runtime is bfloat16")


@dataclass(frozen=True)
class GenerationConfig:
    thinking_mode: bool
    do_sample: bool
    temperature: float
    top_p: float
    top_k: int
    min_p: float
    max_new_tokens: int

    def __post_init__(self) -> None:
        if not self.thinking_mode:
            raise ColabConfigurationError("thinking_mode must remain true")
        if not self.do_sample:
            raise ColabConfigurationError("thinking-mode qualification must use sampling")
        if (self.temperature, self.top_p, self.top_k, self.min_p) != (0.6, 0.95, 20, 0.0):
            raise ColabConfigurationError(
                "the Qwen3 thinking decoding configuration is frozen at 0.6/0.95/20/0"
            )
        if self.max_new_tokens != 4096:
            raise ColabConfigurationError("the maximum reasoning budget is frozen at 4096")


@dataclass(frozen=True)
class QualificationConfig:
    run_id: str
    cycles_per_case: int
    activation_layers: tuple[int, ...] | None
    minimum_vram_gib: int
    minimum_free_disk_gib: int
    memory_growth_tolerance_mib: int

    def __post_init__(self) -> None:
        if not _RELATIVE_COMPONENT.fullmatch(self.run_id):
            raise ColabConfigurationError("qualification.run_id must be a safe identifier")
        if self.cycles_per_case != 3:
            raise ColabConfigurationError("the frozen synthetic qualification uses exactly three cycles per case")
        if self.activation_layers is not None:
            raise ColabConfigurationError("the frozen qualification extracts all transformer layers")
        if self.minimum_vram_gib != 16 or self.minimum_free_disk_gib != 30:
            raise ColabConfigurationError("the frozen qualification resource thresholds are 16 GiB VRAM and 30 GiB disk")
        if self.memory_growth_tolerance_mib != 512:
            raise ColabConfigurationError("the frozen memory-growth tolerance is 512 MiB")


@dataclass(frozen=True)
class ArtifactConfig:
    model_cache_dir: str
    qualification_dir: str
    private_study_dir: str
    public_safe_dir: str
    provenance_dir: str

    def __post_init__(self) -> None:
        names = (
            self.model_cache_dir,
            self.qualification_dir,
            self.private_study_dir,
            self.public_safe_dir,
            self.provenance_dir,
        )
        if len(set(names)) != len(names):
            raise ColabConfigurationError("artifact directory names must be distinct")


@dataclass(frozen=True)
class RuntimeLockConfig:
    """The import-time environment identity required by the frozen runtime."""

    python_major_minor: str
    torch_cuda_build: str
    packages: Mapping[str, str]

    def __post_init__(self) -> None:
        if self.python_major_minor != "3.12":
            raise ColabConfigurationError("the Colab execution lock requires CPython 3.12")
        if self.torch_cuda_build != "12.8":
            raise ColabConfigurationError("the primary Torch build must target CUDA 12.8")
        if dict(self.packages) != _FROZEN_RUNTIME_PACKAGES:
            raise ColabConfigurationError(
                "runtime_lock.packages must exactly match the frozen execution package versions"
            )


@dataclass(frozen=True)
class BenchmarkGateConfig:
    manifest_path: str
    require_qualification_pass: bool
    default_run_benchmark: bool

    def __post_init__(self) -> None:
        path = Path(self.manifest_path)
        if path.is_absolute() or ".." in path.parts:
            raise ColabConfigurationError("benchmark manifest path must remain repository relative")
        if self.manifest_path != "activation_continuation/manifests/study_manifest.json":
            raise ColabConfigurationError("the frozen benchmark manifest path must not change")
        if not self.require_qualification_pass:
            raise ColabConfigurationError("benchmark execution must require qualification PASS")
        if self.default_run_benchmark:
            raise ColabConfigurationError("benchmark execution must default to false")


@dataclass(frozen=True)
class ColabRuntimeConfig:
    schema_version: int
    study_id: str
    model: ModelConfig
    generation: GenerationConfig
    qualification: QualificationConfig
    artifacts: ArtifactConfig
    runtime_lock: RuntimeLockConfig
    prior_local_runtime_failure: Mapping[str, str]
    benchmark_gate: BenchmarkGateConfig
    source_path: Path
    canonical_bytes: bytes

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    def public_identity(self) -> dict[str, object]:
        """Return provenance that deliberately excludes the private Drive root."""

        return {
            "config_schema_version": self.schema_version,
            "config_sha256": self.fingerprint,
            "study_id": self.study_id,
            "model_id": self.model.repo_id,
            "model_revision": self.model.revision,
            "tokenizer_revision": self.model.tokenizer_revision,
            "generation": {
                "thinking_mode": self.generation.thinking_mode,
                "do_sample": self.generation.do_sample,
                "temperature": self.generation.temperature,
                "top_p": self.generation.top_p,
                "top_k": self.generation.top_k,
                "min_p": self.generation.min_p,
                "max_new_tokens": self.generation.max_new_tokens,
            },
            "runtime_lock": {
                "python_major_minor": self.runtime_lock.python_major_minor,
                "torch_cuda_build": self.runtime_lock.torch_cuda_build,
                "packages": dict(self.runtime_lock.packages),
            },
            "prior_local_runtime_failure": dict(self.prior_local_runtime_failure),
        }


def load_colab_runtime_config(path: Path) -> ColabRuntimeConfig:
    """Load a pinned JSON configuration without accessing a model or network."""

    try:
        raw_bytes = path.read_bytes()
        raw = json.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ColabConfigurationError(f"cannot read Colab configuration: {path}") from error
    root = _mapping(raw, "root")
    schema_version = _integer(root.get("schema_version"), "schema_version", minimum=1)
    if schema_version != 1:
        raise ColabConfigurationError(f"unsupported configuration schema {schema_version}")
    model_data = _mapping(root.get("model"), "model")
    generation_data = _mapping(root.get("generation"), "generation")
    qualification_data = _mapping(root.get("qualification"), "qualification")
    artifact_data = _mapping(root.get("artifacts"), "artifacts")
    runtime_lock_data = _mapping(root.get("runtime_lock"), "runtime_lock")
    gate_data = _mapping(root.get("benchmark_gate"), "benchmark_gate")
    prior = _mapping(root.get("prior_local_runtime_failure"), "prior_local_runtime_failure")
    activation_layers_value = qualification_data.get("activation_layers")
    if activation_layers_value is None:
        activation_layers = None
    elif isinstance(activation_layers_value, list) and all(
        type(value) is int and value >= 0 for value in activation_layers_value
    ):
        activation_layers = tuple(activation_layers_value)
    else:
        raise ColabConfigurationError("qualification.activation_layers must be null or non-negative integers")
    config = ColabRuntimeConfig(
        schema_version=schema_version,
        study_id=_string(root.get("study_id"), "study_id"),
        model=ModelConfig(
            repo_id=_string(model_data.get("repo_id"), "model.repo_id"),
            revision=_string(model_data.get("revision"), "model.revision"),
            tokenizer_revision=_string(
                model_data.get("tokenizer_revision"), "model.tokenizer_revision"
            ),
            trust_remote_code=_boolean(model_data.get("trust_remote_code"), "model.trust_remote_code"),
            dtype=_string(model_data.get("dtype"), "model.dtype"),
        ),
        generation=GenerationConfig(
            thinking_mode=_boolean(generation_data.get("thinking_mode"), "generation.thinking_mode"),
            do_sample=_boolean(generation_data.get("do_sample"), "generation.do_sample"),
            temperature=_number(generation_data.get("temperature"), "generation.temperature"),
            top_p=_number(generation_data.get("top_p"), "generation.top_p"),
            top_k=_integer(generation_data.get("top_k"), "generation.top_k", minimum=0),
            min_p=_number(generation_data.get("min_p"), "generation.min_p", minimum=0),
            max_new_tokens=_integer(
                generation_data.get("max_new_tokens"), "generation.max_new_tokens", minimum=1
            ),
        ),
        qualification=QualificationConfig(
            run_id=_string(qualification_data.get("run_id"), "qualification.run_id"),
            cycles_per_case=_integer(
                qualification_data.get("cycles_per_case"), "qualification.cycles_per_case", minimum=1
            ),
            activation_layers=activation_layers,
            minimum_vram_gib=_integer(
                qualification_data.get("minimum_vram_gib"), "qualification.minimum_vram_gib", minimum=1
            ),
            minimum_free_disk_gib=_integer(
                qualification_data.get("minimum_free_disk_gib"), "qualification.minimum_free_disk_gib", minimum=1
            ),
            memory_growth_tolerance_mib=_integer(
                qualification_data.get("memory_growth_tolerance_mib"),
                "qualification.memory_growth_tolerance_mib",
                minimum=0,
            ),
        ),
        artifacts=ArtifactConfig(
            model_cache_dir=_relative_component(artifact_data.get("model_cache_dir"), "artifacts.model_cache_dir"),
            qualification_dir=_relative_component(artifact_data.get("qualification_dir"), "artifacts.qualification_dir"),
            private_study_dir=_relative_component(artifact_data.get("private_study_dir"), "artifacts.private_study_dir"),
            public_safe_dir=_relative_component(artifact_data.get("public_safe_dir"), "artifacts.public_safe_dir"),
            provenance_dir=_relative_component(artifact_data.get("provenance_dir"), "artifacts.provenance_dir"),
        ),
        runtime_lock=RuntimeLockConfig(
            python_major_minor=_string(
                runtime_lock_data.get("python_major_minor"), "runtime_lock.python_major_minor"
            ),
            torch_cuda_build=_string(
                runtime_lock_data.get("torch_cuda_build"), "runtime_lock.torch_cuda_build"
            ),
            packages={
                _string(key, "runtime_lock.packages key"): _string(
                    value, f"runtime_lock.packages.{key}"
                )
                for key, value in _mapping(runtime_lock_data.get("packages"), "runtime_lock.packages").items()
            },
        ),
        prior_local_runtime_failure={
            key: _string(value, f"prior_local_runtime_failure.{key}")
            for key, value in prior.items()
        },
        benchmark_gate=BenchmarkGateConfig(
            manifest_path=_string(gate_data.get("manifest_path"), "benchmark_gate.manifest_path"),
            require_qualification_pass=gate_data.get("require_qualification_pass") is True,
            default_run_benchmark=gate_data.get("default_run_benchmark") is True,
        ),
        source_path=path,
        canonical_bytes=json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8"),
    )
    if not config.prior_local_runtime_failure:
        raise ColabConfigurationError("prior local runtime-failure provenance is required")
    return config
