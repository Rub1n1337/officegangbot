"""Tests for compute_next_run() in core/schedule.py."""
from datetime import datetime, timedelta, timezone

from core.schedule import compute_next_run

NOW = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def test_one_off_does_not_repeat():
    assert compute_next_run(NOW - timedelta(hours=1), "none", NOW) is None


def test_unknown_repeat_does_not_repeat():
    assert compute_next_run(NOW - timedelta(hours=1), "monthly", NOW) is None


def test_daily_advances_one_day_when_just_fired():
    sched = NOW - timedelta(minutes=1)
    nxt = compute_next_run(sched, "daily", NOW)
    assert nxt == sched + timedelta(days=1)
    assert nxt > NOW


def test_daily_skips_missed_intervals():
    # Scheduled 3 days + a bit ago: should jump to the next future occurrence,
    # not fire three times.
    sched = NOW - timedelta(days=3, minutes=5)
    nxt = compute_next_run(sched, "daily", NOW)
    assert nxt > NOW
    assert (nxt - sched).days == 4  # 3 missed + 1 to get into the future


def test_weekly_advances_one_week():
    sched = NOW - timedelta(hours=2)
    nxt = compute_next_run(sched, "weekly", NOW)
    assert nxt == sched + timedelta(weeks=1)


def test_future_scheduled_time_is_returned_unchanged():
    future = NOW + timedelta(hours=5)
    assert compute_next_run(future, "daily", NOW) == future


def test_exact_boundary_is_pushed_to_the_future():
    # scheduled_at exactly == now -> next must be strictly after now.
    nxt = compute_next_run(NOW, "daily", NOW)
    assert nxt == NOW + timedelta(days=1)
