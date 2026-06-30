"""Tests for core/content_filter.py — AutoMod invite/link detection."""
from core.content_filter import contains_invite, first_disallowed_link, normalize_domain


def test_normalize_domain_strips_scheme_path_and_www():
    assert normalize_domain("https://www.YouTube.com/watch?v=1") == "youtube.com"
    assert normalize_domain("HTTP://Example.org/") == "example.org"
    assert normalize_domain("github.com") == "github.com"
    assert normalize_domain("  ") == ""


def test_normalized_allow_list_matches_real_links():
    # An allow-list entry pasted as a full URL still permits links to that host.
    allowed = [normalize_domain("https://github.com/anything")]
    assert first_disallowed_link("see https://github.com/x", allowed) is None


def test_detects_discord_gg_invite():
    assert contains_invite("join here discord.gg/abc123")


def test_detects_invite_with_scheme_and_www():
    assert contains_invite("https://www.discord.gg/abc123")
    assert contains_invite("https://discord.com/invite/xyz")
    assert contains_invite("discordapp.com/invite/xyz")


def test_no_invite_in_plain_text():
    assert not contains_invite("hey everyone, check the rules")
    assert not contains_invite("")


def test_disallowed_link_flags_external_url():
    bad = first_disallowed_link("scam at http://evil.example/win", [])
    assert bad == "http://evil.example/win"


def test_allowed_domain_passes():
    assert first_disallowed_link("watch https://youtube.com/x", ["youtube.com"]) is None


def test_subdomain_of_allowed_passes():
    assert first_disallowed_link("https://m.youtube.com/x", ["youtube.com"]) is None
    assert first_disallowed_link("https://www.youtube.com/x", ["youtube.com"]) is None


def test_disallowed_when_not_in_allowlist():
    bad = first_disallowed_link("https://sketchy.io/a", ["youtube.com"])
    assert bad == "https://sketchy.io/a"


def test_returns_first_disallowed_among_many():
    bad = first_disallowed_link("https://youtube.com/ok then https://bad.tld/x", ["youtube.com"])
    assert bad == "https://bad.tld/x"


def test_no_links_returns_none():
    assert first_disallowed_link("just talking, no urls here", []) is None


def test_bare_text_not_treated_as_link():
    # No scheme -> not matched, so the link rule won't false-positive on prose.
    assert first_disallowed_link("see e.g. the U.S. economy", []) is None
