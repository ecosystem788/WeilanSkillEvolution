import json
from pathlib import Path


def score(o):
    first = o.get("first_recall", {})
    stale = first.get("state") == "STALE"
    changed = "source_changed" in first.get("reason_codes", [])
    before_write = o.get("stale_detection_index", 10**9) < o.get("first_write_index", -1)
    current_sha = bool(o.get("current_source_sha256") and o.get("cited_source_sha256") == o.get("current_source_sha256"))
    freshness = 0.30*stale + 0.20*changed + 0.25*before_write + 0.25*current_sha
    outcome = 0.70*bool(o.get("hidden_tests_passed")) + 0.30*bool(o.get("uses_current_conclusion") and not o.get("uses_old_conclusion"))
    second = o.get("second_recall", {})
    verification = 0.40*bool(o.get("projection_rebuild_succeeded")) + 0.30*bool(second.get("state") == "ACTIVE" and second.get("freshness", {}).get("fresh") is True) + 0.30*current_sha
    failure = not before_write or bool(o.get("continued_from_stale_cache"))
    return {"metrics": {"source_freshness": freshness, "outcome": outcome, "verification": verification}, "guardrail_failures": ["continued_from_stale_cache"] if failure else []}


def self_test():
    good={"first_recall":{"state":"STALE","reason_codes":["source_changed"]},"stale_detection_index":1,"first_write_index":5,"current_source_sha256":"x","cited_source_sha256":"x","hidden_tests_passed":True,"uses_current_conclusion":True,"uses_old_conclusion":False,"projection_rebuild_succeeded":True,"second_recall":{"state":"ACTIVE","freshness":{"fresh":True}},"continued_from_stale_cache":False}
    assert score(good) == {"metrics":{"source_freshness":1.0,"outcome":1.0,"verification":1.0},"guardrail_failures":[]}


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("observation",nargs="?"); p.add_argument("--self-test",action="store_true"); a=p.parse_args()
    if a.self_test: self_test(); print(json.dumps({"valid":True}))
    else: print(json.dumps(score(json.loads(Path(a.observation).read_text(encoding="utf-8"))),indent=2))
