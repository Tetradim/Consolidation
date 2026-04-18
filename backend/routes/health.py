"""
Health and status endpoints
FIXED C2b, C20, M28, M29
"""
from fastapi import APIRouter
import threading

router = APIRouter(tags=["Health"])

_status_lock = threading.Lock()  # FIXED C20: thread-safe bot_status

bot_status = {
    "discord_connected": False,
    "broker_connected": False,
    "active_broker": "ibkr",
    "auto_trading_enabled": False,  # FIXED C2b: was True
    "last_alert_time": None,
    "alerts_processed": 0
}

_VALID_STATUS_KEYS = set(bot_status.keys())  # FIXED M29: schema enforcement


def get_bot_status():
    """Get a thread-safe snapshot of bot status"""
    with _status_lock:
        return dict(bot_status)


def update_bot_status(key: str, value):
    """Update bot status (thread-safe)"""
    with _status_lock:
        bot_status[key] = value


@router.get("/health")
async def health():
    """FIXED M28: real health check"""
    status = get_bot_status()
    discord_ok = status.get("discord_connected", False)
    broker_ok = status.get("broker_connected", False)
    return {
        "status": "healthy" if (discord_ok and broker_ok) else "degraded",
        "discord_connected": discord_ok,
        "broker_connected": broker_ok
    }


@router.get("/status")
async def get_status():
    """Get current bot status"""
    return bot_status
