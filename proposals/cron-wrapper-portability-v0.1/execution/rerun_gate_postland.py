"""Re-run the death-gate AFTER landing, without touching any repo file.

Post-landing the live target IS the post-image, so gate_portability's
PRE_IMAGE (= the live target) no longer holds the pre-image: arm 1's second
check and arm 5's mutation anchor both lose their subject.  That is a property
of where the gate sources its pre-image, not of the wrapper.

This runner tests exactly that claim: point PRE_IMAGE at the preflight sidecar
(whose sha256 == the co-signed base) and change nothing else.  If the gate then
returns to 17/17 against the landed post-image, the post-landing failure was
sourcing, not regression.

Lives outside the working tree per CONVENTION Sec.5.3.d.
"""
import hashlib
import pathlib
import sys

GATE_DIR = pathlib.Path(r"D:\WeilanSkillEvolution\proposals\cron-wrapper-portability-v0.1")
SIDECAR = pathlib.Path(__file__).resolve().parent / "run_wake_cron.base.bytes"
BASE = "eb552cc6e9e83abca0e65b7016f10538c687c7aded938840e581a83f5d769f1a"

actual = hashlib.sha256(SIDECAR.read_bytes()).hexdigest()
if actual != BASE:
    raise SystemExit(f"sidecar is not the signed base: {actual}")

sys.path.insert(0, str(GATE_DIR))
import gate_portability as gate  # noqa: E402

# The one substitution: pre-image from the sidecar, not from the live target.
gate.PRE_IMAGE = SIDECAR

sys.argv = ["gate_portability.py", "--workdir", r"D:\WeilanExec\cron-portability-gate-postland"]
gate.main()
