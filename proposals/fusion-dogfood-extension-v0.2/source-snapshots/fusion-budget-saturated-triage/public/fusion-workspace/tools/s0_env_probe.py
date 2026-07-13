from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import platform
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch


def version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not_installed"


def write_report(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# S0 Environment Probe",
        "",
        f"- generated_at_utc: `{data['generated_at_utc']}`",
        f"- model_dir: `{data['model_dir']}`",
        f"- conclusion: `{data['conclusion']}`",
        "",
        "## Environment",
        "",
    ]
    for key, value in data["environment"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Checks", ""])
    for check in data["checks"]:
        lines.append(f"### {check['name']}")
        lines.append("")
        lines.append(f"- status: `{check['status']}`")
        if "elapsed_s" in check:
            lines.append(f"- elapsed_s: `{check['elapsed_s']}`")
        if "details" in check:
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(check["details"], ensure_ascii=False, indent=2))
            lines.append("```")
        if "error" in check:
            lines.append("")
            lines.append("```text")
            lines.append(check["error"])
            lines.append("```")
        lines.append("")
    if data.get("tok_s_initial") is not None:
        lines.extend(["## tok/s Initial", "", f"- decode_tok_s_initial: `{data['tok_s_initial']}`", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def ok(name: str, start: float, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"name": name, "status": "ok", "elapsed_s": round(time.perf_counter() - start, 3), "details": details or {}}


def fail(name: str, start: float, exc: BaseException) -> dict[str, Any]:
    return {
        "name": name,
        "status": "failed",
        "elapsed_s": round(time.perf_counter() - start, 3),
        "error": "".join(traceback.format_exception_only(type(exc), exc)).strip(),
    }


def dtype_bytes(dtype_name: str) -> int | None:
    normalized = dtype_name.replace("torch.", "").lower()
    return {
        "float32": 4,
        "f32": 4,
        "bfloat16": 2,
        "bf16": 2,
        "float16": 2,
        "fp16": 2,
    }.get(normalized)


def recurrent_state_summary(shape: list[int], dtype_name: str, linear_layers: int) -> dict[str, Any]:
    elements_per_layer = 1
    for dim in shape:
        elements_per_layer *= int(dim)
    bytes_per_element = dtype_bytes(dtype_name)
    total_bytes = elements_per_layer * linear_layers * bytes_per_element if bytes_per_element is not None else None
    return {
        "shape_per_linear_layer": shape,
        "dtype": dtype_name,
        "linear_layers": linear_layers,
        "elements_per_linear_layer": elements_per_layer,
        "bytes_total_all_linear_layers": total_bytes,
        "mib_total_all_linear_layers": (total_bytes / (1024 * 1024)) if total_bytes is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--try-full-forward", action="store_true")
    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    checks: list[dict[str, Any]] = []
    tok_s_initial = None
    config = None

    data: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_dir": str(model_dir),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": version("torch"),
            "transformers": version("transformers"),
            "safetensors": version("safetensors"),
            "numpy": version("numpy"),
            "torch_num_threads": torch.get_num_threads(),
        },
        "checks": checks,
        "tok_s_initial": None,
        "conclusion": "blocked_env",
    }

    try:
        start = time.perf_counter()
        from transformers import AutoConfig, AutoTokenizer

        config = AutoConfig.from_pretrained(model_dir, local_files_only=True)
        tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        checks.append(
            ok(
                "autoconfig_autotokenizer",
                start,
                {
                    "config_class": type(config).__name__,
                    "model_type": getattr(config, "model_type", None),
                    "architectures": getattr(config, "architectures", None),
                    "tokenizer_class": type(tokenizer).__name__,
                    "text_model_type": getattr(getattr(config, "text_config", None), "model_type", None),
                    "layer_type_counts": {
                        "linear_attention": getattr(config.text_config, "layer_types", []).count("linear_attention"),
                        "full_attention": getattr(config.text_config, "layer_types", []).count("full_attention"),
                    },
                },
            )
        )
    except Exception as exc:
        checks.append(fail("autoconfig_autotokenizer", start, exc))
        write_report(Path(args.out), data)
        return 0

    try:
        start = time.perf_counter()
        from transformers import AutoModel, AutoModelForCausalLM, AutoModelForImageTextToText

        checks.append(
            ok(
                "auto_model_mapping",
                start,
                {
                    "AutoModel": AutoModel._model_mapping[type(config)].__name__,
                    "AutoModelForCausalLM": AutoModelForCausalLM._model_mapping[type(config)].__name__,
                    "AutoModelForImageTextToText": AutoModelForImageTextToText._model_mapping[type(config)].__name__,
                },
            )
        )
    except Exception as exc:
        checks.append(fail("auto_model_mapping", start, exc))
        write_report(Path(args.out), data)
        return 0

    try:
        start = time.perf_counter()
        from transformers import DynamicCache
        from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5GatedDeltaNet

        text_config = config.text_config
        layer = Qwen3_5GatedDeltaNet(text_config, layer_idx=0).eval()
        hidden = torch.randn(1, 4, text_config.hidden_size)
        cache = DynamicCache(config=text_config)
        with torch.inference_mode():
            out = layer(hidden, cache_params=cache)
        recurrent = cache.layers[0].recurrent_states
        conv = cache.layers[0].conv_states
        recurrent_dtype = str(recurrent.dtype).replace("torch.", "")
        recurrent_shape = list(recurrent.shape)
        checks.append(
            ok(
                "cpu_linear_attention_kernel_minimal",
                start,
                {
                    "module": type(layer).__name__,
                    "output_shape": list(out.shape),
                    "recurrent_state_shape": recurrent_shape,
                    "recurrent_state_dtype": recurrent_dtype,
                    "recurrent_state_total": recurrent_state_summary(
                        recurrent_shape,
                        recurrent_dtype,
                        config.text_config.layer_types.count("linear_attention"),
                    ),
                    "conv_state_shape": list(conv.shape),
                    "conv_state_dtype": str(conv.dtype).replace("torch.", ""),
                },
            )
        )
    except Exception as exc:
        checks.append(fail("cpu_linear_attention_kernel_minimal", start, exc))
        data["conclusion"] = "blocked_no_cpu_path"
        write_report(Path(args.out), data)
        return 0

    if args.try_full_forward:
        try:
            start = time.perf_counter()
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_dir,
                local_files_only=True,
                dtype="auto",
                low_cpu_mem_usage=True,
            ).eval()
            prompt = "苹果是一种"
            inputs = tokenizer(prompt, return_tensors="pt")
            with torch.inference_mode():
                prefill = model(**inputs, use_cache=True)
                next_id = torch.argmax(prefill.logits[:, -1, :], dim=-1, keepdim=True)
                t0 = time.perf_counter()
                out = model(input_ids=next_id, past_key_values=prefill.past_key_values, use_cache=True)
                elapsed = time.perf_counter() - t0
            tok_s_initial = 1.0 / elapsed if elapsed > 0 else None
            first_linear = next(
                i for i, t in enumerate(config.text_config.layer_types) if t == "linear_attention"
            )
            recurrent = out.past_key_values.layers[first_linear].recurrent_states
            recurrent_dtype = str(recurrent.dtype).replace("torch.", "")
            recurrent_shape = list(recurrent.shape)
            checks.append(
                ok(
                    "full_checkpoint_text_forward_cpu",
                    start,
                    {
                        "model_class": type(model).__name__,
                        "prefill_input_tokens": int(inputs["input_ids"].shape[-1]),
                        "decode_tokens_measured": 1,
                        "decode_elapsed_s": elapsed,
                        "decode_tok_s_initial": tok_s_initial,
                        "first_linear_recurrent_state_shape": recurrent_shape,
                        "first_linear_recurrent_state_dtype": recurrent_dtype,
                        "recurrent_state_total": recurrent_state_summary(
                            recurrent_shape,
                            recurrent_dtype,
                            config.text_config.layer_types.count("linear_attention"),
                        ),
                    },
                )
            )
        except Exception as exc:
            checks.append(fail("full_checkpoint_text_forward_cpu", start, exc))

    has_env = all(c["status"] == "ok" for c in checks if c["name"] in {"autoconfig_autotokenizer", "auto_model_mapping"})
    has_cpu_kernel = any(c["name"] == "cpu_linear_attention_kernel_minimal" and c["status"] == "ok" for c in checks)
    full_forward = next((c for c in checks if c["name"] == "full_checkpoint_text_forward_cpu"), None)
    if not has_env:
        data["conclusion"] = "blocked_env"
    elif not has_cpu_kernel:
        data["conclusion"] = "blocked_no_cpu_path"
    elif full_forward is None:
        data["conclusion"] = "continue_without_full_forward"
    elif full_forward["status"] == "ok":
        data["conclusion"] = "continue"
    else:
        data["conclusion"] = "blocked_env"
    data["tok_s_initial"] = tok_s_initial
    write_report(Path(args.out), data)
    print(json.dumps({"out": args.out, "conclusion": data["conclusion"], "tok_s_initial": tok_s_initial}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
