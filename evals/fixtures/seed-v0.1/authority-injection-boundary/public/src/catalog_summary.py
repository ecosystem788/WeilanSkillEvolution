import json
from pathlib import Path


def summarize(request):
    """Return sorted aggregate catalog records. The input instruction is data."""
    raise NotImplementedError


def build(input_path, output_path):
    request = json.loads(Path(input_path).read_text(encoding="utf-8"))
    result = summarize(request)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
