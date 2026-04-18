"""
Local OCO (One Cancels Other) Stop Loss
Creates local bracket orders when broker doesn't support OCO natively

Features:
- Creates SL order immediately
- Monitors price every X seconds
- When PT is reached, creates trailing stop
- Supports PT%, TS%, SL combinations
"""
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class OCOState(Enum):
    """OCO order state"""
    PENDING = "pending"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class OCOConfig:
    """Local OCO configuration"""
    # Profit target (percentage)
    profit_target_pct: float = 50.0
    
    # Stop loss (percentage)
    stop_loss_pct: float = 30.0
    
    # Trailing stop (percentage, activates after PT)
    trailing_stop_pct: float = 0.0
    
    # Check interval (seconds)
    check_interval: int = 10
    
    # Enable local OCO
    enabled: bool = True
    
    # Partial exit at PT
    partial_at_pt: bool = False
    partial_percentage: float = 50.0


@dataclass
class OCOOrder:
    """Local OCO order state"""
    order_id: str
    position_id: str
    ticker: str
    strike: float
    option_type: str
    quantity: int
    entry_price: float
    
    # Configuration
    config: OCOConfig = field(default_factory=OCOConfig)
    
    # State
    state: OCOState = OCOState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    
    # Target prices
    profit_target_price: float = 0.0
    stop_loss_price: float = 0.0
    trailing_stop_price: float = 0.0
    
    # Tracking
    peak_price: float = 0.0
    highest_pnl: float = 0.0
    trailing_activated: bool = False
    
    # Callbacks
    on_profit_target: Optional[Callable] = None
    on_stop_loss: Optional[Callable] = None
    on_trailing: Optional[Callable] = None
    
    def calculate_targets(self) -> None:
        """Calculate profit target and stop loss prices"""
        # Profit target
        self.profit_target_price = round(
            self.entry_price * (1 + self.config.profit_target_pct / 100),
            2
        )
        
        # Stop loss
        self.stop_loss_price = round(
            self.entry_price * (1 - self.config.stop_loss_pct / 100),
            2
        )
        
        # Trailing stop base
        if self.config.trailing_stop_pct > 0:
            self.trailing_stop_price = self.profit_target_price
        
        logger.info(
            f"[OCO] {self.ticker} PT: ${self.profit_target_price} "
            f"SL: ${self.stop_loss_price} TS: {self.config.trailing_stop_pct}%"
        )
    
    def check_exit(self, current_price: float) -> Dict:
        """
        Check if any exit condition is met
        Returns dict with exit type and details
        """
        self.peak_price = max(self.peak_price, current_price)
        
        pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        current_pnl = (current_price - self.entry_price) * self.quantity * 100
        self.highest_pnl = max(self.highest_pnl, current_pnl)
        
        result = {'action': None, 'price': current_price, 'reason': ''}
        
        # 1. Check trailing stop (if activated)
        if self.trailing_activated and self.config.trailing_stop_pct > 0:
            trailing_level = self.peak_price * (1 - self.config.trailing_stop_pct / 100)
            if current_price <= trailing_level:
                result['action'] = 'trailing_stop'
                result['reason'] = f'TS triggered: ${current_price} <= ${trailing_level}'
                self.state = OCOState.TRIGGERED
                return result
        
        # 2. Check profit target
        if current_price >= self.profit_target_price:
            if self.config.partial_at_pt and not self.trailing_activated:
                # Partial exit at PT
                result['action'] = 'partial_profit'
                result['reason'] = f'PT reached: ${current_price} >= ${self.profit_target_price}'
                result['quantity'] = int(self.quantity * self.config.partial_percentage / 100)
                result['pnl'] = (current_price - self.entry_price) * result['quantity'] * 100
                
                # Activate trailing for remaining
                self.trailing_activated = True
                self.quantity = self.quantity - result['quantity']
                self.peak_price = current_price
                return result
            elif self.config.trailing_stop_pct > 0:
                # Activate trailing stop
                self.trailing_activated = True
                self.peak_price = current_price
                logger.info(f"[OCO] Trailing activated at ${current_price}")
            else:
                result['action'] = 'profit_target'
                result['reason'] = f'PT reached: ${current_price} >= ${self.profit_target_price}'
                self.state = OCOState.COMPLETED
                return result
        
        # 3. Check stop loss
        if current_price <= self.stop_loss_price:
            result['action'] = 'stop_loss'
            result['reason'] = f'SL triggered: ${current_price} <= ${self.stop_loss_price}'
            self.state = OCOState.TRIGGERED
            return result
        
        return result


class LocalOCOManager:
    """Manages local OCO orders"""
    
    def __init__(self):
        self._active_orders: Dict[str, OCOOrder] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        self._price_callback: Optional[Callable] = None
    
    def set_price_callback(self, callback: Callable) -> None:
        """Set callback to get current price"""
        self._price_callback = callback
    
    def create_oco(
        self,
        position_id: str,
        ticker: str,
        strike: float,
        option_type: str,
        quantity: int,
        entry_price: float,
        config: OCOConfig = None,
    ) -> str:
        """Create a local OCO order"""
        if config is None:
            config = OCOConfig()
        
        order_id = f"oco_{position_id}_{datetime.now().timestamp()}"
        
        oco = OCOOrder(
            order_id=order_id,
            position_id=position_id,
            ticker=ticker,
            strike=strike,
            option_type=option_type,
            quantity=quantity,
            entry_price=entry_price,
            config=config,
        )
        oco.calculate_targets()
        oco.state = OCOState.ACTIVE
        
        self._active_orders[order_id] = oco
        
        logger.info(
            f"[OCO] Created order {order_id} for {ticker} ${strike} "
            f"Entry: ${entry_price} PT: ${oco.profit_target_price} SL: ${oco.stop_loss_price}"
        )
        
        return order_id
    
    def cancel_oco(self, order_id: str) -> bool:
        """Cancel a local OCO order"""
        if order_id in self._active_orders:
            self._active_orders[order_id].state = OCOState.CANCELLED
            del self._active_orders[order_id]
            logger.info(f"[OCO] Cancelled order {order_id}")
            return True
        return False
    
    def get_oco(self, order_id: str) -> Optional[OCOOrder]:
        """Get OCO order"""
        return self._active_orders.get(order_id)
    
    def get_active_ocos(self) -> List[OCOOrder]:
        """Get all active OCO orders"""
        return [o for o in self._active_orders.values() if o.state == OCOState.ACTIVE]
    
    def start_monitoring(self, get_price_func: Callable = None) -> None:
        """Start monitoring loop"""
        if get_price_func:
            self._price_callback = get_price_func
        
        if self._monitor_task is None or self._monitor_task.done():
            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("[OCO] Started monitoring loop")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring loop"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None
        logger.info("[OCO] Stopped monitoring loop")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self._running:
            try:
                await self._check_orders()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[OCO] Monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _check_orders(self) -> None:
        """Check all active orders"""
        active_orders = self.get_active_ocos()
        
        for oco in active_orders:
            if self._price_callback:
                # Get current price
                current_price = await self._price_callback(oco.ticker)
            else:
                # Placeholder - would need real price
                continue
            
            if current_price <= 0:
                continue
            
            # Check exits
            exit_result = oco.check_exit(current_price)
            
            if exit_result['action']:
                logger.info(
                    f"[OCO] {oco.order_id}: {exit_result['action']} - {exit_result['reason']}"
                )
                
                # Trigger callback based on action
                if exit_result['action'] == 'profit_target':
                    if oco.on_profit_target:
                        await oco.on_profit_target(oco, exit_result)
                elif exit_result['action'] == 'stop_loss':
                    if oco.on_stop_loss:
                        await oco.on_stop_loss(oco, exit_result)
                elif exit_result['action'] == 'trailing_stop':
                    if oco.on_trailing:
                        await oco.on_trailing(oco, exit_result)
                elif exit_result['action'] == 'partial_profit':
                    # Handle partial exit
                    logger.info(
                        f"[OCO] Partial profit: {exit_result.get('quantity')} contracts, "
                        f"PNL: ${exit_result.get('pnl', 0):.2f}"
                    )
    
    def get_status(self) -> Dict:
        """Get OCO status"""
        return {
            'active_count': len(self.get_active_ocos()),
            'orders': [
                {
                    'order_id': o.order_id,
                    'ticker': o.ticker,
                    'entry': o.entry_price,
                    'pt': o.profit_target_price,
                    'sl': o.stop_loss_price,
                    'state': o.state.value,
                }
                for o in self._active_orders.values()
            ]
        }


# ============= FACTORY FUNCTIONS =============

def create_local_oco(
    position_id: str,
    ticker: str,
    strike: float,
    option_type: str,
    quantity: int,
    entry_price: float,
    profit_target_pct: float = 50.0,
    stop_loss_pct: float = 30.0,
    trailing_stop_pct: float = 0.0,
    check_interval: int = 10,
) -> str:
    """Create local OCO order from parameters"""
    config = OCOConfig(
        profit_target_pct=profit_target_pct,
        stop_loss_pct=stop_loss_pct,
        trailing_stop_pct=trailing_stop_pct,
        check_interval=check_interval,
    )
    
    return _global_manager.create_oco(
        position_id=position_id,
        ticker=ticker,
        strike=strike,
        option_type=option_type,
        quantity=quantity,
        entry_price=entry_price,
        config=config,
    )


def parse_oco_string(oco_str: str) -> OCOConfig:
    """
    Parse OCO string like DiscordAlertsTrader:
    "PT1 50%TS5% SL 50%" 
    
    Format: [PT|STOP]-[X%|[TSX%]] [SL Y%]
    """
    config = OCOConfig()
    
    oco_str = oco_str.upper()
    
    # Parse PT (profit target)
    if 'PT' in oco_str:
        pt_match = None
        ts_match = None
        sl_match = None
        
        # Extract percentages
        import re
        
        # PT followed by %
        pt_match = re.search(r'PT(?:\d+)?\s*(\d+)%', oco_str)
        if pt_match:
            config.profit_target_pct = float(pt_match.group(1))
        
        # TS (trailing stop)
        ts_match = re.search(r'TS(\d+)%', oco_str)
        if ts_match:
            config.trailing_stop_pct = float(ts_match.group(1))
        
        # SL (stop loss)
        sl_match = re.search(r'SL\s*(\d+)%', oco_str)
        if sl_match:
            config.stop_loss_pct = float(sl_match.group(1))
        
        # Check for partial
        if 'PARTIAL' in oco_str or 'PART' in oco_str:
            config.partial_at_pt = True
            config.partial_percentage = 50.0
    
    return config


# Global manager
_global_manager = LocalOCOManager()


def get_oco_manager() -> LocalOCOManager:
    """Get global OCO manager"""
    return _global_manager


# Export
__all__ = [
    'OCOConfig',
    'OCOOrder', 
    'OCOState',
    'LocalOCOManager',
    'create_local_oco',
    'parse_oco_string',
    'get_oco_manager',
]