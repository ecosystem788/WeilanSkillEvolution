LATENCY_P95_MS = 75
STORAGE_RATIO_MAX = 1.50
ROLLBACK_MAX_MS = 1000
BATCH_SIZE = 64


def canonical_event(event):
    import json
    return json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
