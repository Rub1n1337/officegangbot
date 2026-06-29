"""Tests for plan_reaction_changes() in core/reaction_sync.py.

This is the diff that drives how the bot reconciles its own reactions on
reaction-role messages. The bug it fixes: changing the emoji on a reaction role
used to *add* the new reaction but leave the old one behind. The plan must mark
the old emoji for removal and the new emoji for addition on the same message.
"""
from core.reaction_sync import plan_reaction_changes


def _row(message_id, emoji, channel_id=10):
    return {"message_id": message_id, "channel_id": channel_id, "emoji": emoji}


def test_emoji_change_removes_old_and_adds_new():
    old = [_row(100, "😀")]
    new = [_row(100, "🎉")]
    plan = plan_reaction_changes(new, old)
    assert plan[100]["remove"] == {"😀"}
    assert plan[100]["add"] == {"🎉"}
    assert plan[100]["channel_id"] == 10


def test_unchanged_emoji_is_not_removed():
    old = [_row(100, "😀")]
    new = [_row(100, "😀")]
    plan = plan_reaction_changes(new, old)
    # Nothing to remove; add is idempotent so the desired emoji is still listed.
    assert plan[100]["remove"] == set()
    assert plan[100]["add"] == {"😀"}


def test_adding_first_reaction_role_has_no_removals():
    plan = plan_reaction_changes([_row(100, "✅")], [])
    assert plan[100]["add"] == {"✅"}
    assert plan[100]["remove"] == set()


def test_removing_all_roles_clears_old_reaction():
    # Feature turned off / item deleted: new is empty, old must be removed.
    plan = plan_reaction_changes([], [_row(100, "✅")])
    assert plan[100]["add"] == set()
    assert plan[100]["remove"] == {"✅"}
    # channel_id is still resolvable from the old rows so the IO can find the msg.
    assert plan[100]["channel_id"] == 10


def test_multiple_emojis_on_one_message_diff_independently():
    old = [_row(100, "😀"), _row(100, "🔴")]
    new = [_row(100, "😀"), _row(100, "🟢")]
    plan = plan_reaction_changes(new, old)
    assert plan[100]["remove"] == {"🔴"}
    assert plan[100]["add"] == {"😀", "🟢"}


def test_separate_messages_are_planned_separately():
    old = [_row(100, "😀"), _row(200, "🅰️")]
    new = [_row(100, "🎉"), _row(200, "🅰️")]
    plan = plan_reaction_changes(new, old)
    assert plan[100]["remove"] == {"😀"} and plan[100]["add"] == {"🎉"}
    # message 200 unchanged -> no removals
    assert plan[200]["remove"] == set() and plan[200]["add"] == {"🅰️"}


def test_string_coercion_of_ids_and_emoji():
    # Rows may carry string ids (from JSON) — they must compare equal to int ids.
    old = [{"message_id": "100", "channel_id": "10", "emoji": "😀"}]
    new = [{"message_id": 100, "channel_id": 10, "emoji": "🎉"}]
    plan = plan_reaction_changes(new, old)
    assert set(plan.keys()) == {100}
    assert plan[100]["remove"] == {"😀"}
    assert plan[100]["add"] == {"🎉"}


def test_no_changes_returns_empty_plan():
    assert plan_reaction_changes([], []) == {}
