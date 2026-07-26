"""Read-only recheck of the 2026-07-20 safety premise before landing the
.pytest_cache tree_manifest exclusion to history.

Premise being retested at TODAY's on-disk state (not trusting the 07-20 run):
  no existing artifact address is satisfied under the OLD rule and broken by
  the NEW rule.  Writes nothing.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from evolution_core import canonical_json, file_sha256, sha256_text  # noqa: E402


def manifest(root, exclude_pytest_cache):
    root = Path(root).resolve()
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if exclude_pytest_cache and ".pytest_cache" in path.parts:
            continue
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    return rows


def thash(root, exclude_pytest_cache):
    return sha256_text(canonical_json(manifest(root, exclude_pytest_cache)))


def main():
    artifacts = REPO / "artifacts"
    regressions = []
    checked = 0
    for entry in sorted(artifacts.iterdir()):
        if not entry.is_dir() or len(entry.name) != 64:
            continue
        inner = entry / "solve-with-weilan"
        root = inner if inner.is_dir() else entry
        old = thash(root, exclude_pytest_cache=False)
        new = thash(root, exclude_pytest_cache=True)
        old_ok = old == entry.name
        new_ok = new == entry.name
        checked += 1
        flag = "REGRESSION" if (old_ok and not new_ok) else "ok"
        if flag == "REGRESSION":
            regressions.append(entry.name)
        print(f"{entry.name[:12]}  old={'==' if old_ok else '!='}addr  new={'==' if new_ok else '!='}addr  {flag}")

    live = Path(r"D:\CodexData\skills\solve-with-weilan")
    if live.is_dir():
        print(f"live      old={thash(live, False)[:12]}  new={thash(live, True)[:12]}")
    else:
        print("live      (absent)")

    print(f"\nchecked={checked} regressions={len(regressions)}")
    return 1 if regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())
