"""
Trading Analytics
- Performance metrics
- Trade history analysis
- Win rate and expectancy calculations
- Position analytics
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class TradeMetrics:
    """Trade performance metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    total_pnl: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Streaks
    current_streak: int = 0
    longest_win_streak: int = 0
    longest_loss_streak: int = 0
    
    # Time metrics
    total_held_time_minutes: float = 0.0
    avg_hold_time_minutes: float = 0.0
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def profit_factor(self) -> float:
        if self.avg_loss == 0:
            return 0.0
        return abs(self.avg_win / self.avg_loss)
    
    @property
    def expectancy(self) -> float:
        """Expected value per trade"""
        win_rate = self.win_rate / 100
        if win_rate == 0:
            return -100.0
        return (win_rate * self.avg_loss) + ((1 - win_rate) * self.avg_loss)
    
    def calculate_from_trades(self, trades: List[Dict]) -> None:
        """Calculate metrics from trade history"""
        if not trades:
            return
        
        self.total_trades = len(trades)
        
        pnls = []
        hold_times = []
        
        for trade in trades:
            pnl = trade.get('realized_pnl', 0) or trade.get('pnl', 0)
            pnls.append(pnl)
            
            if trade.get('opened_at') and trade.get('closed_at'):
                try:
                    opened = datetime.fromisoformat(trade['opened_at'])
                    closed = datetime.fromisoformat(trade['closed_at'])
                    hold_times.append((closed - opened).total_seconds() / 60)
                except:
                    pass
        
        if pnls:
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            
            self.winning_trades = len(wins)
            self.losing_trades = len(losses)
            self.total_pnl = sum(pnls)
            
            if wins:
                self.avg_win = statistics.mean(wins)
                self.largest_win = max(wins)
            
            if losses:
                self.avg_loss = statistics.mean(losses)
                self.largest_loss = min(losses)
            
            # Update streaks
            current = 0
            for pnl in pnls:
                if pnl > 0:
                    current = current + 1 if current > 0 else 1
                    self.longest_win_streak = max(self.longest_win_streak, current)
                else:
                    current = current - 1 if current < 0 else -1
                    self.longest_loss_streak = min(self.longest_loss_streak, current)
        
        if hold_times:
            self.total_held_time_minutes = sum(hold_times)
            self.avg_hold_time_minutes = statistics.mean(hold_times)
    
    def to_dict(self) -> dict:
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate, 2),
            'total_pnl': round(self.total_pnl, 2),
            'avg_win': round(self.avg_win, 2),
            'avg_loss': round(self.avg_loss, 2),
            'largest_win': round(self.largest_win, 2),
            'largest_loss': round(self.largest_loss, 2),
            'profit_factor': round(self.profit_factor, 2),
            'expectancy': round(self.expectancy, 2),
            'longest_win_streak': self.longest_win_streak,
            'longest_loss_streak': abs(self.longest_loss_streak),
            'avg_hold_time_minutes': round(self.avg_hold_time_minutes, 1),
        }


@dataclass
class PositionAnalytics:
    """Analytics for a single position"""
    
    position_id: str
    ticker: str
    strike: float
    option_type: str
    
    entry_price: float
    quantity: int
    
    # Tracking
    entry_time: datetime = field(default_factory=datetime.now)
    peak_price: float = 0.0
    trough_price: float = float('inf')
    
    # Metrics
    max_price: float = 0.0
    min_price: float = float('inf')
    
    high_water_mark: float = 0.0
    
    def update(self, current_price: float, timestamp: datetime = None) -> None:
        """Update with new price"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Update peak/trough
        if current_price > self.peak_price:
            self.peak_price = current_price
        if current_price < self.trough_price:
            self.trough_price = current_price
        
        # Track session high/low
        self.max_price = max(self.max_price, current_price)
        self.min_price = min(self.min_price, current_price)
        
        # High water mark
        pnl = (current_price - self.entry_price) * self.quantity * 100
        if pnl > self.high_water_mark:
            self.high_water_mark = pnl
    
    @property
    def unrealized_pnl(self) -> float:
        return (self.peak_price - self.entry_price) * self.quantity * 100
    
    @property
    def return_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        return ((self.peak_price - self.entry_price) / self.entry_price) * 100
    
    @property
    def volatility(self) -> float:
        """Simple volatility measure"""
        if self.min_price == float('inf'):
            return 0.0
        return ((self.max_price - self.min_price) / self.entry_price) * 100
    
    @property
    def hold_time_minutes(self) -> float:
        elapsed = datetime.now(timezone.utc) - self.entry_time
        return elapsed.total_seconds() / 60
    
    def to_dict(self) -> dict:
        return {
            'position_id': self.position_id,
            'ticker': self.ticker,
            'current_price': self.peak_price,
            'unrealized_pnl': round(self.unrealized_pnl, 2),
            'return_pct': round(self.return_pct, 2),
            'peak_price': self.peak_price,
            'trough_price': self.trough_price if self.trough_price != float('inf') else 0,
            'hold_time_minutes': round(self.hold_time_minutes, 1),
            'high_water_mark': round(self.high_water_mark, 2),
        }


class PerformanceAnalyzer:
    """Analyze trading performance"""
    
    def __init__(self):
        self._positions: Dict[str, PositionAnalytics] = {}
        self._daily_stats: Dict[str, Dict] = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0
        })
    
    def register_position(
        self,
        position_id: str,
        ticker: str,
        strike: float,
        option_type: str,
        entry_price: float,
        quantity: int
    ) -> None:
        """Register new position for tracking"""
        self._positions[position_id] = PositionAnalytics(
            position_id=position_id,
            ticker=ticker,
            strike=strike,
            option_type=option_type,
            entry_price=entry_price,
            quantity=quantity,
        )
    
    def update_position(
        self,
        position_id: str,
        current_price: float
    ) -> None:
        """Update position price"""
        if position_id in self._positions:
            self._positions[position_id].update(current_price)
    
    def close_position(
        self,
        position_id: str,
        exit_price: float,
        reason: str
    ) -> dict:
        """Close position and record stats"""
        if position_id not in self._positions:
            return {}
        
        pos = self._positions.pop(position_id)
        
        # Calculate metrics
        pnl = (exit_price - pos.entry_price) * pos.quantity * 100
        is_win = pnl > 0
        
        # Record daily stats
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        self._daily_stats[today]['trades'] += 1
        if is_win:
            self._daily_stats[today]['wins'] += 1
        else:
            self._daily_stats[today]['losses'] += 1
        self._daily_stats[today]['pnl'] += pnl
        
        return {
            'position_id': position_id,
            'exit_price': exit_price,
            'pnl': pnl,
            'is_win': is_win,
            'reason': reason,
            'holding_time_minutes': round(pos.hold_time_minutes, 1),
        }
    
    def get_position_status(self, position_id: str) -> Optional[dict]:
        """Get position analytics"""
        if position_id in self._positions:
            return self._positions[position_id].to_dict()
        return None
    
    def get_all_positions(self) -> List[dict]:
        """Get all position analytics"""
        return [p.to_dict() for p in self._positions.values()]
    
    def get_daily_summary(self, date: str = None) -> dict:
        """Get daily summary"""
        if date is None:
            date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        stats = self._daily_stats.get(date, {})
        if not stats:
            return {
                'date': date,
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'pnl': 0.0,
                'win_rate': 0.0,
            }
        
        win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
        
        return {
            'date': date,
            **stats,
            'win_rate': round(win_rate, 1),
        }
    
    def get_best_trade(self) -> dict:
        """Get best trade historically"""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        day_stats = self._daily_stats.get(today, {})
        
        # This is simplified - would need full history for true best
        return {
            'pnl': day_stats.get('pnl', 0),
            'date': today,
        }
    
    def get_performance_summary(self) -> dict:
        """Get overall performance summary"""
        all_dates = sorted(self._daily_stats.keys())
        
        total_trades = 0
        total_wins = 0
        total_pnl = 0.0
        
        for date in all_dates:
            stats = self._daily_stats[date]
            total_trades += stats['trades']
            total_wins += stats['wins']
            total_pnl += stats['pnl']
        
        return {
            'total_trades': total_trades,
            'total_wins': total_wins,
            'total_pnl': round(total_pnl, 2),
            'win_rate': round((total_wins / total_trades * 100) if total_trades > 0 else 0, 1),
            'trading_days': len(all_dates),
            'avg_pnl_per_day': round(total_pnl / len(all_dates), 2) if all_dates else 0,
        }


# Global analytics instance
_performance_analyzer: Optional[PerformanceAnalyzer] = None


def get_performance_analyzer() -> PerformanceAnalyzer:
    """Get global performance analyzer"""
    global _performance_analyzer
    if _performance_analyzer is None:
        _performance_analyzer = PerformanceAnalyzer()
    return _performance_analyzer