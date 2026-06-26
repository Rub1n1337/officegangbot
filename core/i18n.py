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
        # --- levels ---
        "levelup.title": "⭐ Level Up!",
        "levelup.desc": "🎉 {mention} reached **Level {level}**!",
        "rank.title": "⭐ {member}'s Rank",
        "rank.level": "Level",
        "rank.total_xp": "Total XP",
        "rank.progress": "Progress to Next Level",
        "rank.requested_by": "Requested by {user}",
        "leaderboard.title": "🏆 XP Leaderboard",
        "leaderboard.empty": "❌ No XP data found for this server.",
        "leaderboard.footer": "Page {current}/{total} • Requested by {user}",
        "leaderboard.row": "{medal} **{name}** — Level {level} | {xp} XP",
        "setlevelrole.invalid": "❌ Level must be at least 1.",
        "setlevelrole.set_title": "✅ Level Role Set",
        "setlevelrole.set_desc": "Members who reach **Level {level}** will receive {role}.",
        # --- filter ---
        "filter.deleted": "{mention}, your message contained inappropriate language and was deleted.",
        "filter.toggle_on": "✅ The profanity filter has been **enabled**.",
        "filter.toggle_off": "✅ The profanity filter has been **disabled**.",
        "filter.add_exists": "The word `{word}` is already in the filter.",
        "filter.added": "✅ The word `{word}` has been added to the filter.",
        "filter.defaults_all": "✅ All default profanities are already in your filter list.",
        "filter.defaults_added": "✅ Added **{count}** new words from the default profanity list to your filter.",
        "filter.not_found": "The word `{word}` is not in the filter.",
        "filter.removed": "✅ The word `{word}` has been removed from the filter.",
        "filter.list_empty": "There are no words in the filter.",
        "filter.list_title": "🚫 Filtered Words",
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
        # --- levels ---
        "levelup.title": "⭐ Новый уровень!",
        "levelup.desc": "🎉 {mention} достиг **уровня {level}**!",
        "rank.title": "⭐ Ранг {member}",
        "rank.level": "Уровень",
        "rank.total_xp": "Всего опыта",
        "rank.progress": "Прогресс до следующего уровня",
        "rank.requested_by": "Запросил {user}",
        "leaderboard.title": "🏆 Таблица лидеров по опыту",
        "leaderboard.empty": "❌ На этом сервере пока нет данных об опыте.",
        "leaderboard.footer": "Страница {current}/{total} • Запросил {user}",
        "leaderboard.row": "{medal} **{name}** — ур. {level} | {xp} опыта",
        "setlevelrole.invalid": "❌ Уровень должен быть не меньше 1.",
        "setlevelrole.set_title": "✅ Роль за уровень установлена",
        "setlevelrole.set_desc": "Участники, достигшие **уровня {level}**, получат {role}.",
        # --- filter ---
        "filter.deleted": "{mention}, твоё сообщение содержало недопустимую лексику и было удалено.",
        "filter.toggle_on": "✅ Фильтр нецензурной лексики **включён**.",
        "filter.toggle_off": "✅ Фильтр нецензурной лексики **выключен**.",
        "filter.add_exists": "Слово `{word}` уже есть в фильтре.",
        "filter.added": "✅ Слово `{word}` добавлено в фильтр.",
        "filter.defaults_all": "✅ Все стандартные нецензурные слова уже в вашем фильтре.",
        "filter.defaults_added": "✅ Добавлено **{count}** новых слов из стандартного списка в ваш фильтр.",
        "filter.not_found": "Слова `{word}` нет в фильтре.",
        "filter.removed": "✅ Слово `{word}` удалено из фильтра.",
        "filter.list_empty": "В фильтре нет слов.",
        "filter.list_title": "🚫 Слова в фильтре",
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
