from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PUBLIC_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object: {path}")
    return value


def artifact_record(root: Path, path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def compact_q7_pair(pair: dict[str, Any]) -> dict[str, Any]:
    candidate = pair["candidate_agreement"]
    bac = pair["BAC"]
    correlation = bac["correlation"]
    return {
        "paired_checkpoint_count": pair["checkpoint_population_count"],
        "candidate_agreement": {
            "comparable_pair_count": candidate[
                "candidate_identity_comparable_pair_count"
            ],
            "exact_normalized_candidate_agreement_count": candidate[
                "exact_normalized_candidate_agreement_count"
            ],
            "exact_normalized_candidate_agreement_fraction": candidate[
                "exact_normalized_candidate_agreement_fraction"
            ],
        },
        "BAC": {
            "paired_value_count": bac["paired_BAC_count"],
            "mean_absolute_difference": bac["mean_absolute_difference"],
            "median_absolute_difference": bac["median_absolute_difference"],
            "maximum_absolute_difference": bac["maximum_absolute_difference"],
            "pearson_correlation": correlation["pearson_correlation"],
            "spearman_correlation": correlation["spearman_correlation"],
        },
    }


def compact_inputs_from_artifact_root(artifact_root: Path) -> dict[str, Any]:
    outputs = artifact_root / "quantized_sandbox" / "outputs"
    required = {
        "q3_summary": outputs / "q3_summary.json",
        "q4_metrics": outputs / "q4_predictive_metrics.json",
        "q5_metrics": outputs / "q5_measurement_metrics.json",
        "q6_metrics": outputs / "q6_holdout_metrics.json",
        "q7_metrics": outputs / "q7_precision_metrics.json",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing required frozen aggregate artifact(s): " + ", ".join(missing)
        )

    q3 = read_json(required["q3_summary"])
    q5 = read_json(required["q5_metrics"])
    q6 = read_json(required["q6_metrics"])
    q7 = read_json(required["q7_metrics"])
    q3_measurement = q3["measurement_effect"]
    q5_predictive = q5["predictive_metrics_primary"]
    q6_contamination = q6["hypothesis_1_measurement_contamination"]
    q6_compute = q6["hypothesis_3_probe_compute"]
    q6_ranking = q6["hypothesis_2_correctness_ranking"]
    q7_pairs = q7["primary_precision_comparison"]["required_pairwise_metrics"]
    q7_tq1 = q7["TQ1_0_extreme_post_training_ternary_stress_test"][
        "all_scheduled_TQ1_0_probes"
    ]

    return {
        "schema_version": "1.1",
        "source_artifacts": [
            artifact_record(artifact_root, required["q3_summary"]),
            artifact_record(artifact_root, required["q4_metrics"]),
            artifact_record(artifact_root, required["q5_metrics"]),
            artifact_record(artifact_root, required["q6_metrics"]),
            artifact_record(artifact_root, required["q7_metrics"]),
        ],
        "q3": {
            "total_probes": q3_measurement["box_completed_probe_count"],
            "box_completed_before_released_termination": (
                q3_measurement["box_completed_before_termination_count"]
            ),
            "post_box_released_window_nll_share": (
                q3_measurement["post_box_nll_share_distribution"]
            ),
            "absolute_c_full_minus_c_box": (
                q3_measurement["absolute_c_full_minus_c_box_distribution"]
            ),
        },
        "q5": {
            "directly_evaluable_probe_rows": q5["primary_population"][
                "directly_evaluable_probe_rows"
            ],
            "correct_probe_rows": q5["primary_population"]["correct_probe_rows"],
            "incorrect_probe_rows": q5["primary_population"][
                "incorrect_probe_rows"
            ],
            "c_full": {
                "auroc": q5_predictive["c_full"]["auroc"],
                "auprc": q5_predictive["c_full"]["average_precision_auprc"],
            },
            "c_box_geom": {
                "auroc": q5_predictive["c_box_geom"]["auroc"],
                "auprc": q5_predictive["c_box_geom"]["average_precision_auprc"],
            },
        },
        "q6": {
            "total_probes": q6_contamination["total_probes"],
            "box_completed_before_released_termination": (
                q6_contamination["box_completed_before_released_termination_count"]
            ),
            "post_box_released_window_nll_share": (
                q6_contamination[
                    "post_box_released_window_nll_share_distribution_all_defined"
                ]
            ),
            "absolute_c_full_minus_BAC": (
                q6_contamination["absolute_c_full_minus_BAC_distribution"]
            ),
            "directly_evaluable_candidates": q6_ranking["population"]["probe_rows"],
            "correct_candidates": q6_ranking["population"]["correct"],
            "incorrect_candidates": q6_ranking["population"]["incorrect"],
            "released_probe_generated_tokens": (
                q6_compute["released_probe_generated_tokens"]
            ),
            "boundary_probe_tokens": q6_compute["BAC_boundary_probe_tokens"],
            "absolute_tokens_avoided": q6_compute["absolute_tokens_avoided"],
            "percentage_probe_token_reduction": (
                q6_compute["percentage_probe_token_reduction"]
            ),
        },
        "q7": {
            "scope": "Controlled fixed-prefix precision-fidelity probes only.",
            "primary_checkpoint_count": q7["analysis_status"][
                "primary_checkpoint_count"
            ],
            "bf16_subset_checkpoint_count": q7["analysis_status"][
                "frozen_BF16_subset_checkpoint_count"
            ],
            "Q8_0_vs_Q4_K_M": compact_q7_pair(q7_pairs["Q8_0_vs_Q4_K_M"]),
            "BF16_vs_Q8_0": compact_q7_pair(q7_pairs["BF16_vs_Q8_0"]),
            "BF16_vs_Q4_K_M": compact_q7_pair(q7_pairs["BF16_vs_Q4_K_M"]),
            "TQ1_0_extreme_stress": {
                "scheduled_probe_count": q7_tq1["expected_checkpoint_count"],
                "outer_box_closed_count": q7_tq1["outer_box_closed_count"],
                "malformed_probe_count": q7_tq1["malformed_probe_count"],
                "candidate_identity_available_count": q7_tq1[
                    "candidate_identity_available_count"
                ],
            },
        },
    }


def build_summary(inputs: dict[str, Any]) -> dict[str, Any]:
    for key in ("source_artifacts", "q3", "q5", "q6", "q7"):
        if key not in inputs:
            raise KeyError(f"Compact input is missing required key: {key}")
    q3 = inputs["q3"]
    q5 = inputs["q5"]
    q6 = inputs["q6"]
    q7 = inputs["q7"]

    return {
        "release_scope": (
            "Compact public aggregate of the frozen Q3-Q7 reasoning-confidence "
            "audit; not a faithful BF16 reproduction or a validated new method."
        ),
        "status_labels": {
            "ESTABLISHED IN CURRENT SANDBOX": (
                "Directly supported by recorded frozen sandbox artifacts within "
                "their stated measurement and precision scope."
            ),
            "EXPLORATORY": (
                "Development-trace observation requiring independent evidence."
            ),
            "ONGOING": (
                "The next risk-controlled study is a frozen protocol, not a result."
            ),
        },
        "provenance": {
            "model": "Qwen/Qwen3-4B",
            "model_revision": "1cfa9a7208912126459214e8b04321603b3df60c",
            "q4_k_m_sha256": (
                "069872af6a408c4d3998f6ecd15b0028ac3b38839be6dd98f80a84493e9c0a20"
            ),
            "q8_0_sha256": (
                "0d5964f2837d157bf8d845f09b006254b85389ef4293ec0f41dd8ffeab1ab3f0"
            ),
            "bf16_anchor_sha256": (
                "89ee1fd110158671b341bf4a8d45bd4859f60ac1ef7252e89233d2492f712814"
            ),
            "llama_cpp_commit": "7798007a29a90e3053e799394da48cf53a2f8e0f",
            "codestop_commit": "b5081e7c2abe23bb1d19649421cc13522fee7c50",
        },
        "established_in_current_sandbox": {
            "q3_development_measurement_boundary": q3,
            "q6_preregistered_holdout_measurement_boundary": {
                "total_probes": q6["total_probes"],
                "box_completed_before_released_termination": (
                    q6["box_completed_before_released_termination"]
                ),
                "post_box_released_window_nll_share": (
                    q6["post_box_released_window_nll_share"]
                ),
                "absolute_c_full_minus_BAC": q6["absolute_c_full_minus_BAC"],
                "directly_evaluable_candidates": (
                    q6["directly_evaluable_candidates"]
                ),
                "correct_candidates": q6["correct_candidates"],
                "incorrect_candidates": q6["incorrect_candidates"],
            },
            "q6_counterfactual_trial_probe_accounting": {
                "released_probe_generated_tokens": (
                    q6["released_probe_generated_tokens"]
                ),
                "boundary_probe_tokens": q6["boundary_probe_tokens"],
                "absolute_tokens_avoided": q6["absolute_tokens_avoided"],
                "percentage_probe_token_reduction": (
                    q6["percentage_probe_token_reduction"]
                ),
                "interpretation": (
                    "counterfactual reduction in trial-probe generated tokens "
                    "on the Q6 holdout"
                ),
            },
            "q7_fixed_prefix_precision_fidelity": q7,
        },
        "exploratory": {"q3_q5_development_candidate_ranking": q5},
        "ongoing": {
            "risk_controlled_boundary_aligned_stopping": (
                "Protocol frozen; not executed."
            )
        },
        "source_artifacts": inputs["source_artifacts"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a compact public result summary from frozen aggregate JSON."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--artifact-root",
        type=Path,
        help="Root of a full frozen artifact tree.",
    )
    source.add_argument(
        "--input",
        type=Path,
        help="Compact input JSON path; defaults to the public-release input.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path for the compact public aggregate JSON.",
    )
    args = parser.parse_args()
    if args.artifact_root is not None:
        inputs = compact_inputs_from_artifact_root(args.artifact_root.resolve())
    else:
        input_path = args.input or (PUBLIC_ROOT / "results" / "aggregate_inputs.json")
        inputs = read_json(input_path.resolve())
    summary = build_summary(inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "sha256": sha256_file(args.output)}))


if __name__ == "__main__":
    main()
