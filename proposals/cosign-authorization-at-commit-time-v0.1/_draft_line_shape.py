# 用被钉为不变量的机检器自带口径算第五件（增行/删行），不另造实现。
import importlib.util, hashlib, json, pathlib

CHK = pathlib.Path("proposals/cosign-bytewise-binding-v0.1/verify_binding.py")
spec = importlib.util.spec_from_file_location("verify_binding", CHK)
vb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vb)

base = open("CHARTER.md", "rb").read()
final = open("proposals/cosign-authorization-at-commit-time-v0.1/CHARTER.proposed.md", "rb").read()

d = vb.line_delta(base, final)
print(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True))
print("base sha256 ", hashlib.sha256(base).hexdigest())
print("final sha256", hashlib.sha256(final).hexdigest())
