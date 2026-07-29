"""Targeted read-only check: does the publication closure carry the three
privacy items the community has explicitly ring-fenced?

  1. the observer's ID-photo path / the word for it,
  2. the local redaction private-strings file (must stay gitignored),
  3. image blobs of any kind.

This asks a question scan_push_manifest.py does not ask; `clean=true` there is
only about configured secret shapes.
"""
import json
import io
import re
import subprocess

REPO = "D:/WeilanSkillEvolution"
MANIFEST = ("D:/WeilanSkillEvolution/proposals/charter-daily-push-v0.1/"
            "_scan_claude_20260730.json")

TARGETS = {
    "id_photo_word": "\u767b\u8bb0\u7167",           # 登记照
    "photo_dir": "\u4e2d\u56fd\u519c\u5927",         # 中国农大
    "transfer_dir": "D:\\\u8f6c\u79fb",              # D:\转移
    "redaction_private_file": "redaction-private-strings.local",
    "chorus": "\u7267\u6b4c\u5408\u5531\u56e2",      # 牧歌合唱团
}


def cat(oid):
    return subprocess.run(["git", "-C", REPO, "cat-file", "blob", oid],
                          capture_output=True).stdout


def main():
    d = json.load(io.open(MANIFEST, encoding="utf-8"))
    blobs = [m for m in d["manifest"] if m["object_type"] == "blob"]
    hits = {k: [] for k in TARGETS}
    for m in blobs:
        path = (m.get("path_hints") or ["<no-hint>"])[0]
        text = cat(m["object_id"]).decode("utf-8", "replace")
        for name, needle in TARGETS.items():
            start = 0
            while True:
                i = text.find(needle, start)
                if i < 0:
                    break
                hits[name].append({"path": path,
                                   "line": text.count("\n", 0, i) + 1})
                start = i + 1
    # tracked-image census over the whole tree at HEAD, not just the closure
    tracked = subprocess.run(
        ["git", "-C", REPO, "ls-files"], capture_output=True).stdout.decode(
        "utf-8", "replace").splitlines()
    img_re = re.compile(r"\.(png|jpg|jpeg|gif|webp|bmp|heic)$", re.I)
    tracked_images = [p for p in tracked if img_re.search(p)]
    untracked = subprocess.run(
        ["git", "-C", REPO, "ls-files", "--others"], capture_output=True
    ).stdout.decode("utf-8", "replace").splitlines()
    untracked_images = [p for p in untracked if img_re.search(p)]
    ignored = subprocess.run(
        ["git", "-C", REPO, "ls-files", "--others", "--ignored",
         "--exclude-standard"], capture_output=True
    ).stdout.decode("utf-8", "replace").splitlines()
    ignored_images = [p for p in ignored if img_re.search(p)]

    print(json.dumps({
        "manifest_digest": d["manifest_digest"],
        "closure_blob_count": len(blobs),
        "target_hit_counts": {k: len(v) for k, v in hits.items()},
        "target_hits": {k: v[:10] for k, v in hits.items() if v},
        "tracked_images_at_head": tracked_images,
        "untracked_not_ignored_images": untracked_images,
        "ignored_images_count": len(ignored_images),
        "ignored_images_sample": ignored_images[:10],
        "redaction_private_file_tracked": [
            p for p in tracked if "redaction-private-strings" in p],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
