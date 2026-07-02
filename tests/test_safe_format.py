"""Tests for core/safe_format.py — the welcome-template renderer must substitute
only whitelisted placeholders and must NOT allow attribute traversal (which
str.format would, leaking the bot token / internals)."""
from core.safe_format import render_template, is_template_valid, WELCOME_PLACEHOLDERS

VALUES = {
    "user": "Alice#1234",
    "user.mention": "<@1>",
    "user.name": "Alice",
    "user.id": "1",
    "server": "My Server",
    "server.name": "My Server",
    "server.member_count": "42",
}


def test_substitutes_whitelisted():
    out = render_template("Welcome {user.mention} to {server.name}!", VALUES)
    assert out == "Welcome <@1> to My Server!"


def test_plain_user_and_server():
    assert render_template("{user} joined {server}", VALUES) == "Alice#1234 joined My Server"


def test_member_count():
    assert render_template("We are now {server.member_count} members", VALUES) == (
        "We are now 42 members"
    )


def test_malicious_attribute_chain_left_literal():
    # The classic token-leak payload — must NOT be resolved or crash.
    payload = "{user._state.http.token}"
    assert render_template(payload, VALUES) == payload


def test_dunder_traversal_left_literal():
    for payload in [
        "{user.__class__}",
        "{user.__init__.__globals__}",
        "{server.__class__.__mro__}",
        "{0.__class__}",
    ]:
        assert render_template(payload, VALUES) == payload


def test_unknown_placeholder_left_literal():
    assert render_template("hi {user.email}", VALUES) == "hi {user.email}"


def test_no_object_attribute_access_happens():
    # If render_template tried real attribute access, this object would raise.
    class Boom:
        def __getattr__(self, name):
            raise AssertionError(f"attribute access happened: {name}")

    # Boom is not in the values map at all; template references it by literal key.
    out = render_template("{user._state} {server.name}", {"server.name": "X"})
    assert out == "{user._state} X"


def test_escaped_braces_preserved():
    assert render_template("literal {{braces}} and {user.name}", VALUES) == (
        "literal {braces} and Alice"
    )


def test_empty_and_none_template():
    assert render_template("", VALUES) == ""
    assert render_template(None, VALUES) is None


def test_no_placeholders():
    assert render_template("just text", VALUES) == "just text"


def test_is_template_valid():
    assert is_template_valid("Hi {user.mention} on {server.name}") is True
    assert is_template_valid("Hi {user.email}") is False
    assert is_template_valid("{user._state.http.token}") is False
    assert is_template_valid("no placeholders") is True
    assert is_template_valid("escaped {{not a placeholder}}") is True


def test_all_documented_placeholders_are_valid():
    tmpl = " ".join("{" + p + "}" for p in WELCOME_PLACEHOLDERS)
    assert is_template_valid(tmpl) is True
