"""
Enhanced Notifications
- Multiple notification channels
- Rich Discord embeds
- Trade alerts with P&L
- System status notifications
"""
import os
import logging
import aiohttp
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    TRADE_FILLED = "trade_filled"
    TRADE_FAILED = "trade_failed"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    ALERT_RECEIVED = "alert_received"
    ERROR = "error"
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    AUTO_SHUTDOWN = "auto_shutdown"


class NotificationChannel(Enum):
    DISCORD = "discord"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SMS = "sms"


@dataclass
class NotificationConfig:
    """Notification configuration"""
    # Discord
    discord_webhook_url: str = ""
    discord_bot_token: str = ""
    discord_channel_id: str = ""
    
    # Webhook
    webhook_url: str = ""
    
    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""
    
    # SMS (Twilio)
    twilio_sid: str = ""
    twilio_token: str = ""
    twilio_from: str = ""
    twilio_to: str = ""
    
    # Settings
    notify_on_trade: bool = True
    notify_on_error: bool = True
    notify_on_startup: bool = True
    notify_on_position_close: bool = True
    
    # Quiet hours
    quiet_hours_enabled: bool = False
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 7   # 7 AM
    
    def is_quiet_hours(self) -> bool:
        """Check if currently in quiet hours"""
        if not self.quiet_hours_enabled:
            return False
        
        hour = datetime.now(timezone.utc).hour
        return self.quiet_hours_start <= hour or hour < self.quiet_hours_end


class RichEmbed:
    """Rich notification embed"""
    
    def __init__(self, title: str = "", description: str = ""):
        self.title = title
        self.description = description
        self.color = 0x00FF00  # Green default
        self.fields: List[Dict] = []
        self.footer: Dict = {}
        self.timestamp: str = ""
    
    def set_color(self, color: int) -> 'RichEmbed':
        self.color = color
        return self
    
    def add_field(self, name: str, value: str, inline: bool = True) -> 'RichEmbed':
        self.fields.append({
            'name': name,
            'value': value,
            'inline': inline
        })
        return self
    
    def set_footer(self, text: str) -> 'RichEmbed':
        self.footer = {'text': text}
        return self
    
    def set_timestamp(self) -> 'RichEmbed':
        self.timestamp = datetime.now(timezone.utc).isoformat()
        return self
    
    def to_dict(self) -> dict:
        data = {
            'title': self.title,
            'description': self.description,
            'color': self.color,
        }
        
        if self.fields:
            data['fields'] = self.fields
        if self.footer:
            data['footer'] = self.footer
        if self.timestamp:
            data['timestamp'] = self.timestamp
        
        return data


class NotificationManager:
    """Manage all notifications"""
    
    def __init__(self):
        self.config = NotificationConfig()
        self._session: Optional[aiohttp.ClientSession] = None
    
    def configure(self, settings: dict) -> None:
        """Configure from settings"""
        self.config.discord_webhook_url = settings.get('discord_webhook_url', '')
        self.config.webhook_url = settings.get('webhook_url', '')
        self.config.notify_on_trade = settings.get('notify_on_trade', True)
        self.config.notify_on_error = settings.get('notify_on_error', True)
        self.config.quiet_hours_enabled = settings.get('quiet_hours_enabled', False)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
    
    # ============= NOTIFICATION METHODS =============
    
    async def notify_trade_filled(
        self,
        ticker: str,
        strike: float,
        option_type: str,
        quantity: int,
        price: float,
        side: str,
        pnl: float = 0.0,
        buffer_saved: float = 0.0
    ) -> None:
        """Send trade filled notification"""
        if self.config.is_quiet_hours():
            return
        
        color = 0x00FF00 if pnl >= 0 else 0xFF0000
        
        is_profit = pnl > 0
        emoji = "🟢" if is_profit else "🔴"
        
        embed = RichEmbed(
            title=f"{emoji} Trade {'FILLED' if side == 'BUY' else 'CLOSED'}: {ticker}",
            description=f"{quantity}x {option_type} ${strike}"
        ).set_color(color).set_timestamp().set_footer(text="TradeBot")
        
        embed.add_field("Entry Price", f"${price:.2f}", True)
        embed.add_field("Quantity", str(quantity), True)
        embed.add_field("Side", side, True)
        
        if pnl != 0:
            embed.add_field(
                "P&L", 
                f"${pnl:.2f} ({'+' if pnl >= 0 else ''}{pnl/price/100*100:.1f}%)",
                True
            )
        
        if buffer_saved > 0:
            embed.add_field("Buffer Saved", f"${buffer_saved:.4f}", True)
        
        await self._send_embed(embed, NotificationType.TRADE_FILLED)
    
    async def notify_position_closed(
        self,
        position_id: str,
        ticker: str,
        pnl: float,
        reason: str,
        exit_price: float,
        hold_time_minutes: float
    ) -> None:
        """Send position closed notification"""
        if self.config.is_quiet_hours():
            return
        
        is_profit = pnl > 0
        emoji = "✅" if is_profit else "❌"
        
        color = 0x00FF00 if is_profit else 0xFF0000
        
        embed = RichEmbed(
            title=f"{emoji} Position CLOSED: {ticker}",
            description=f"Reason: {reason}"
        ).set_color(color).set_timestamp().set_footer(text="TradeBot")
        
        embed.add_field("P&L", f"${pnl:.2f}", True)
        embed.add_field("Exit Price", f"${exit_price:.2f}", True)
        embed.add_field("Hold Time", f"{hold_time_minutes:.1f} min", True)
        
        await self._send_embed(embed, NotificationType.POSITION_CLOSED)
    
    async def notify_take_profit(
        self,
        ticker: str,
        quantity: int,
        price: float,
        profit_pct: float
    ) -> None:
        """Send take profit notification"""
        embed = RichEmbed(
            title=f"🎯 Take Profit: {ticker}",
            description=f"{quantity} contracts at ${price:.2f}"
        ).set_color(0x00FF00).set_timestamp().set_footer(text="TradeBot")
        
        embed.add_field("Profit", f"+{profit_pct:.1f}%", True)
        embed.add_field("Price", f"${price:.2f}", True)
        
        await self._send_embed(embed, NotificationType.TAKE_PROFIT)
    
    async def notify_stop_loss(
        self,
        ticker: str,
        quantity: int,
        price: float,
        loss_pct: float
    ) -> None:
        """Send stop loss notification"""
        embed = RichEmbed(
            title=f"🛑 Stop Loss: {ticker}",
            description=f"Sold {quantity} contracts at ${price:.2f}"
        ).set_color(0xFF4500).set_timestamp().set_footer(text="TradeBot")
        
        embed.add_field("Loss", f"-{loss_pct:.1f}%", True)
        embed.add_field("Price", f"${price:.2f}", True)
        
        await self._send_embed(embed, NotificationType.STOP_LOSS)
    
    async def notify_error(
        self,
        error_type: str,
        message: str,
        details: str = ""
    ) -> None:
        """Send error notification"""
        embed = RichEmbed(
            title=f"⚠️ ERROR: {error_type}",
            description=message
        ).set_color(0xFF0000).set_timestamp().set_footer(text="TradeBot")
        
        if details:
            embed.add_field("Details", details[:500], False)
        
        await self._send_embed(embed, NotificationType.ERROR)
    
    async def notify_startup(self) -> None:
        """Send startup notification"""
        embed = RichEmbed(
            title="🚀 Trading Bot Started",
            description="All systems operational"
        ).set_color(0x00FF00).set_timestamp().set_footer(text="TradeBot")
        
        await self._send_embed(embed, NotificationType.STARTUP)
    
    async def notify_auto_shutdown(self, reason: str) -> None:
        """Send auto shutdown notification"""
        embed = RichEmbed(
            title="🛑 Trading Bot STOPPED",
            description=f"Reason: {reason}"
        ).set_color(0xFF0000).set_timestamp().set_footer(text="TradeBot")
        
        await self._send_embed(embed, NotificationType.AUTO_SHUTDOWN)
    
    # ============= SEND METHODS =============
    
    async def _send_embed(
        self,
        embed: RichEmbed,
        notification_type: NotificationType
    ) -> bool:
        """Send embed to all configured channels"""
        # Check if should notify
        if notification_type in [NotificationType.TRADE_FILLED, NotificationType.POSITION_CLOSED]:
            if not self.config.notify_on_trade:
                return False
        elif notification_type == NotificationType.ERROR:
            if not self.config.notify_on_error:
                return False
        
        # Send to Discord webhook
        if self.config.discord_webhook_url:
            await self._send_discord_webhook(embed)
        
        # Send to generic webhook
        if self.config.webhook_url:
            await self._send_generic_webhook(embed)
        
        return True
    
    async def _send_discord_webhook(self, embed: RichEmbed) -> bool:
        """Send to Discord webhook"""
        try:
            session = await self._get_session()
            async with session.post(
                self.config.discord_webhook_url,
                json={'embeds': [embed.to_dict()]}
            ) as resp:
                if resp.status in [200, 204]:
                    logger.info(f"[Discord] Notification sent: {embed.title}")
                    return True
                else:
                    logger.error(f"[Discord] Failed: {resp.status}")
        except Exception as e:
            logger.error(f"[Discord] Error: {e}")
        return False
    
    async def _send_generic_webhook(self, embed: RichEmbed) -> bool:
        """Send to generic webhook"""
        try:
            session = await self._get_session()
            async with session.post(
                self.config.webhook_url,
                json=embed.to_dict()
            ) as resp:
                if resp.status in [200, 204]:
                    logger.info(f"[Webhook] Notification sent: {embed.title}")
                    return True
        except Exception as e:
            logger.error(f"[Webhook] Error: {e}")
        return False


# Global notification manager
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get global notification manager"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def configure_notifications(settings: dict) -> None:
    """Configure global notifications"""
    get_notification_manager().configure(settings)