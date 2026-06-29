"""Tests for member_hierarchy_block() in core/permissions.py — the shared slash-
command hierarchy check used by both the Moderation and Timed Events cogs (so
/ban, /mute and /tempban can't drift apart).
"""
from core.permissions import (
    member_hierarchy_block,
    HIERARCHY_SELF,
    HIERARCHY_BOT_SELF,
    HIERARCHY_OWNER,
    HIERARCHY_TARGET_HIGHER,
    HIERARCHY_BOT_NOT_HIGHER,
)

AUTHOR, TARGET, BOT, OWNER = 100, 200, 1, 999


def _block(*, author_id=AUTHOR, author_pos=5, target_id=TARGET, target_pos=3, bot_pos=10):
    return member_hierarchy_block(
        author_id=author_id,
        author_top_role_pos=author_pos,
        target_id=target_id,
        target_top_role_pos=target_pos,
        bot_id=BOT,
        bot_top_role_pos=bot_pos,
        owner_id=OWNER,
    )


def test_allows_lower_target():
    assert _block() is None


def test_blocks_self():
    assert _block(target_id=AUTHOR) == HIERARCHY_SELF


def test_blocks_targeting_the_bot():
    assert _block(target_id=BOT) == HIERARCHY_BOT_SELF


def test_blocks_targeting_the_owner():
    assert _block(target_id=OWNER) == HIERARCHY_OWNER


def test_blocks_target_with_higher_role():
    assert _block(author_pos=3, target_pos=5) == HIERARCHY_TARGET_HIGHER


def test_allows_equal_role_targets():
    # Equal top role is allowed (only strictly higher is blocked).
    assert _block(author_pos=5, target_pos=5) is None


def test_owner_is_exempt_from_the_author_check():
    # The owner can act on a member with a higher role than the owner's own.
    assert _block(author_id=OWNER, author_pos=1, target_pos=8) is None


def test_blocks_when_bot_not_strictly_higher():
    # Author is fine, but the bot's top role is not above the target.
    assert _block(author_pos=9, target_pos=8, bot_pos=8) == HIERARCHY_BOT_NOT_HIGHER


def test_self_check_takes_precedence_for_owner_self_target():
    # Owner targeting themselves -> self, not owner.
    assert _block(author_id=OWNER, target_id=OWNER) == HIERARCHY_SELF
