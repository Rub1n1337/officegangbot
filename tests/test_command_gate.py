"""Unit tests for the per-command permission gate (core.command_gate)."""
from core.command_gate import command_allowed


def _ov(**kw):
    base = {"enabled": True, "allowed_channels": [], "ignored_channels": [], "allowed_roles": [], "ignored_roles": []}
    base.update(kw)
    return base


def test_no_override_allows():
    assert command_allowed(None, channel_id=1, role_ids=[9]) is True


def test_disabled_blocks():
    assert command_allowed(_ov(enabled=False), channel_id=1, role_ids=[9]) is False


def test_default_override_allows():
    assert command_allowed(_ov(), channel_id=1, role_ids=[9]) is True


def test_allowed_channels_restricts():
    ov = _ov(allowed_channels=[10, 11])
    assert command_allowed(ov, channel_id=10, role_ids=[]) is True
    assert command_allowed(ov, channel_id=99, role_ids=[]) is False


def test_ignored_channels_blocks():
    ov = _ov(ignored_channels=[10])
    assert command_allowed(ov, channel_id=10, role_ids=[]) is False
    assert command_allowed(ov, channel_id=11, role_ids=[]) is True


def test_allowed_roles_requires_one():
    ov = _ov(allowed_roles=[5, 6])
    assert command_allowed(ov, channel_id=1, role_ids=[6, 7]) is True
    assert command_allowed(ov, channel_id=1, role_ids=[7, 8]) is False


def test_ignored_roles_blocks_if_any_held():
    ov = _ov(ignored_roles=[5])
    assert command_allowed(ov, channel_id=1, role_ids=[5, 9]) is False
    assert command_allowed(ov, channel_id=1, role_ids=[9]) is True


def test_channel_and_role_both_must_pass():
    ov = _ov(allowed_channels=[10], allowed_roles=[5])
    assert command_allowed(ov, channel_id=10, role_ids=[5]) is True
    assert command_allowed(ov, channel_id=10, role_ids=[9]) is False  # wrong role
    assert command_allowed(ov, channel_id=99, role_ids=[5]) is False  # wrong channel


def test_missing_channel_id_skips_channel_checks():
    ov = _ov(allowed_channels=[10])
    # e.g. a DM / no channel context — only role rules apply
    assert command_allowed(ov, channel_id=None, role_ids=[]) is True
