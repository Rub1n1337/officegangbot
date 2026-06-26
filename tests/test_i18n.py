"""Tests for the i18n translator (core/i18n.py).

The key guarantees: the two locales never drift (same keys, same placeholders),
unknown keys/locales degrade gracefully, and formatting works.
"""
import string

from core.i18n import TRANSLATIONS, SUPPORTED_LOCALES, DEFAULT_LOCALE, t, normalize_locale


def _placeholders(template: str) -> set:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_default_locale_is_supported():
    assert DEFAULT_LOCALE in TRANSLATIONS
    assert set(SUPPORTED_LOCALES) == set(TRANSLATIONS.keys())


def test_all_locales_have_the_same_keys():
    en_keys = set(TRANSLATIONS["en"])
    for loc, table in TRANSLATIONS.items():
        assert set(table) == en_keys, f"locale '{loc}' key set differs from 'en'"


def test_placeholders_match_across_locales():
    # A key must use the same {placeholders} in every locale, otherwise
    # t(loc, key, **kwargs) would format inconsistently.
    for key, en_template in TRANSLATIONS["en"].items():
        en_ph = _placeholders(en_template)
        for loc, table in TRANSLATIONS.items():
            assert _placeholders(table[key]) == en_ph, f"placeholder mismatch for '{key}' in '{loc}'"


def test_translation_returns_locale_specific_string():
    assert t("ru", "warn.cannot_bot") == TRANSLATIONS["ru"]["warn.cannot_bot"]
    assert t("en", "warn.cannot_bot") == TRANSLATIONS["en"]["warn.cannot_bot"]


def test_unknown_locale_falls_back_to_english():
    assert t("de", "warn.cannot_bot") == TRANSLATIONS["en"]["warn.cannot_bot"]


def test_unknown_key_returns_key():
    assert t("en", "nope.not_a_key") == "nope.not_a_key"


def test_formatting_applies_kwargs():
    assert t("en", "page.indicator", current=2, total=5) == "Page 2/5"
    assert t("ru", "page.indicator", current=2, total=5) == "Страница 2/5"


def test_missing_format_kwarg_does_not_raise():
    # Returns the unformatted template rather than blowing up.
    assert "{current}" in t("en", "page.indicator")


def test_normalize_locale():
    assert normalize_locale("ru") == "ru"
    assert normalize_locale("xx") == DEFAULT_LOCALE
