"""Classify each `lock timeout on` hit: a real runtime failure, or someone
reading/quoting the source that contains the string?

A raw hit count cannot tell those apart, and reporting the count as if it were
an incidence would overstate the finding. This probe extracts the surrounding
bytes of every hit and classifies conservatively.

Read-only. Usage: python _probe_20260801_lock_timeout_context.py <out.json>
"""
import io
import json
import os
import re
import sys

ROOT = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl"
TOKEN = "lock timeout on"
WINDOW = 420

TARGETS = [
    os.path.join(ROOT, "wake-codex-runs"),
    os.path.join(ROOT, "wake-agent-runs"),
    os.path.join(ROOT, "wake-cron.log"),
]

# markers that the hit is source code / a quotation of the implementation
SOURCE_MARKERS = (
    "raise RuntimeError",
    "WEILAN_LOCK_TIMEOUT_S",
    "msvcrt",
    "runtime_core",
    "def exclusive_file_lock",
    "last_error",
    "f\"lock timeout on",
)
# markers that the hit is an actually-raised error surfacing at runtime
RUNTIME_MARKERS = (
    "Traceback",
    "RuntimeError: lock timeout on",
    "raise RuntimeError(",
)


def iter_files():
    for target in TARGETS:
        if os.path.isfile(target):
            yield target
        elif os.path.isdir(target):
            for entry in sorted(os.listdir(target)):
                path = os.path.join(target, entry)
                if os.path.isfile(path):
                    yield path


def contexts_for(blob, pattern, encoding):
    """Yield decoded context windows around each occurrence of pattern bytes."""
    out = []
    start = 0
    while True:
        idx = blob.find(pattern, start)
        if idx < 0:
            break
        lo = max(0, idx - WINDOW)
        hi = min(len(blob), idx + len(pattern) + WINDOW)
        chunk = blob[lo:hi]
        try:
            text = chunk.decode(encoding, "replace")
        except Exception:  # noqa: BLE001
            text = repr(chunk)
        out.append({"byte_offset": idx, "context": text})
        start = idx + len(pattern)
    return out


def classify(context):
    lowered = context
    is_source = any(m in lowered for m in SOURCE_MARKERS)
    is_runtime = any(m in lowered for m in RUNTIME_MARKERS)
    if is_runtime and not is_source:
        return "runtime_error"
    if is_source and not is_runtime:
        return "source_or_quotation"
    if is_source and is_runtime:
        return "ambiguous_both_markers"
    return "unclassified"


def main():
    out_path = sys.argv[1]
    hits = []
    for path in iter_files():
        with open(path, "rb") as handle:
            blob = handle.read()
        for enc in ("utf-8", "utf-16-le"):
            pattern = TOKEN.encode(enc)
            for ctx in contexts_for(blob, pattern, enc):
                # collapse whitespace so the receipt stays readable
                squashed = re.sub(r"\s+", " ", ctx["context"]).strip()
                hits.append(
                    {
                        "path": path,
                        "encoding": enc,
                        "byte_offset": ctx["byte_offset"],
                        "class": classify(ctx["context"]),
                        "context": squashed,
                    }
                )

    tally = {}
    for hit in hits:
        tally[hit["class"]] = tally.get(hit["class"], 0) + 1

    files_by_class = {}
    for hit in hits:
        files_by_class.setdefault(hit["class"], set()).add(hit["path"])

    report = {
        "token": TOKEN,
        "window_bytes": WINDOW,
        "total_occurrences": len(hits),
        "occurrences_by_class": tally,
        "distinct_files_by_class": {
            k: sorted(v) for k, v in files_by_class.items()
        },
        "hits": hits,
    }
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({
        "total_occurrences": len(hits),
        "occurrences_by_class": tally,
        "distinct_files_by_class": {k: len(v) for k, v in files_by_class.items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
