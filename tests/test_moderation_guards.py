"""Unit tests for the dashboard moderation guard logic (core.permissions).

These cover the hierarchy/owner/self checks and the mute-duration clamp used by
the `moderate_member` RPC, without needing live discord objects.
"""
from core.permissions import bot_can_act_on, clamp_mute_minutes, MAX_TIMEOUT_MINUTES

BOT_ID, OWNER_ID, BOT_POS = 1, 9, 5


def _can(target_id: int, target_pos: int) -> bool:
    return bot_can_act_on(
        target_id=target_id,
        target_top_role_pos=target_pos,
        bot_id=BOT_ID,
        bot_top_role_pos=BOT_POS,
        owner_id=OWNER_ID,
    )


def test_cannot_act_on_self():
    assert _can(BOT_ID, 1) is False


def test_cannot_act_on_owner():
    assert _can(OWNER_ID, 1) is False


def test_cannot_act_on_higher_role():
    assert _can(2, BOT_POS + 1) is False


def test_cannot_act_on_equal_role():
    # Bot needs to be strictly higher.
    assert _can(2, BOT_POS) is False


def test_can_act_on_lower_role():
    assert _can(2, BOT_POS - 1) is True


def test_clamp_negative_goes_to_one():
    assert clamp_mute_minutes(-5) == 1


def test_clamp_zero_goes_to_one():
    assert clamp_mute_minutes(0) == 1


def test_clamp_caps_at_28_days():
    assert clamp_mute_minutes(10_000_000) == MAX_TIMEOUT_MINUTES


def test_clamp_passes_through_normal():
    assert clamp_mute_minutes(60) == 60


def test_clamp_non_numeric_uses_default():
    assert clamp_mute_minutes("abc") == 10
    assert clamp_mute_minutes(None) == 10
