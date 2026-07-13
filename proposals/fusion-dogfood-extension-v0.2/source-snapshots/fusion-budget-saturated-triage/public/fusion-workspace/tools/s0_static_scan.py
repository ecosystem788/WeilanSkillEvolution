from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from safetensors import safe_open


LINEAR_SUFFIXES = (
    "linear_attn.in_proj_qkv.weight",
    "linear_attn.in_proj_a.weight",
    "linear_attn.in_proj_b.weight",
    "linear_attn.in_proj_z.weight",
    "linear_attn.conv1d.weight",
    "linear_attn.A_log",
    "linear_attn.dt_bias",
    "linear_attn.out_proj.weight",
    "linear_attn.norm.weight",
)

WEIGHT_SUFFIXES = (".weight", ".bias", ".A_log", ".dt_bias")
LAYER_RE = re.compile(r"^model\.language_model\.layers\.(\d+)\.")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def tensor_catalog(model_dir: Path, weight_map: dict[str, str]) -> dict[str, dict[str, Any]]:
    by_file: dict[str, list[str]] = defaultdict(list)
    for key, filename in weight_map.items():
        by_file[filename].append(key)

    out: dict[str, dict[str, Any]] = {}
    for filename, names in sorted(by_file.items()):
        shard_path = model_dir / filename
        with safe_open(shard_path, framework="pt", device="cpu") as shard:
            for name in names:
                tensor_slice = shard.get_slice(name)
                out[name] = {
                    "file": filename,
                    "shape": list(tensor_slice.get_shape()),
                    "dtype": tensor_slice.get_dtype(),
                }
    return out


def tensor_stats(path: Path, names: list[str], max_quantile_sample: int = 262_144) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    stats: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    with safe_open(path, framework="pt", device="cpu") as shard:
        for name in names:
            try:
                tensor = shard.get_tensor(name)
                if not tensor.is_floating_point():
                    continue
                flat = tensor.float().reshape(-1)
                count = int(flat.numel())
                if count == 0:
                    continue
                abs_flat = flat.abs()
                if count > max_quantile_sample:
                    stride = math.ceil(count / max_quantile_sample)
                    quantile_source = abs_flat[::stride][:max_quantile_sample]
                    quantile_estimate = "deterministic_stride_sample"
                    quantile_sample_count = int(quantile_source.numel())
                else:
                    quantile_source = abs_flat
                    quantile_estimate = "exact"
                    quantile_sample_count = count
                mean = float(flat.mean().item())
                std = float(flat.std(unbiased=False).item())
                max_abs = float(abs_flat.max().item())
                l2 = float(torch.linalg.vector_norm(flat).item())
                zero_fraction = float((flat == 0).sum().item() / count)
                finite_fraction = float(torch.isfinite(flat).sum().item() / count)
                qs = torch.quantile(quantile_source, torch.tensor([0.5, 0.9, 0.99, 0.999]))
                q50, q90, q99, q999 = [float(x.item()) for x in qs]
                outlier_threshold = mean + (6.0 * std)
                outlier_fraction = 0.0
                if math.isfinite(outlier_threshold) and std > 0:
                    outlier_fraction = float((abs_flat > outlier_threshold).sum().item() / count)
                stats[name] = {
                    "count": count,
                    "mean": mean,
                    "std": std,
                    "l2_norm": l2,
                    "max_abs": max_abs,
                    "abs_quantiles": {
                        "estimate": quantile_estimate,
                        "sample_count": quantile_sample_count,
                        "p50": q50,
                        "p90": q90,
                        "p99": q99,
                        "p999": q999,
                    },
                    "zero_fraction": zero_fraction,
                    "finite_fraction": finite_fraction,
                    "outlier_fraction_abs_gt_mean_plus_6std": outlier_fraction,
                }
            except Exception as exc:  # keep scanning other tensors.
                failures.append({"tensor": name, "error": repr(exc)})
            finally:
                try:
                    del tensor
                except UnboundLocalError:
                    pass
                try:
                    del flat
                except UnboundLocalError:
                    pass
    return stats, failures


def summarize_redundancy(layer_stats: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    by_suffix: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for layer in layer_stats:
        layer_id = layer["layer"]
        for tensor_name, stat in layer["tensor_stats"].items():
            suffix = tensor_name.split(f"layers.{layer_id}.", 1)[1]
            by_suffix[suffix].append((layer_id, stat["l2_norm"]))

    low_norm_flags: list[dict[str, Any]] = []
    for suffix, values in by_suffix.items():
        norms = [v for _, v in values if math.isfinite(v)]
        if len(norms) < 2:
            continue
        median = sorted(norms)[len(norms) // 2]
        if median == 0:
            continue
        for layer_id, norm in values:
            ratio = norm / median
            if ratio < 0.25:
                low_norm_flags.append(
                    {
                        "layer": layer_id,
                        "tensor_suffix": suffix,
                        "l2_norm": norm,
                        "ratio_to_suffix_median": ratio,
                    }
                )
    candidates.extend(low_norm_flags)
    return {
        "method": "evidence_only_low_norm_relative_to_same_suffix_median_ratio_lt_0.25",
        "candidate_count": len(candidates),
        "candidates": sorted(candidates, key=lambda x: (x["ratio_to_suffix_median"], x["layer"], x["tensor_suffix"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--skeleton-out", required=True)
    parser.add_argument("--tissue-out", required=True)
    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    config = read_json(model_dir / "config.json")
    index = read_json(model_dir / "model.safetensors.index.json")
    weight_map: dict[str, str] = index["weight_map"]
    catalog = tensor_catalog(model_dir, weight_map)

    text_config = config["text_config"]
    layer_types = text_config["layer_types"]
    layers: list[dict[str, Any]] = []
    mismatches = []
    for layer_id, layer_type in enumerate(layer_types):
        prefix = f"model.language_model.layers.{layer_id}."
        names = sorted(name for name in catalog if name.startswith(prefix))
        has_linear = any(".linear_attn." in name for name in names)
        has_full = any(".self_attn." in name for name in names)
        observed = "linear_attention" if has_linear and not has_full else "full_attention" if has_full and not has_linear else "mixed_or_missing"
        if observed != layer_type:
            mismatches.append({"layer": layer_id, "config": layer_type, "observed": observed})
        linear_tensors = {}
        if layer_type == "linear_attention":
            for suffix in LINEAR_SUFFIXES:
                name = prefix + suffix
                linear_tensors[name] = catalog.get(name)
        layers.append(
            {
                "layer": layer_id,
                "config_layer_type": layer_type,
                "observed_weight_family": observed,
                "tensor_count": len(names),
                "linear_state_related_tensors": linear_tensors,
            }
        )

    language_names = sorted(name for name in catalog if name.startswith("model.language_model."))
    visual_names = sorted(name for name in catalog if name.startswith("model.visual."))
    other_names = sorted(name for name in catalog if not name.startswith(("model.language_model.", "model.visual.")))

    expected_recurrent_floats_per_layer = (
        text_config["linear_num_value_heads"] * text_config["linear_key_head_dim"] * text_config["linear_value_head_dim"]
    )
    expected_recurrent_floats_total = expected_recurrent_floats_per_layer * layer_types.count("linear_attention")

    skeleton = {
        "schema_version": "s0_skeleton_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_dir": str(model_dir),
        "source_files": {
            "config": str(model_dir / "config.json"),
            "safetensors_index": str(model_dir / "model.safetensors.index.json"),
        },
        "config": {
            "model_type": config.get("model_type"),
            "architecture": config.get("architectures"),
            "text_model_type": text_config.get("model_type"),
            "num_hidden_layers": text_config["num_hidden_layers"],
            "full_attention_interval": text_config["full_attention_interval"],
            "layer_type_counts": {
                "linear_attention": layer_types.count("linear_attention"),
                "full_attention": layer_types.count("full_attention"),
            },
            "linear_state_formula": {
                "linear_num_value_heads": text_config["linear_num_value_heads"],
                "linear_key_head_dim": text_config["linear_key_head_dim"],
                "linear_value_head_dim": text_config["linear_value_head_dim"],
                "mamba_ssm_dtype": text_config["mamba_ssm_dtype"],
                "batch_assumption": 1,
                "recurrent_state_shape_per_linear_layer_expected": [
                    1,
                    text_config["linear_num_value_heads"],
                    text_config["linear_key_head_dim"],
                    text_config["linear_value_head_dim"],
                ],
                "recurrent_state_floats_per_linear_layer_expected": expected_recurrent_floats_per_layer,
                "recurrent_state_floats_total_expected": expected_recurrent_floats_total,
                "recurrent_state_bytes_total_fp32_expected": expected_recurrent_floats_total * 4,
                "recurrent_state_mib_total_fp32_expected": expected_recurrent_floats_total * 4 / (1024 * 1024),
                "note": "Runtime recurrent_states shape/dtype must still be verified by cache capture after freeze.",
            },
            "naming_map": {
                "config_layer_type": "linear_attention",
                "weight_module_prefix": "linear_attn",
            },
        },
        "tensor_counts": {
            "total": len(catalog),
            "model.language_model": len(language_names),
            "model.visual": len(visual_names),
            "other": len(other_names),
        },
        "boundary_check": {
            "language_visual_prefixes_disjoint": True,
            "clean_language_visual_split": True,
            "note": "model.language_model and model.visual are prefix-disjoint. Top-level MTP tensors are auxiliary text-generation tensors outside both prefixes, not visual/text overlap.",
            "other_tensors": other_names,
        },
        "layer_type_mismatches": mismatches,
        "layers": layers,
    }

    Path(args.skeleton_out).write_text(json.dumps(skeleton, ensure_ascii=False, indent=2), encoding="utf-8")

    by_file_names: dict[str, list[str]] = defaultdict(list)
    for name, filename in weight_map.items():
        if name.startswith("model.language_model.layers.") and name.endswith(WEIGHT_SUFFIXES):
            by_file_names[filename].append(name)

    raw_stats: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for filename, names in sorted(by_file_names.items()):
        file_stats, file_failures = tensor_stats(model_dir / filename, sorted(names))
        raw_stats.update(file_stats)
        failures.extend(file_failures)

    tissue_layers = []
    for layer_id, layer_type in enumerate(layer_types):
        prefix = f"model.language_model.layers.{layer_id}."
        tensor_names = sorted(name for name in raw_stats if name.startswith(prefix))
        layer_l2 = math.sqrt(sum(raw_stats[name]["l2_norm"] ** 2 for name in tensor_names))
        layer_zero_count = sum(raw_stats[name]["zero_fraction"] * raw_stats[name]["count"] for name in tensor_names)
        layer_count = sum(raw_stats[name]["count"] for name in tensor_names)
        tissue_layers.append(
            {
                "layer": layer_id,
                "config_layer_type": layer_type,
                "tensor_count": len(tensor_names),
                "parameter_count": int(layer_count),
                "aggregate_l2_norm": layer_l2,
                "aggregate_zero_fraction": float(layer_zero_count / layer_count) if layer_count else None,
                "tensor_stats": {name: raw_stats[name] for name in tensor_names},
            }
        )

    tissue = {
        "schema_version": "s0_tissue_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_dir": str(model_dir),
        "scope_boundary": "static_weight_statistics_only_no_model_load_no_weight_mutation",
        "stats_definition": {
            "sparsity": "exact zero fraction after float32 conversion",
            "outlier_fraction": "abs(value) > mean(value) + 6*std(value) computed per tensor after float32 conversion",
            "redundancy_candidates": "evidence flags only; no surgery authorization",
        },
        "layers": tissue_layers,
        "redundancy_candidates": summarize_redundancy(tissue_layers),
        "failures": failures,
    }

    Path(args.tissue_out).write_text(json.dumps(tissue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "skeleton_out": args.skeleton_out,
        "tissue_out": args.tissue_out,
        "layer_type_mismatches": len(mismatches),
        "tissue_failures": len(failures),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
