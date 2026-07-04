# core/db_manager.py
"""Async PostgreSQL database manager (asyncpg connection pool).

The query methods are organised into domain mixins under ``core/db/`` and
composed here into a single ``DatabaseManager`` facade, so every existing
``bot.db.<method>()`` call site keeps working unchanged.
"""
from core.db.base import _BaseDB
from core.db.settings import _SettingsMixin, ALLOWED_GUILD_SETTINGS
from core.db.levels import _LevelsMixin
from core.db.moderation import _ModerationMixin
from core.db.reactions import _ReactionsMixin
from core.db.scheduled import _ScheduledMixin
from core.db.automod import _AutomodMixin
from core.db.tickets import _TicketsMixin
from core.db.analytics import _AnalyticsMixin
from core.db.appeals import _AppealsMixin

__all__ = ["DatabaseManager", "ALLOWED_GUILD_SETTINGS"]


class DatabaseManager(
    _BaseDB,
    _SettingsMixin,
    _LevelsMixin,
    _ModerationMixin,
    _ReactionsMixin,
    _ScheduledMixin,
    _AutomodMixin,
    _TicketsMixin,
    _AnalyticsMixin,
    _AppealsMixin,
):
    """Async PostgreSQL manager with connection pooling via asyncpg.
    Initialize once at bot startup via ``connect()``, close the pool via
    ``close()``. Query methods live in the domain mixins under ``core/db/``.
    """
