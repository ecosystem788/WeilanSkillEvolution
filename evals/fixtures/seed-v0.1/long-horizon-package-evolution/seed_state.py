import hashlib
import json
from pathlib import Path


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_seed(workspace):
    workspace=Path(workspace).resolve()
    requirements=[workspace/"requirements"/f"milestone-{i}.md" for i in (1,2,3)]
    tests=sorted((workspace/"tests").glob("test_*.py"))
    return {"schema_version":"weilan_eval_long_horizon_seed_v0.1","workspace":str(workspace),"scope":"parcel-route-evolution","control":{"state":"active","resume_requires_confirmation":False},"requirements_hashes":{str(p.relative_to(workspace)):sha(p) for p in requirements},"test_hashes":{str(p.relative_to(workspace)):sha(p) for p in tests},"initial_parent_frame":"fixture-parcel-route-root","milestones":[str(p.relative_to(workspace)) for p in requirements]}


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("workspace"); p.add_argument("output"); a=p.parse_args()
    Path(a.output).write_text(json.dumps(build_seed(a.workspace),indent=2),encoding="utf-8")
