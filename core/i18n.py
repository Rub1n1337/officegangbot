# core/i18n.py
"""Lightweight per-guild internationalisation.

Each locale is a flat dict of `key -> template`. Look up with `t(locale, key,
**kwargs)`; missing keys fall back to English and then to the key itself, so a
not-yet-translated string degrades gracefully instead of raising.

Keys are namespaced by feature (e.g. "warn.cannot_self"). When adding a new
string, add it to BOTH locales — tests/test_i18n.py enforces key + placeholder
parity so the two locales can't drift apart.
"""
from typing import Dict

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "ru")

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # --- language command ---
        "language.set": "✅ Language set to **English** for this server.",
        # --- shared field labels ---
        "field.user": "User",
        "field.reason": "Reason",
        "field.moderator": "Moderator",
        "field.total_warnings": "Total Warnings",
        "page.indicator": "Page {current}/{total}",
        # --- /warn ---
        "warn.cannot_self": "❌ You cannot warn yourself.",
        "warn.cannot_bot": "❌ You cannot warn bots.",
        "warn.dm_title": "⚠️ You have received a warning in {guild}",
        "warn.issued_title": "⚠️ Warning Issued",
        # --- /warnings ---
        "warnings.title": "⚠️ Warnings: {member}",
        "warnings.none": "✅ This member has no warnings.",
        "warnings.total": "Total warnings: **{count}**",
        "warnings.entry_name": "#{number} — {time} UTC",
        "warnings.entry_value": "**Reason:** {reason}\n**Moderator:** {moderator}",
        # --- /clearwarnings ---
        "warnings.cleared": "✅ Cleared **{count}** warning(s) for {member}.",
    },
    "ru": {
        # --- language command ---
        "language.set": "✅ Язык сервера установлен на **Русский**.",
        # --- shared field labels ---
        "field.user": "Пользователь",
        "field.reason": "Причина",
        "field.moderator": "Модератор",
        "field.total_warnings": "Всего предупреждений",
        "page.indicator": "Страница {current}/{total}",
        # --- /warn ---
        "warn.cannot_self": "❌ Нельзя выдать предупреждение самому себе.",
        "warn.cannot_bot": "❌ Нельзя выдавать предупреждения ботам.",
        "warn.dm_title": "⚠️ Вы получили предупреждение на сервере {guild}",
        "warn.issued_title": "⚠️ Предупреждение выдано",
        # --- /warnings ---
        "warnings.title": "⚠️ Предупреждения: {member}",
        "warnings.none": "✅ У этого участника нет предупреждений.",
        "warnings.total": "Всего предупреждений: **{count}**",
        "warnings.entry_name": "#{number} — {time} UTC",
        "warnings.entry_value": "**Причина:** {reason}\n**Модератор:** {moderator}",
        # --- /clearwarnings ---
        "warnings.cleared": "✅ Снято предупреждений: **{count}** для {member}.",
    },
}


def normalize_locale(locale: str) -> str:
    """Returns a supported locale, falling back to the default."""
    return locale if locale in TRANSLATIONS else DEFAULT_LOCALE


def t(locale: str, key: str, **kwargs) -> str:
    """Translate `key` into `locale`, formatting with kwargs.

    Falls back to English, then to the raw key. A formatting error (missing
    kwarg) returns the unformatted template rather than raising.
    """
    loc = normalize_locale(locale)
    template = TRANSLATIONS[loc].get(key)
    if template is None:
        template = TRANSLATIONS[DEFAULT_LOCALE].get(key, key)
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
