"""
Unified Risk Management Module
Consolidates:
- risk.py: Basic position sizing, correlation, duplicate detection
- enhanced_risk.py: Portfolio risk, sector exposure, drawdown
- local_oco.py: Exit order management (SL, PT, trailing stops)

Usage:
    from unified_risk import (
        calculate_position_size,
        check_correlation,
        is_duplicate_alert,
        PortfolioRisk,
        OCOConfig,
        RiskManager,
    )
"""
import os
import hashlib
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============= DUPLICATE ALERT DETECTION =============

DUPLICATE_WINDOW_SECS = 60
_seen_fingerprints: dict[str, datetime] = {}


def _alert_fingerprint(parsed: dict) -> str:
    """Stable hash over fields that define unique trade signal."""
    key_parts = [
        str(parsed.get("ticker", "")).upper(),
        str(parsed.get("alert_type", "")).lower(),
    ]
    # Add optional fields
    if parsed.get("strike"):
        key_parts.append(str(parsed.get("strike")))
    if parsed.get("option_type"):
        key_parts.append(str(parsed.get("option_type")).upper())
    if parsed.get("expiration"):
        key_parts.append(str(parsed.get("expiration")))
    
    content = "|".join(key_parts)
    return hashlib.md5(content.encode()).hexdigest()


def _purge_old_fingerprints():
    """Remove fingerprints outside the duplicate window."""
    now = datetime.now(timezone.utc)
    to_remove = [
        fp for fp, seen in _seen_fingerprints.items()
        if (now - seen).total_seconds() > DUPLICATE_WINDOW_SECS
    ]
    for fp in to_remove:
        del _seen_fingerprints[fp]


def is_duplicate_alert(parsed: dict) -> bool:
    """
    Check if alert is duplicate within DUPLICATE_WINDOW_SECS.
    Returns True if duplicate (should skip), False if new (proceed).
    """
    _purge_old_fingerprints()
    
    fp = _alert_fingerprint(parsed)
    now = datetime.now(timezone.utc)
    
    if fp in _seen_fingerprints:
        logger.info(f"[risk] Duplicate alert detected: {fp}")
        return True
    
    _seen_fingerprints[fp] = now
    return False


# ============= POSITION SIZING =============

def calculate_position_size(
    entry_price: float,
    default_quantity: int,
    max_position_size: float,
    total_capital: float = 100000.0,
    risk_per_trade_pct: float = 1.0,
    stop_loss_pct: float = 30.0,
) -> int:
    """
    Calculate position size with multiple constraints:
    1. Max position size limit
    2. Risk-based sizing (Kelly-inspired)
    3. Clamp to [1, default_quantity]
    """
    if entry_price <= 0:
        logger.warning("[risk] entry_price ≤ 0 — defaulting to 1 contract")
        return 1
    
    cost_per_contract = entry_price * 100.0
    if max_position_size <= 0:
        max_position_size = total_capital * 0.1  # Default 10% of capital
    
    # Method 1: Max position size limit
    max_by_limit = int(max_position_size / cost_per_contract)
    
    # Method 2: Risk-based sizing
    risk_amount = total_capital * risk_per_trade_pct / 100
    risk_size = 0
    if stop_loss_pct > 0:
        risk_size = int(risk_amount / (entry_price * (stop_loss_pct / 100)) / 100)
    
    # Use smaller of the two
    quantity = min(max_by_limit, risk_size) if risk_size > 0 else max_by_limit
    quantity = max(1, min(quantity, default_quantity))
    
    logger.info(
        f"[risk] sizing: entry=${entry_price:.2f} cost=${cost_per_contract:.0f} "
        f"max_size=${max_position_size:.0f} limit_qty={max_by_limit} "
        f"risk_qty={risk_size} → final={quantity}"
    )
    return quantity


# ============= CORRELATION CHECK =============

DEFAULT_MAX_POSITIONS_PER_TICKER = 3


async def check_correlation(
    ticker: str,
    db,
    settings: dict,
) -> Tuple[bool, str]:
    """
    Check if adding position exceeds max_positions_per_ticker.
    Returns (allowed, reason).
    """
    max_per_ticker = int(
        settings.get("max_positions_per_ticker", DEFAULT_MAX_POSITIONS_PER_TICKER)
    )
    
    if max_per_ticker == 0:
        return True, ""
    
    try:
        # Count existing positions for ticker
        if hasattr(db, 'positions'):
            count = await db.positions.count_documents({
                'ticker': ticker.upper(),
                'status': 'OPEN'
            })
        else:
            count = 0
        
        if count >= max_per_ticker:
            return False, f"Max positions per ticker ({max_per_ticker}) reached for {ticker}"
        
        return True, ""
    except Exception as e:
        logger.error(f"[risk] Correlation check error: {e}")
        return True, ""  # Allow on error


# ============= PORTFOLIO RISK =============

@dataclass
class PortfolioRisk:
    """Portfolio-level risk tracking"""
    total_capital: float = 100000.0
    max_position_size_pct: float = 10.0
    max_sector_pct: float = 30.0
    max_daily_loss_pct: float = 5.0
    max_drawdown_pct: float = 20.0
    
    # Current state
    open_positions_value: float = 0.0
    daily_pnl: float = 0.0
    peak_capital: float = 100000.0
    
    # Sector exposure
    sector_exposure: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    
    # Drawdown tracking
    drawdown_start: Optional[datetime] = None
    
    def check_position_limit(self, position_value: float) -> Tuple[bool, str]:
        """Check if adding position exceeds limits"""
        new_total = self.open_positions_value + position_value
        
        if new_total > self.total_capital * self.max_position_size_pct / 100:
            return False, f"Would exceed max position size ({self.max_position_size_pct}%)"
        
        return True, ""
    
    def check_sector_limit(self, sector: str, position_value: float) -> Tuple[bool, str]:
        """Check sector exposure limit"""
        current = self.sector_exposure.get(sector, 0.0)
        new_exposure = current + position_value
        
        if new_exposure > self.total_capital * self.max_sector_pct / 100:
            return False, f"Would exceed max sector exposure ({self.max_sector_pct}%) for {sector}"
        
        return True, ""
    
    def check_daily_loss(self) -> Tuple[bool, str]:
        """Check daily loss limit"""
        if self.daily_pnl < 0:
            loss_pct = abs(self.daily_pnl) / self.total_capital * 100
            if loss_pct > self.max_daily_loss_pct:
                return False, f"Daily loss limit reached ({loss_pct:.1f}%)"
        
        return True, ""
    
    def update(self, pnl: float = 0.0):
        """Update portfolio state"""
        self.daily_pnl += pnl
        
        # Update peak
        current_capital = self.total_capital + self.daily_pnl
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital
    
    def get_drawdown(self) -> float:
        """Current drawdown %"""
        if self.peak_capital == 0:
            return 0.0
        current = self.total_capital + self.daily_pnl
        return max(0, (self.peak_capital - current) / self.peak_capital * 100)


# ============= EXIT ORDER MANAGEMENT =============

class OCOState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class OCOConfig:
    """One-Cancels-Other configuration"""
    profit_target_pct: float = 50.0
    stop_loss_pct: float = 30.0
    trailing_stop_pct: float = 0.0
    check_interval: int = 10
    enabled: bool = True
    partial_at_pt: bool = False
    partial_percentage: float = 50.0


@dataclass
class OCOOrder:
    """Exit order state"""
    order_id: str
    position_id: str
    ticker: str
    strike: float
    option_type: str
    quantity: int
    entry_price: float
    config: OCOConfig = field(default_factory=OCOConfig)
    state: OCOState = OCOState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    profit_target_price: float = 0.0
    stop_loss_price: float = 0.0
    peak_price: float = 0.0
    trailing_activated: bool = False
    
    def calculate_targets(self):
        """Calculate PT and SL prices"""
        self.profit_target_price = round(
            self.entry_price * (1 + self.config.profit_target_pct / 100), 2
        )
        self.stop_loss_price = round(
            self.entry_price * (1 - self.config.stop_loss_pct / 100), 2
        )
    
    def check_exit(self, current_price: float) -> Dict:
        """Check if exit condition met"""
        self.peak_price = max(self.peak_price, current_price)
        result = {'action': None, 'price': current_price, 'reason': ''}
        
        # Check trailing stop
        if self.trailing_activated and self.config.trailing_stop_pct > 0:
            trailing_level = self.peak_price * (1 - self.config.trailing_stop_pct / 100)
            if current_price <= trailing_level:
                result['action'] = 'trailing_stop'
                result['reason'] = f'TS: ${current_price:.2f} <= ${trailing_level:.2f}'
                self.state = OCOState.TRIGGERED
                return result
        
        # Check profit target
        if current_price >= self.profit_target_price:
            if self.config.trailing_stop_pct > 0:
                self.trailing_activated = True
                self.peak_price = current_price
                result['action'] = 'trailing_activated'
                result['reason'] = 'PT reached, trailing activated'
            else:
                result['action'] = 'profit_target'
                result['reason'] = f'PT: ${current_price:.2f} >= ${self.profit_target_price:.2f}'
                self.state = OCOState.COMPLETED
            return result
        
        # Check stop loss
        if current_price <= self.stop_loss_price:
            result['action'] = 'stop_loss'
            result['reason'] = f'SL: ${current_price:.2f} <= ${self.stop_loss_price:.2f}'
            self.state = OCOState.TRIGGERED
            return result
        
        return result


def parse_oco_string(oco_str: str) -> OCOConfig:
    """Parse OCO config from string like 'PT1 50%TS5% SL 50%'"""
    import re
    
    config = OCOConfig()
    oco_str = oco_str.upper()
    
    pt_match = re.search(r'PT(?:\d+)?\s*(\d+)%', oco_str)
    if pt_match:
        config.profit_target_pct = float(pt_match.group(1))
    
    ts_match = re.search(r'TS(\d+)%', oco_str)
    if ts_match:
        config.trailing_stop_pct = float(ts_match.group(1))
    
    sl_match = re.search(r'SL\s*(\d+)%', oco_str)
    if sl_match:
        config.stop_loss_pct = float(sl_match.group(1))
    
    return config


def check_exit_conditions(
    entry_price: float,
    current_price: float,
    config: OCOConfig,
) -> Dict:
    """
    Check exit conditions without creating OCO order.
    Returns dict with action, price, reason.
    """
    order = OCOOrder(
        order_id="temp",
        position_id="temp",
        ticker="",
        strike=0,
        option_type="",
        quantity=1,
        entry_price=entry_price,
        config=config,
    )
    order.calculate_targets()
    return order.check_exit(current_price)


# ============= UNIFIED RISK MANAGER =============

class RiskManager:
    """
    Unified risk manager combining all risk functions.
    Use this instead of separate modules.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.portfolio = PortfolioRisk(
            total_capital=self.config.get('total_capital', 100000.0),
            max_position_size_pct=self.config.get('max_position_size_pct', 10.0),
            max_sector_pct=self.config.get('max_sector_pct', 30.0),
            max_daily_loss_pct=self.config.get('max_daily_loss_pct', 5.0),
            max_drawdown_pct=self.config.get('max_drawdown_pct', 20.0),
        )
        self._oco_orders: Dict[str, OCOOrder] = {}
    
    def check_new_trade(
        self,
        parsed_alert: dict,
        position_value: float,
        sector: str = None,
    ) -> Tuple[bool, str]:
        """
        Check if new trade is allowed.
        Returns (allowed, reason).
        """
        # 1. Duplicate check
        if is_duplicate_alert(parsed_alert):
            return False, "Duplicate alert"
        
        # 2. Position size check
        allowed, reason = self.portfolio.check_position_limit(position_value)
        if not allowed:
            return False, reason
        
        # 3. Sector check
        if sector:
            allowed, reason = self.portfolio.check_sector_limit(sector, position_value)
            if not allowed:
                return False, reason
        
        # 4. Daily loss check
        allowed, reason = self.portfolio.check_daily_loss()
        if not allowed:
            return False, reason
        
        # 5. Drawdown check
        if self.portfolio.get_drawdown() > self.portfolio.max_drawdown_pct:
            return False, f"Max drawdown ({self.portfolio.max_drawdown_pct}%) reached"
        
        return True, ""
    
    def calculate_size(
        self,
        entry_price: float,
        default_quantity: int = 5,
        stop_loss_pct: float = 30.0,
    ) -> int:
        """Calculate position size"""
        return calculate_position_size(
            entry_price=entry_price,
            default_quantity=default_quantity,
            max_position_size=self.config.get('max_position_size', 0),
            total_capital=self.portfolio.total_capital,
            risk_per_trade_pct=self.config.get('risk_per_trade_pct', 1.0),
            stop_loss_pct=stop_loss_pct,
        )
    
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
        """Create exit order"""
        if config is None:
            config = OCOConfig()
        
        order = OCOOrder(
            order_id=f"oco_{position_id}_{datetime.now().timestamp()}",
            position_id=position_id,
            ticker=ticker,
            strike=strike,
            option_type=option_type,
            quantity=quantity,
            entry_price=entry_price,
            config=config,
        )
        order.calculate_targets()
        order.state = OCOState.ACTIVE
        
        self._oco_orders[order.order_id] = order
        return order.order_id
    
    def check_oco(self, order_id: str, current_price: float) -> Optional[Dict]:
        """Check OCO exit conditions"""
        order = self._oco_orders.get(order_id)
        if not order:
            return None
        
        return order.check_exit(current_price)
    
    def update_portfolio(self, pnl: float):
        """Update portfolio PnL"""
        self.portfolio.update(pnl)


# Export all
__all__ = [
    # Duplicate detection
    'is_duplicate_alert',
    # Position sizing
    'calculate_position_size',
    # Correlation
    'check_correlation',
    # Portfolio risk
    'PortfolioRisk',
    # Exit orders
    'OCOState',
    'OCOConfig', 
    'OCOOrder',
    'parse_oco_string',
    'check_exit_conditions',
    # Unified manager
    'RiskManager',
]