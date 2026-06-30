import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parent


def files_below(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


manifest = {"schema_version": "weilan_eval_fixture_manifest_v0.1", "case_id": ROOT.name, "public_files": files_below(ROOT / "public"), "contract_sha256": hashlib.sha256((ROOT / "stages.json").read_bytes()).hexdigest()}
(ROOT / "fixture-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
