"""Tests for core/role_menu.build_menu_body."""
from core.role_menu import build_menu_body


def test_body_with_description_and_roles():
    body = build_menu_body("Pick your roles", [("🔴", "@Red"), ("🟢", "@Green")])
    assert body == "Pick your roles\n🔴 — @Red\n🟢 — @Green"


def test_body_without_description():
    body = build_menu_body("", [("🔴", "@Red")])
    assert body == "🔴 — @Red"


def test_empty_falls_back_to_placeholder():
    assert build_menu_body("", []) == "React below to pick up a role."


def test_whitespace_description_is_ignored():
    assert build_menu_body("   ", [("✅", "@A")]) == "✅ — @A"
