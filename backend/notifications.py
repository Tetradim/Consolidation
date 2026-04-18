"""
Notifications module — SMS alerts via Twilio + in-app event log.

SMS is sent for:
  - Trade filled (buy or sell)
  - Trade failed / order rejected
  - Auto-shutdown triggered
  - Discord bot disconnected (detected by health monitor)
  - Correlation / position-limit block

Requires settings fields:
  sms_enabled          bool
  sms_phone_number     str  e.g. "+15551234567"
  twilio_account_sid   str
  twilio_auth_token    str
  twilio_from_number   str  e.g. "+15550000000"

Twilio is an optional dependency — if not installed the module degrades
gracefully and logs a warning instead of crashing.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Twilio import (optional) ──────────────────────────────────────────────────
try:
    from twilio.rest import Client as TwilioClient
    _TWILIO_AVAILABLE = True
except ImportError:
    _TWILIO_AVAILABLE = False
    logger.warning(
        "twilio package not installed — SMS notifications disabled. "
        "Install with: pip install twilio"
    )

# ── In-memory notification log (last 100) ─────────────────────────────────────
_notification_log: list[dict] = []
_MAX_LOG = 100


def _log_event(event_type: str, message: str, sent_sms: bool, error: Optional[str] = None):
    entry = {
        "id": str(len(_notification_log) + 1),
        "event_type": event_type,
        "message": message,
        "sent_sms": sent_sms,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _notification_log.append(entry)
    if len(_notification_log) > _MAX_LOG:
        _notification_log.pop(0)
    return entry


def get_notification_log() -> list[dict]:
    return list(reversed(_notification_log))


# ── Core send function ─────────────────────────────────────────────────────────
def _send_sms_sync(to: str, from_: str, sid: str, token: str, body: str) -> bool:
    """Blocking Twilio call — run in a thread to avoid blocking the event loop."""
    if not _TWILIO_AVAILABLE:
        return False
    try:
        client = TwilioClient(sid, token)
        msg = client.messages.create(body=body, from_=from_, to=to)
        logger.info(f"SMS sent: {msg.sid} → {to}")
        return True
    except Exception as e:
        logger.error(f"Twilio send failed: {e}")
        raise


async def send_notification(
    event_type: str,
    message: str,
    settings: dict,
) -> dict:
    """
    Send an SMS notification if configured, always log the event.

    Args:
        event_type:  short identifier e.g. "trade_filled", "trade_failed",
                     "auto_shutdown", "discord_disconnected", "correlation_block"
        message:     human-readable description of the event
        settings:    the app settings dict from the database

    Returns the log entry dict.
    """
    sms_enabled      = settings.get("sms_enabled", False)
    phone            = settings.get("sms_phone_number", "").strip()
    account_sid      = settings.get("twilio_account_sid", "").strip()
    auth_token       = settings.get("twilio_auth_token", "").strip()
    from_number      = settings.get("twilio_from_number", "").strip()

    logger.info(f"[notification] {event_type}: {message}")

    if not sms_enabled:
        return _log_event(event_type, message, sent_sms=False, error="SMS disabled")

    if not all([phone, account_sid, auth_token, from_number]):
        return _log_event(
            event_type, message, sent_sms=False,
            error="Twilio credentials incomplete — check Settings → Notifications"
        )

    sms_body = f"[TradingBot] {event_type.replace('_', ' ').upper()}\n{message}"

    try:
        # Run blocking Twilio call in a thread pool so we don't stall FastAPI
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, _send_sms_sync, phone, from_number, account_sid, auth_token, sms_body
        )
        return _log_event(event_type, message, sent_sms=True)
    except Exception as e:
        return _log_event(event_type, message, sent_sms=False, error=str(e))


# ── Typed helper functions ─────────────────────────────────────────────────────
async def notify_trade_filled(trade_id: str, ticker: str, strike: float,
                               option_type: str, quantity: int, price: float,
                               side: str, settings: dict):
    msg = (
        f"{side} {quantity}x {ticker} ${strike} {option_type} "
        f"filled @ ${price:.2f}  (trade {trade_id[:8]})"
    )
    return await send_notification("trade_filled", msg, settings)


async def notify_trade_failed(trade_id: str, ticker: str, strike: float,
                               option_type: str, reason: str, settings: dict):
    msg = (
        f"Order FAILED: {ticker} ${strike} {option_type} — "
        f"{reason}  (trade {trade_id[:8]})"
    )
    return await send_notification("trade_failed", msg, settings)


async def notify_auto_shutdown(reason: str, consecutive: int,
                                daily: int, settings: dict):
    msg = (
        f"Auto-shutdown triggered: {reason}. "
        f"Consecutive losses: {consecutive}, daily losses: {daily}. "
        f"Trading paused — review and reset manually."
    )
    return await send_notification("auto_shutdown", msg, settings)


async def notify_discord_disconnected(settings: dict):
    msg = "Discord bot disconnected. Alerts are NOT being received."
    return await send_notification("discord_disconnected", msg, settings)


async def notify_correlation_block(ticker: str, open_count: int,
                                    max_count: int, settings: dict):
    msg = (
        f"Trade BLOCKED: already {open_count} open positions in {ticker} "
        f"(max {max_count}). Adjust max_positions_per_ticker in Settings."
    )
    return await send_notification("correlation_block", msg, settings)
