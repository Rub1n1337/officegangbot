"""Tests for core/observability.py — RPC metrics math and alert cooldowns."""
import asyncio

from core.observability import RpcMetrics, AlertManager


# --- RpcMetrics -------------------------------------------------------------

def test_record_and_snapshot_basics():
    m = RpcMetrics()
    m.record("get_feature", 100, ok=True)
    m.record("get_feature", 300, ok=True)
    m.record("update_feature", 500, ok=False)
    snap = m.snapshot()
    assert snap["total"]["count"] == 3
    assert snap["total"]["errors"] == 1
    assert snap["actions"]["get_feature"]["count"] == 2
    assert snap["actions"]["get_feature"]["errors"] == 0
    assert snap["actions"]["get_feature"]["avg_ms"] == 200.0
    assert snap["actions"]["update_feature"]["errors"] == 1


def test_error_rate():
    m = RpcMetrics()
    for i in range(4):
        m.record("x", 10, ok=(i != 0))
    assert m.snapshot()["total"]["error_rate"] == 0.25


def test_empty_snapshot():
    snap = RpcMetrics().snapshot()
    assert snap["total"] == {
        "count": 0, "errors": 0, "error_rate": 0.0, "p50_ms": 0.0, "p95_ms": 0.0,
    }
    assert snap["actions"] == {}


def test_percentile_nearest_rank():
    assert RpcMetrics.percentile([], 95) == 0.0
    assert RpcMetrics.percentile([42], 95) == 42.0
    values = list(range(1, 101))  # 1..100
    assert RpcMetrics.percentile(values, 50) == 51  # nearest-rank on 0-based index
    assert RpcMetrics.percentile(values, 95) == 95
    assert RpcMetrics.percentile(values, 100) == 100


def test_recent_window_bounded():
    m = RpcMetrics(window=10, per_action_window=5)
    for i in range(100):
        m.record("a", i, ok=True)
    assert len(m._recent) == 10
    assert len(m._per_action["a"]["recent"]) == 5
    assert m.snapshot()["actions"]["a"]["count"] == 100  # counters keep counting


# --- AlertManager -----------------------------------------------------------

class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_cooldown_allows_first_and_blocks_repeat():
    clock = FakeClock()
    a = AlertManager(cooldown_s=900, url="https://example.invalid/hook", now=clock)
    assert a.check_cooldown("rpc_timeout") is True
    a._mark_sent("rpc_timeout")
    clock.t = 100
    assert a.check_cooldown("rpc_timeout") is False
    clock.t = 901
    assert a.check_cooldown("rpc_timeout") is True


def test_suppressed_count_reported_once():
    clock = FakeClock()
    a = AlertManager(cooldown_s=900, url="https://example.invalid/hook", now=clock)
    a._mark_sent("k")
    for _ in range(3):
        assert a.check_cooldown("k") is False
    clock.t = 1000
    assert a.check_cooldown("k") is True
    assert a._mark_sent("k") == 3
    # counter resets after being reported
    clock.t = 2000
    assert a.check_cooldown("k") is True
    assert a._mark_sent("k") == 0


def test_keys_are_independent():
    clock = FakeClock()
    a = AlertManager(cooldown_s=900, url="https://example.invalid/hook", now=clock)
    a._mark_sent("redis_down")
    assert a.check_cooldown("redis_down") is False
    assert a.check_cooldown("rpc_timeout") is True


def test_alert_noops_without_url():
    a = AlertManager(url="", now=FakeClock())
    assert a.enabled is False
    # Must not raise and must not send.
    sent = asyncio.run(a.alert("k", "title", "desc"))
    assert sent is False


def test_explicit_url_enables():
    a = AlertManager(url="https://example.invalid/hook")
    assert a.enabled is True
