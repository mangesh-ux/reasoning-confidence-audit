"""Lazy, local-only native Transformers runner for synthetic qualification.

Importing this module does not import Torch or Transformers.  Loading a model
is possible only after the caller explicitly invokes ``prepare``.
"""

from __future__ import annotations

import hashlib
import importlib
import time
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .models import (
    ActivationVector,
    CudaAvailability,
    MemorySnapshot,
    QualificationIntent,
    QualificationPlan,
    SyntheticExecution,
)


class RuntimeQualificationError(RuntimeError):
    """A qualification condition was not met; callers must preserve it as evidence."""


class CudaUnavailableError(RuntimeQualificationError):
    pass


class LocalModelUnavailableError(RuntimeQualificationError):
    pass


class MemoryProbe(Protocol):
    def availability(self) -> CudaAvailability:
        ...

    def reset_peak(self) -> None:
        ...

    def snapshot(self) -> MemorySnapshot:
        ...


class SyntheticRunner(Protocol):
    """Minimal runner surface used by the harness and its mock-only tests."""

    def prepare(self, plan: QualificationPlan) -> Mapping[str, Any]:
        ...

    def execute(
        self, intent: QualificationIntent, plan: QualificationPlan
    ) -> SyntheticExecution:
        ...

    def close(self) -> None:
        ...


class TorchCudaMemoryProbe:
    """CUDA inspection which tolerates a missing/inoperable Torch installation."""

    def __init__(self, device: str = "cuda") -> None:
        self.device = device

    @staticmethod
    def _load_torch() -> Any:
        return importlib.import_module("torch")

    def availability(self) -> CudaAvailability:
        try:
            torch = self._load_torch()
        except Exception as error:  # pragma: no cover - depends on host install
            return CudaAvailability(
                torch_available=False,
                cuda_available=False,
                device_count=None,
                device_name=None,
                cuda_version=None,
                reason=f"Torch import failed: {type(error).__name__}: {error}",
            )
        try:
            available = bool(torch.cuda.is_available())
        except Exception as error:  # pragma: no cover - driver-specific
            return CudaAvailability(
                torch_available=True,
                cuda_available=False,
                device_count=None,
                device_name=None,
                cuda_version=getattr(getattr(torch, "version", None), "cuda", None),
                reason=f"CUDA probe failed: {type(error).__name__}: {error}",
            )
        if not available:
            return CudaAvailability(
                torch_available=True,
                cuda_available=False,
                device_count=0,
                device_name=None,
                cuda_version=getattr(getattr(torch, "version", None), "cuda", None),
                reason="torch.cuda.is_available() returned false",
            )
        try:
            index = torch.device(self.device).index or 0
            properties = torch.cuda.get_device_properties(index)
            return CudaAvailability(
                torch_available=True,
                cuda_available=True,
                device_count=int(torch.cuda.device_count()),
                device_name=str(properties.name),
                cuda_version=getattr(getattr(torch, "version", None), "cuda", None),
                reason=None,
            )
        except Exception as error:  # pragma: no cover - driver-specific
            return CudaAvailability(
                torch_available=True,
                cuda_available=False,
                device_count=None,
                device_name=None,
                cuda_version=getattr(getattr(torch, "version", None), "cuda", None),
                reason=f"CUDA device inspection failed: {type(error).__name__}: {error}",
            )

    def reset_peak(self) -> None:
        availability = self.availability()
        if not availability.cuda_available:
            return
        torch = self._load_torch()
        torch.cuda.reset_peak_memory_stats(self.device)

    def snapshot(self) -> MemorySnapshot:
        availability = self.availability()
        if not availability.cuda_available:
            return MemorySnapshot(
                cuda_available=False,
                device=self.device,
                allocated_bytes=None,
                reserved_bytes=None,
                peak_allocated_bytes=None,
                free_bytes=None,
                total_bytes=None,
            )
        torch = self._load_torch()
        free_bytes, total_bytes = torch.cuda.mem_get_info(self.device)
        return MemorySnapshot(
            cuda_available=True,
            device=self.device,
            allocated_bytes=int(torch.cuda.memory_allocated(self.device)),
            reserved_bytes=int(torch.cuda.memory_reserved(self.device)),
            peak_allocated_bytes=int(torch.cuda.max_memory_allocated(self.device)),
            free_bytes=int(free_bytes),
            total_bytes=int(total_bytes),
        )


@dataclass
class NativeTransformersBf16Qwen3Runner:
    """Opt-in Qwen3 BF16 runner using native Transformers APIs.

    The source is deliberately local-only.  A missing local snapshot is an
    informative qualification failure, never a reason to fetch weights.
    """

    model_source: str
    device: str = "cuda"
    _torch: Any = None
    _tokenizer: Any = None
    _model: Any = None

    def prepare(self, plan: QualificationPlan) -> Mapping[str, Any]:
        if plan.required_device != self.device:
            raise RuntimeQualificationError(
                f"plan requires {plan.required_device!r}, runner uses {self.device!r}"
            )
        try:
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
        except Exception as error:
            raise RuntimeQualificationError(
                f"native Transformers dependencies unavailable: {type(error).__name__}: {error}"
            ) from error
        if not torch.cuda.is_available():
            raise CudaUnavailableError("CUDA is unavailable; BF16 model load was not attempted")
        self._torch = torch
        try:
            tokenizer = transformers.AutoTokenizer.from_pretrained(
                self.model_source,
                revision=plan.tokenizer_revision,
                local_files_only=True,
                trust_remote_code=False,
            )
            model = transformers.AutoModelForCausalLM.from_pretrained(
                self.model_source,
                revision=plan.model_revision,
                torch_dtype=torch.bfloat16,
                local_files_only=True,
                low_cpu_mem_usage=True,
                trust_remote_code=False,
            )
            model.to(torch.device(self.device))
            model.eval()
        except Exception as error:
            self.close()
            raise LocalModelUnavailableError(
                "local-only Qwen3 BF16 load failed; no download was attempted: "
                f"{type(error).__name__}: {error}"
            ) from error
        self._tokenizer = tokenizer
        self._model = model
        config = getattr(model, "config", None)
        return {
            "runner": "native_transformers_bf16_qwen3",
            "model_id": plan.model_id,
            "model_revision_requested": plan.model_revision,
            "tokenizer_revision_requested": plan.tokenizer_revision,
            "model_class": type(model).__name__,
            "transformers_version": str(getattr(transformers, "__version__", "unknown")),
            "torch_version": str(getattr(torch, "__version__", "unknown")),
            "torch_cuda_version": getattr(getattr(torch, "version", None), "cuda", None),
            "model_config_commit_hash": getattr(config, "_commit_hash", None),
            "tokenizer_commit_hash": getattr(tokenizer, "_commit_hash", None),
            "dtype": "bfloat16",
            "local_files_only": True,
            "device": self.device,
        }

    def execute(
        self, intent: QualificationIntent, plan: QualificationPlan
    ) -> SyntheticExecution:
        if self._model is None or self._tokenizer is None or self._torch is None:
            raise RuntimeQualificationError("prepare must complete before synthetic execution")
        torch = self._torch
        input_ids, attention_mask = self._render_prefix(intent, plan)
        activations = self._extract_last_token_activations(input_ids, attention_mask, plan)
        torch.manual_seed(intent.seed)
        torch.cuda.manual_seed_all(intent.seed)
        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": plan.generation.max_new_tokens,
            "min_new_tokens": plan.generation.min_new_tokens,
            "do_sample": plan.generation.do_sample,
            "use_cache": True,
            "pad_token_id": self._pad_token_id(),
        }
        if plan.generation.do_sample:
            generation_kwargs.update(
                {
                    "temperature": plan.generation.temperature,
                    "top_p": plan.generation.top_p,
                    "top_k": plan.generation.top_k,
                    "min_p": plan.generation.min_p,
                }
            )
        torch.cuda.synchronize(self.device)
        started = time.perf_counter()
        with torch.inference_mode():
            generated = self._model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                **generation_kwargs,
            )
        torch.cuda.synchronize(self.device)
        elapsed = time.perf_counter() - started
        prompt_length = int(input_ids.shape[-1])
        new_ids = tuple(int(value) for value in generated[0, prompt_length:].detach().cpu().tolist())
        decoded = self._tokenizer.decode(list(new_ids), skip_special_tokens=False)
        return SyntheticExecution(
            prompt_token_count=prompt_length,
            generated_token_ids=new_ids,
            generated_text_sha256=hashlib.sha256(decoded.encode("utf-8")).hexdigest(),
            elapsed_seconds=elapsed,
            context_limit_tokens=self._context_limit_tokens(),
            activations=activations,
            runner_provenance={
                "seed": intent.seed,
                "chat_template_kwargs": self._template_kwargs(plan),
                "activation_layer_policy": plan.activation_layer_policy,
            },
        )

    def close(self) -> None:
        model = self._model
        self._model = None
        self._tokenizer = None
        torch = self._torch
        if model is not None:
            del model
        if torch is not None:
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

    def _template_kwargs(self, plan: QualificationPlan) -> dict[str, Any]:
        # Qwen3's native chat template accepts this frozen thinking-mode flag.
        # No compatibility fallback is used because an implicit template change
        # would invalidate provenance.
        if plan.chat_template_kwargs is None:
            return {"enable_thinking": True}
        return dict(plan.chat_template_kwargs)

    def _render_prefix(
        self, intent: QualificationIntent, plan: QualificationPlan
    ) -> tuple[Any, Any]:
        torch = self._torch
        assert torch is not None and self._tokenizer is not None
        rendered = self._tokenizer.apply_chat_template(
            [{"role": "user", "content": intent.case.user_prompt}],
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            **self._template_kwargs(plan),
        )
        if isinstance(rendered, Mapping):
            input_ids = rendered["input_ids"]
            attention_mask = rendered.get("attention_mask")
        else:
            input_ids = rendered
            attention_mask = None
        if input_ids.ndim == 1:
            input_ids = input_ids.unsqueeze(0)
        prefix = self._tokenizer(
            intent.case.reasoning_prefix,
            add_special_tokens=False,
            return_tensors="pt",
        )["input_ids"]
        input_ids = torch.cat((input_ids, prefix), dim=-1).to(self.device)
        if attention_mask is None:
            attention_mask = torch.ones_like(input_ids)
        else:
            if attention_mask.ndim == 1:
                attention_mask = attention_mask.unsqueeze(0)
            prefix_mask = torch.ones_like(prefix)
            attention_mask = torch.cat((attention_mask, prefix_mask), dim=-1).to(self.device)
        return input_ids, attention_mask

    def _extract_last_token_activations(
        self, input_ids: Any, attention_mask: Any, plan: QualificationPlan
    ) -> tuple[ActivationVector, ...]:
        torch = self._torch
        assert torch is not None and self._model is not None
        with torch.inference_mode():
            output = self._model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True,
                use_cache=True,
                return_dict=True,
            )
        all_states = getattr(output, "hidden_states", None)
        if not all_states or len(all_states) < 2:
            raise RuntimeQualificationError("model did not return transformer hidden states")
        # Hugging Face causal LMs expose embeddings at position 0 and each
        # transformer block thereafter.  The plan indexes blocks from zero.
        transformer_states = all_states[1:]
        if plan.activation_layers is None:
            selected_layers = range(len(transformer_states))
        else:
            selected_layers = plan.activation_layers
        vectors: list[ActivationVector] = []
        for layer_index in selected_layers:
            if layer_index >= len(transformer_states):
                raise RuntimeQualificationError(
                    f"requested activation layer {layer_index} exceeds model depth "
                    f"{len(transformer_states)}"
                )
            vector = transformer_states[layer_index][0, -1, :]
            values = tuple(float(value) for value in vector.float().detach().cpu().tolist())
            vectors.append(
                ActivationVector(
                    layer_index=int(layer_index),
                    values=values,
                    source_dtype=str(vector.dtype).removeprefix("torch."),
                )
            )
        return tuple(vectors)

    def _pad_token_id(self) -> int | None:
        assert self._tokenizer is not None
        pad_token_id = getattr(self._tokenizer, "pad_token_id", None)
        if pad_token_id is not None:
            return int(pad_token_id)
        eos_token_id = getattr(self._tokenizer, "eos_token_id", None)
        return int(eos_token_id) if eos_token_id is not None else None

    def _context_limit_tokens(self) -> int | None:
        config = getattr(self._model, "config", None)
        for name in ("max_position_embeddings", "max_sequence_length", "n_positions"):
            value = getattr(config, name, None)
            if isinstance(value, int) and value > 0:
                return value
        return None
