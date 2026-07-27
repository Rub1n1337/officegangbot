"""Unit tests for per-plan resource caps (core.limits) and the premium-aware
sanitize_rules cap."""
from core.limits import FREE_LIMITS, PREMIUM_LIMITS, limit_for, limit_error
from core.automod_rules import sanitize_rules


def test_free_and_premium_caps_present_for_every_resource():
    assert set(FREE_LIMITS) == set(PREMIUM_LIMITS)


def test_premium_never_lowers_a_free_cap():
    # Additive only — premium must be >= free for every resource.
    for res in FREE_LIMITS:
        assert PREMIUM_LIMITS[res] >= FREE_LIMITS[res]


def test_limit_for_picks_the_plan():
    assert limit_for("role_menus", premium=False) == FREE_LIMITS["role_menus"]
    assert limit_for("role_menus", premium=True) == PREMIUM_LIMITS["role_menus"]


def test_free_error_mentions_premium_and_both_caps():
    msg = limit_error("automod_rules", "custom filters", premium=False)
    assert str(FREE_LIMITS["automod_rules"]) in msg
    assert str(PREMIUM_LIMITS["automod_rules"]) in msg
    assert "Premium" in msg


def test_premium_error_is_plain_ceiling():
    msg = limit_error("automod_rules", "custom filters", premium=True)
    assert str(PREMIUM_LIMITS["automod_rules"]) in msg
    assert "Premium" not in msg


def test_sanitize_rules_default_cap_unchanged():
    rules = [{"pattern": f"word{i}"} for i in range(200)]
    assert len(sanitize_rules(rules)) == FREE_LIMITS["automod_rules"]


def test_sanitize_rules_respects_premium_cap():
    rules = [{"pattern": f"word{i}"} for i in range(200)]
    assert len(sanitize_rules(rules, PREMIUM_LIMITS["automod_rules"])) == PREMIUM_LIMITS["automod_rules"]
