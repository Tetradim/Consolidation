"""
Enhanced Risk Management
- Advanced position sizing
- Portfolio-level risk controls
- Drawdown protection
- Position correlation analysis
- Dynamic risk adjustments
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class PortfolioRisk:
    """Portfolio-level risk metrics"""
    total_capital: float = 10000.0
    max_position_size_pct: float = 10.0  # Max 10% per position
    max_sector_pct: float = 30.0  # Max 30% in one sector
    max_daily_loss_pct: float = 5.0  # Max 5% daily loss
    max_drawdown_pct: float = 20.0  # Max 20% drawdown
    
    # Current state
    open_positions_value: float = 0.0
    daily_pnl: float = 0.0
    peak_capital: float = 10000.0
    
    # For drawdown tracking
    drawdown_start: Optional[datetime] = None
    
    def calculate_position_size(
        self,
        entry_price: float,
        risk_per_trade_pct: float = 1.0,
        stop_loss_pct: float = 30.0
    ) -> int:
        """
        Calculate position size based on portfolio risk
        
        Uses Kelly Criterion-inspired sizing:
        position_size = (capital * risk%) / (entry * stop_loss%)
        """
        if entry_price <= 0 or stop_loss_pct <= 0:
            return 1
        
        # Maximum position size based on capital
        max_by_capital = (self.total_capital * self.max_position_size_pct / 100) / entry_price / 100
        max_by_capital = int(max_by_capital)
        
        # Risk-based position size
        risk_amount = self.total_capital * risk_per_trade_pct / 100
        risk_size = int(risk_amount / (entry_price * (stop_loss_pct / 100)) / 100)
        
        # Use smaller of the two
        position_size = min(max_by_capital, max(1, risk_size))
        
        logger.info(
            f"[Risk] Position size: {position_size} contracts "
            f"(risk: {risk_per_trade_pct}%, stop: {stop_loss_pct}%)"
        )
        
        return position_size
    
    def check_drawdown(self) -> Tuple[bool, str]:
        """Check if we're in a drawdown and should stop trading"""
        if self.daily_pnl <= 0:
            return False, ""
        
        current_pct = (self.daily_pnl / self.total_capital) * 100
        
        if current_pct >= self.max_daily_loss_pct:
            logger.warning(f"[Risk] Daily loss limit hit: {current_pct:.1f}%")
            return True, f"daily_loss: {current_pct:.1f}%"
        
        # Check overall drawdown from peak
        if self.total_capital < self.peak_capital:
            drawdown = ((self.peak_capital - self.total_capital) / self.peak_capital) * 100
            if drawdown >= self.max_drawdown_pct:
                logger.warning(f"[Risk] Max drawdown hit: {drawdown:.1f}%")
                return True, f"drawdown: {drawdown:.1f}%"
        
        return False, ""
    
    def update_daily_pnl(self, pnl: float) -> None:
        """Update daily P&L and track drawdown"""
        self.daily_pnl = pnl
        
        if pnl > 0 and self.daily_pnl == 0:
            # Reset for new day
            self.peak_capital = self.total_capital
    
    def can_open_position(self, position_value: float) -> Tuple[bool, str]:
        """Check if we can open a new position"""
        # Check total exposure
        total_exposure = self.open_positions_value + position_value
        if total_exposure > self.total_capital * self.max_position_size_pct * 2 / 100:
            return False, "max_exposure_reached"
        
        # Check daily loss
        stop, reason = self.check_drawdown()
        if stop:
            return False, reason
        
        return True, ""


@dataclass
class CorrelationAnalyzer:
    """Analyze position correlations to avoid over-concentration"""
    
    # Ticker to sector mapping (simplified)
    SECTOR_MAP: Dict[str, str] = field(default_factory=lambda: {
        # Tech
        'QQQ': 'tech', 'AAPL': 'tech', 'MSFT': 'tech', 'GOOGL': 'tech', 'GOOG': 'tech',
        'META': 'tech', 'NVDA': 'tech', 'AMD': 'tech', 'INTC': 'tech', 'CRM': 'tech',
        # Finance
        'JPM': 'finance', 'BAC': 'finance', 'WFC': 'finance', 'GS': 'finance', 'MS': 'finance',
        # Healthcare
        'JNJ': 'healthcare', 'PFE': 'healthcare', 'UNH': 'healthcare', 'ABBV': 'healthcare',
        # Energy
        'XOM': 'energy', 'CVX': 'energy', 'COP': 'energy', 'SLB': 'energy',
        # Consumer
        'AMZN': 'consumer', 'WMT': 'consumer', 'TGT': 'consumer', 'HD': 'consumer',
        # Industrial
        'BA': 'industrial', 'CAT': 'industrial', 'GE': 'industrial', 'MMM': 'industrial',
        # Utilities/Telecom
        'T': 'telecom', 'VZ': 'telecom',
        # Real Estate
        'PLD': 'reit', 'AMT': 'reit',
        # Materials
        'LIN': 'materials', 'APD': 'materials',
    })
    
    # Max positions per sector
    max_per_sector: int = 3
    
    # Correlation data
    _sector_positions: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    _ticker_positions: Dict[str, int] = field(default_factory=dict)
    
    def get_sector(self, ticker: str) -> str:
        """Get sector for ticker"""
        return self.SECTOR_MAP.get(ticker.upper(), 'other')
    
    def check_position(
        self,
        ticker: str,
        max_per_ticker: int = 2,
        max_per_sector: int = 3
    ) -> Tuple[bool, str]:
        """Check if adding position would create correlation issues"""
        ticker = ticker.upper()
        sector = self.get_sector(ticker)
        
        # Check ticker limit
        current_ticker = self._ticker_positions.get(ticker, 0)
        if current_ticker >= max_per_ticker:
            return False, f"max_ticker: {current_ticker + 1} > {max_per_ticker}"
        
        # Check sector limit
        current_sector = len(self._sector_positions.get(sector, []))
        if current_sector >= max_per_sector:
            return False, f"max_sector: {current_sector + 1} > {max_per_sector}"
        
        return True, ""
    
    def add_position(self, ticker: str) -> None:
        """Record a new position"""
        ticker = ticker.upper()
        sector = self.get_sector(ticker)
        
        self._ticker_positions[ticker] = self._ticker_positions.get(ticker, 0) + 1
        self._sector_positions[sector].append(ticker)
        
        logger.info(
            f"[Correlation] Added {ticker} to {sector} sector. "
            f"Sector total: {len(self._sector_positions[sector])}"
        )
    
    def remove_position(self, ticker: str) -> None:
        """Remove a closed position"""
        ticker = ticker.upper()
        sector = self.get_sector(ticker)
        
        current = self._ticker_positions.get(ticker, 0)
        if current > 0:
            self._ticker_positions[ticker] = current - 1
        
        if ticker in self._sector_positions[sector]:
            self._sector_positions[sector].remove(ticker)
    
    def get_concentration(self) -> Dict:
        """Get current concentration by sector"""
        return {
            'by_ticker': dict(self._ticker_positions),
            'by_sector': {k: len(v) for k, v in self._sector_positions.items()},
        }
    
    def reset(self) -> None:
        """Reset for new day"""
        self._ticker_positions.clear()
        self._sector_positions.clear()


@dataclass  
class LossTracker:
    """Track consecutive losses and auto-shutdown"""
    
    max_consecutive_losses: int = 3
    max_daily_losses: int = 5
    max_daily_loss_amount: float = 500.0
    
    # State
    consecutive_losses: int = 0
    daily_losses: int = 0
    daily_loss_amount: float = 0.0
    last_loss_date: Optional[str] = None
    
    def record_win(self) -> None:
        """Record a winning trade"""
        self.consecutive_losses = 0
    
    def record_loss(self, loss_amount: float = 0.0) -> None:
        """Record a losing trade"""
        self.consecutive_losses += 1
        self.daily_losses += 1
        self.daily_loss_amount += abs(loss_amount)
        
        logger.warning(
            f"[LossTracker] Loss recorded. "
            f"Consecutive: {self.consecutive_losses}, "
            f"Daily: {self.daily_losses} (${self.daily_loss_amount:.2f})"
        )
    
    def can_trade(self) -> Tuple[bool, str]:
        """Check if we can continue trading"""
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"max_consecutive_losses: {self.consecutive_losses}"
        
        if self.daily_losses >= self.max_daily_losses:
            return False, f"max_daily_losses: {self.daily_losses}"
        
        if self.daily_loss_amount >= self.max_daily_loss_amount:
            return False, f"max_daily_loss: ${self.daily_loss_amount:.2f}"
        
        return True, ""
    
    def reset_daily(self) -> None:
        """Reset daily counters"""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if today != self.last_loss_date:
            self.daily_losses = 0
            self.daily_loss_amount = 0.0
            self.last_loss_date = today
    
    def to_dict(self) -> dict:
        return {
            'consecutive_losses': self.consecutive_losses,
            'daily_losses': self.daily_losses,
            'daily_loss_amount': self.daily_loss_amount,
            'can_trade': self.can_trade()[0],
        }


class EnhancedRiskManager:
    """Enhanced risk management combining all features"""
    
    def __init__(self):
        self.portfolio = PortfolioRisk()
        self.correlation = CorrelationAnalyzer()
        self.loss_tracker = LossTracker()
    
    def configure(self, settings: dict) -> None:
        """Configure from settings"""
        # Portfolio risk
        self.portfolio.max_position_size_pct = settings.get('max_position_size', 10.0)
        self.portfolio.max_daily_loss_pct = settings.get('max_daily_loss_pct', 5.0)
        self.portfolio.max_drawdown_pct = settings.get('max_drawdown_pct', 20.0)
        
        # Loss tracking
        self.loss_tracker.max_consecutive_losses = settings.get('max_consecutive_losses', 3)
        self.loss_tracker.max_daily_losses = settings.get('max_daily_losses', 5)
        self.loss_tracker.max_daily_loss_amount = settings.get('max_daily_loss_amount', 500.0)
        
        # Reset daily counters
        self.loss_tracker.reset_daily()
    
    def calculate_position_size(
        self,
        entry_price: float,
        risk_per_trade: float = 1.0,
        stop_loss_pct: float = 30.0
    ) -> int:
        """Calculate safe position size"""
        return self.portfolio.calculate_position_size(
            entry_price,
            risk_per_trade,
            stop_loss_pct
        )
    
    def can_open_trade(
        self,
        ticker: str,
        position_value: float
    ) -> Tuple[bool, str]:
        """Check if we can open a new trade"""
        # Check portfolio limits
        can_portfolio, reason = self.portfolio.can_open_position(position_value)
        if not can_portfolio:
            return False, reason
        
        # Check correlation
        can_correl, reason = self.correlation.check_position(ticker)
        if not can_correl:
            return False, reason
        
        # Check loss tracking
        can_trade, reason = self.loss_tracker.can_trade()
        if not can_trade:
            return False, reason
        
        return True, ""
    
    def record_trade_result(
        self,
        ticker: str,
        pnl: float
    ) -> None:
        """Record trade result for risk tracking"""
        if pnl < 0:
            self.loss_tracker.record_loss(pnl)
            self.correlation.remove_position(ticker)
        else:
            self.loss_tracker.record_win()
        
        # Update portfolio P&L
        self.portfolio.update_daily_pnl(pnl)
    
    def get_status(self) -> dict:
        """Get current risk status"""
        return {
            'portfolio': {
                'total_capital': self.portfolio.total_capital,
                'open_value': self.portfolio.open_positions_value,
                'daily_pnl': self.portfolio.daily_pnl,
            },
            'loss_tracking': self.loss_tracker.to_dict(),
            'correlation': self.correlation.get_concentration(),
        }
    
    def reset_for_day(self) -> None:
        """Reset counters for new trading day"""
        self.loss_tracker.reset_daily()
        self.correlation.reset()


# Global risk manager instance
_risk_manager: Optional[EnhancedRiskManager] = None


def get_risk_manager() -> EnhancedRiskManager:
    """Get global risk manager"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = EnhancedRiskManager()
    return _risk_manager


def configure_risk_manager(settings: dict) -> None:
    """Configure global risk manager"""
    global _risk_manager
    get_risk_manager().configure(settings)