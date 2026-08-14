import watcher_sentinel
from watcher_sentinel import CooldownGate, DEFAULT_COOLDOWN_SECONDS


def test_default_cooldown_window_is_pinned_30s():
    # 2026-08-14 edit 2: hard cooldown default 30s, pinned as invariant.
    assert DEFAULT_COOLDOWN_SECONDS == 30.0


def test_cooldown_window_first_allowed_then_suppressed():
    gate = CooldownGate(window_seconds=30.0)
    assert gate.try_acquire(now=100.0) is True
    assert gate.try_acquire(now=110.0) is False
    assert gate.try_acquire(now=129.9) is False


def test_cooldown_boundary_exactly_at_window_allowed():
    gate = CooldownGate(window_seconds=30.0)
    assert gate.try_acquire(now=100.0) is True
    assert gate.try_acquire(now=130.0) is True


def test_cooldown_reset_clears_last_trigger():
    gate = CooldownGate(window_seconds=30.0)
    assert gate.try_acquire(now=100.0) is True
    assert gate.try_acquire(now=101.0) is False
    gate.reset()
    assert gate.last_trigger is None
    assert gate.try_acquire(now=101.0) is True


def test_cooldown_rejects_negative_window():
    try:
        CooldownGate(window_seconds=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative window must be rejected")
