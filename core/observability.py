"""Observability: optional Sentry error tracking, in-process RPC metrics and
Discord-webhook alerts.

Everything here is env-gated and degrades to a no-op, so the bot runs unchanged
when the variables aren't set:

- SENTRY_DSN                — enables Sentry (errors already logged via
                              logger.error(..., exc_info=True) become events).
- ALERT_WEBHOOK_URL         — a Discord webhook that receives infra alerts
                              (RPC timeouts, Redis/DB trouble, high latency).
- SENTRY_TRACES_SAMPLE_RATE — optional performance tracing (default off).
"""
import asyncio
import os
import re
import time
from collections import deque
from typing import Deque, Dict, Optional

from core.logger import logger

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------

_sentry_initialized = False


SECRET_PATTERNS = [
    # Connection strings and tokens that could ride along in log messages.
    re.compile(r"postgres(?:ql)?://[^\s'\"]+"),
    re.compile(r"rediss?://[^\s'\"]+"),
    re.compile(r"https?://[^\s'\"]*discord[^\s'\"]*token=[^\s'\"]+"),
    # Discord bot token shape (base64 id . 6 chars . 27+ chars).
    re.compile(r"[A-Za-z0-9_-]{23,28}" + re.escape(".") + r"[A-Za-z0-9_-]{6}" + re.escape(".") + r"[A-Za-z0-9_-]{20,}"),
]


def _scrub_text(text):
    if not isinstance(text, str):
        return text
    for pat in SECRET_PATTERNS:
        text = pat.sub("[redacted]", text)
    return text


def _scrub_event(event, hint):
    """Sentry before_send: mask DSNs/tokens that may leak through log lines."""
    try:
        if event.get("message"):
            event["message"] = _scrub_text(event["message"])
        logentry = event.get("logentry")
        if isinstance(logentry, dict) and logentry.get("message"):
            logentry["message"] = _scrub_text(logentry["message"])
        for crumb in (event.get("breadcrumbs") or {}).get("values", []):
            if isinstance(crumb, dict) and crumb.get("message"):
                crumb["message"] = _scrub_text(crumb["message"])
        for exc in (event.get("exception") or {}).get("values", []):
            if isinstance(exc, dict) and exc.get("value"):
                exc["value"] = _scrub_text(exc["value"])
    except Exception:
        pass  # scrubbing must never block error delivery
    return event


def init_sentry() -> bool:
    """Initializes Sentry if SENTRY_DSN is set. Safe to call more than once.

    The SDK's default logging integration turns every logger.error(...) call —
    which this codebase already makes at each failure point — into a Sentry
    event, with INFO logs kept as breadcrumbs; its FastAPI/asyncio integrations
    auto-enable, so this one init covers the bot, the cogs and the embedded API.
    """
    global _sentry_initialized
    if _sentry_initialized:
        return True
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("SENTRY_ENVIRONMENT")
            or os.getenv("RAILWAY_ENVIRONMENT_NAME")
            or "production",
            release=os.getenv("RAILWAY_GIT_COMMIT_SHA") or None,
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0")),
            before_send=_scrub_event,
        )
        _sentry_initialized = True
        logger.info("Sentry error tracking initialized.")
        return True
    except Exception as e:  # never let observability take the bot down
        logger.warning(f"Sentry init failed (continuing without it): {e}")
        return False


# ---------------------------------------------------------------------------
# RPC metrics
# ---------------------------------------------------------------------------


class RpcMetrics:
    """In-process latency/error counters for the dashboard RPC bridge.

    Bounded memory: per-action stats keep a fixed-size window of recent
    durations for percentiles; counters are plain ints. Pure Python so it can
    be unit-tested directly.
    """

    def __init__(self, window: int = 200, per_action_window: int = 50):
        self._window = window
        self._per_action_window = per_action_window
        self._per_action: Dict[str, dict] = {}
        self._recent: Deque[float] = deque(maxlen=window)
        self._started = time.time()

    def record(self, action: str, duration_ms: float, ok: bool) -> None:
        """Records one RPC call. `ok=False` means an infra failure (timeout /
        Redis down), not a domain error like "guild not found"."""
        s = self._per_action.setdefault(
            str(action),
            {"count": 0, "errors": 0, "total_ms": 0.0,
             "recent": deque(maxlen=self._per_action_window)},
        )
        s["count"] += 1
        s["total_ms"] += float(duration_ms)
        if not ok:
            s["errors"] += 1
        s["recent"].append(float(duration_ms))
        self._recent.append(float(duration_ms))

    @staticmethod
    def percentile(values, pct: float) -> float:
        """Nearest-rank percentile over a small window (0 for no data)."""
        if not values:
            return 0.0
        ordered = sorted(values)
        idx = int(round((pct / 100.0) * (len(ordered) - 1)))
        return float(ordered[max(0, min(idx, len(ordered) - 1))])

    def snapshot(self) -> dict:
        """A JSON-friendly summary: totals + per-action count/errors/avg/p95."""
        actions = {}
        total_count = 0
        total_errors = 0
        for action, s in sorted(self._per_action.items()):
            total_count += s["count"]
            total_errors += s["errors"]
            actions[action] = {
                "count": s["count"],
                "errors": s["errors"],
                "avg_ms": round(s["total_ms"] / s["count"], 1) if s["count"] else 0.0,
                "p95_ms": round(self.percentile(list(s["recent"]), 95), 1),
            }
        recent = list(self._recent)
        return {
            "uptime_s": int(time.time() - self._started),
            "total": {
                "count": total_count,
                "errors": total_errors,
                "error_rate": round(total_errors / total_count, 4) if total_count else 0.0,
                "p50_ms": round(self.percentile(recent, 50), 1),
                "p95_ms": round(self.percentile(recent, 95), 1),
            },
            "actions": actions,
        }


# ---------------------------------------------------------------------------
# Alerts (Discord webhook)
# ---------------------------------------------------------------------------

_LEVEL_COLORS = {"info": 0x5865F2, "warning": 0xE67E22, "error": 0xE74C3C}


class AlertManager:
    """Sends alert embeds to a Discord webhook, with a per-key cooldown so a
    repeating failure produces one alert (plus a suppressed-count) instead of
    spam. No-ops when ALERT_WEBHOOK_URL isn't configured."""

    def __init__(self, cooldown_s: int = 900, url: Optional[str] = None, now=time.monotonic):
        self._cooldown = cooldown_s
        self._explicit_url = url
        self._last_sent: Dict[str, float] = {}
        self._suppressed: Dict[str, int] = {}
        self._now = now

    @property
    def url(self) -> Optional[str]:
        # Read the env lazily so load_dotenv() timing doesn't matter.
        return self._explicit_url or os.getenv("ALERT_WEBHOOK_URL")

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def check_cooldown(self, key: str) -> bool:
        """True if an alert for `key` may be sent now; otherwise counts it as
        suppressed (reported with the next alert that does go out)."""
        now = self._now()
        last = self._last_sent.get(key)
        if last is not None and now - last < self._cooldown:
            self._suppressed[key] = self._suppressed.get(key, 0) + 1
            return False
        return True

    def _mark_sent(self, key: str) -> int:
        self._last_sent[key] = self._now()
        return self._suppressed.pop(key, 0)

    async def alert(self, key: str, title: str, description: str, level: str = "warning") -> bool:
        """Sends one alert embed (respecting the cooldown). Returns True if a
        webhook request was made. Never raises."""
        if not self.enabled or not self.check_cooldown(key):
            return False
        suppressed = self._mark_sent(key)
        if suppressed:
            description += f"\n*(+{suppressed} similar suppressed during cooldown)*"
        payload = {
            "embeds": [
                {
                    "title": title[:256],
                    "description": description[:4000],
                    "color": _LEVEL_COLORS.get(level, _LEVEL_COLORS["warning"]),
                    "footer": {"text": "OfficeGangBot observability"},
                }
            ]
        }
        try:
            import aiohttp  # a discord.py dependency, always present at runtime

            async with aiohttp.ClientSession() as session:
                await session.post(self.url, json=payload,
                                   timeout=aiohttp.ClientTimeout(total=10))
            return True
        except Exception as e:
            logger.warning(f"Alert webhook send failed: {e}")
            return False

    def alert_threadsafe(self, loop, key: str, title: str, description: str,
                         level: str = "warning") -> None:
        """Schedules alert() from a non-async thread (e.g. HealthMonitor)."""
        try:
            asyncio.run_coroutine_threadsafe(self.alert(key, title, description, level), loop)
        except Exception:
            pass


# Shared singletons — the api_server and the bot live in one process.
metrics = RpcMetrics()
alerts = AlertManager()
