"""Read-only: show the citation wording of the lines the proposal's self-check names."""
import io, json, sys

P = r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl\peer-chat.jsonl"
raw = io.open(P, "rb").read()
frames = raw.split(b"\x0a")
print("total frames (0x0A split):", len(frames))

for n in (2862, 2863, 3009, 3010, 3011, 3014):
    if n - 1 >= len(frames):
        print(n, "OUT OF RANGE")
        continue
    b = frames[n - 1]
    try:
        rec = json.loads(b.decode("utf-8"))
    except Exception as e:
        print(n, "unparsed", e)
        continue
    t = rec.get("text", "")
    print("=" * 70)
    print("line", n, "| from", rec.get("from"), "| time", rec.get("time"))
    print(t[:1400])
