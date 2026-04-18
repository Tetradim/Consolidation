"""
Algorithm Library - Pre-built Trading Strategies
Mean Reversion, Momentum, Breakout, etc.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Types of trading strategies"""
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    PAIRS = "pairs"
    SAR = "stop_and_reverse"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER = "bollinger"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass
class Signal:
    """Trading signal"""
    timestamp: datetime
    ticker: str
    side: PositionSide
    strength: float = 1.0  # 0-1 confidence
    price: float = 0.0
    reason: str = ""


@dataclass
class Strategy:
    """Base strategy"""
    name: str
    type: StrategyType
    parameters: Dict = field(default_factory=dict)
    
    # Runtime state
    positions: Dict[str, float] = field(default_factory=dict)
    signals: List[Signal] = field(default_factory=list)
    
    def update(self, data: pd.DataFrame) -> List[Signal]:
        """Generate signals from data"""
        return []
    
    def reset(self) -> None:
        """Reset strategy state"""
        self.positions.clear()
        self.signals.clear()


class MeanReversion(Strategy):
    """Mean Reversion Strategy"""
    
    def __init__(self, lookback: int = 20, threshold: float = 2.0):
        super().__init__("MeanReversion", StrategyType.MEAN_REVERSION, {
            'lookback': lookback,
            'threshold': threshold,
        })
        self.lookback = lookback
        self.threshold = threshold
    
    def update(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.lookback:
            return signals
        
        # Calculate mean and std
        data['mean'] = data['close'].rolling(self.lookback).mean()
        data['std'] = data['close'].rolling(self.lookback).std()
        
        # Z-score
        data['zscore'] = (data['close'] - data['mean']) / data['std']
        
        last = data.iloc[-1]
        
        # Long when oversold
        if last['zscore'] < -self.threshold:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.LONG,
                strength=min(1.0, abs(last['zscore']) / self.threshold),
                price=last['close'],
                reason=f"Z-score: {last['zscore']:.2f}",
            ))
        
        # Short when overbought
        elif last['zscore'] > self.threshold:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.SHORT,
                strength=min(1.0, abs(last['zscore']) / self.threshold),
                price=last['close'],
                reason=f"Z-score: {last['zscore']:.2f}",
            ))
        
        return signals


class Momentum(Strategy):
    """Momentum strategy"""
    
    def __init__(self, fast: int = 10, slow: int = 30):
        super().__init__("Momentum", StrategyType.MOMENTUM, {
            'fast': fast,
            'slow': slow,
        })
        self.fast = fast
        self.slow = slow
    
    def update(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.slow:
            return signals
        
        # Calculate EMAs
        data['fast_ema'] = data['close'].ewm(span=self.fast).mean()
        data['slow_ema'] = data['close'].ewm(span=self.slow).mean()
        
        # Momentum crossover
        data['momentum'] = data['fast_ema'] - data['slow_ema']
        
        last = data.iloc[-1]
        prev = data.iloc[-2]
        
        # Golden cross - long
        if prev['momentum'] < 0 and last['momentum'] > 0:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.LONG,
                strength=min(1.0, abs(last['momentum']) / last['close']),
                price=last['close'],
                reason="Golden cross",
            ))
        
        # Death cross - exit long
        elif prev['momentum'] > 0 and last['momentum'] < 0:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.FLAT,
                strength=min(1.0, abs(last['momentum']) / last['close']),
                price=last['close'],
                reason="Death cross",
            ))
        
        return signals


class Breakout(Strategy):
    """Breakout strategy"""
    
    def __init__(self, lookback: int = 20, atr_mult: float = 2.0):
        super().__init__("Breakout", StrategyType.BREAKOUT, {
            'lookback': lookback,
            'atr_mult': atr_mult,
        })
        self.lookback = lookback
        self.atr_mult = atr_mult
    
    def update(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.lookback + 1:
            return signals
        
        # Calculate ATR
        data['tr'] = np.maximum(
            data['high'] - data['low'],
            np.maximum(
                abs(data['high'] - data['close'].shift(1)),
                abs(data['low'] - data['close'].shift(1))
            )
        )
        data['atr'] = data['tr'].rolling(self.lookback).mean()
        
        # Donchian channel
        data['upper'] = data['high'].rolling(self.lookback).max()
        data['lower'] = data['low'].rolling(self.lookback).min()
        
        last = data.iloc[-1]
        
        # Breakout above
        if last['close'] > last['upper']:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.LONG,
                strength=min(1.0, (last['close'] - last['upper']) / last['atr']),
                price=last['close'],
                reason=f"Breakout: ${last['close']:.2f} > ${last['upper']:.2f}",
            ))
        
        # Breakdown below
        elif last['close'] < last['lower']:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.SHORT,
                strength=min(1.0, (last['lower'] - last['close']) / last['atr']),
                price=last['close'],
                reason=f"Breakdown: ${last['close']:.2f} < ${last['lower']:.2f}",
            ))
        
        return signals


class RSIStrategy(Strategy):
    """RSI Strategy"""
    
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__("RSI", StrategyType.RSI, {
            'period': period,
            'oversold': oversold,
            'overbought': overbought,
        })
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def update(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.period + 1:
            return signals
        
        # RSI calculation
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(self.period).mean()
        avg_loss = loss.rolling(self.period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        last_rsi = rsi.iloc[-1]
        last = data.iloc[-1]
        
        # Oversold - buy
        if last_rsi < self.oversold:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.LONG,
                strength=min(1.0, (self.oversold - last_rsi) / self.oversold),
                price=last['close'],
                reason=f"RSI: {last_rsi:.1f}",
            ))
        
        # Overbought - sell/short
        elif last_rsi > self.overbought:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.SHORT,
                strength=min(1.0, (last_rsi - self.overbought) / (100 - self.overbought)),
                price=last['close'],
                reason=f"RSI: {last_rsi:.1f}",
            ))
        
        return signals


class MACDStrategy(Strategy):
    """MACD Strategy"""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("MACD", StrategyType.MACD, {
            'fast': fast,
            'slow': slow,
            'signal': signal,
        })
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def update(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.slow + self.signal:
            return signals
        
        # MACD calculation
        ema_fast = data['close'].ewm(span=self.fast).mean()
        ema_slow = data['close'].ewm(span=self.slow).mean()
        data['macd'] = ema_fast - ema_slow
        data['signal_line'] = data['macd'].ewm(span=self.signal).mean()
        data['histogram'] = data['macd'] - data['signal_line']
        
        last = data.iloc[-1]
        prev = data.iloc[-2]
        
        # Bullish crossover
        if prev['histogram'] < 0 and last['histogram'] > 0:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.LONG,
                strength=min(1.0, abs(last['histogram']) / last['macd'] if last['macd'] != 0 else 0),
                price=last['close'],
                reason="MACD bullish",
            ))
        
        # Bearish crossover
        elif prev['histogram'] > 0 and last['histogram'] < 0:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.SHORT,
                strength=min(1.0, abs(last['histogram']) / last['macd'] if last['macd'] != 0 else 0),
                price=last['close'],
                reason="MACD bearish",
            ))
        
        return signals


class BollingerBand(Strategy):
    """Bollinger Bands Strategy"""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__("Bollinger", StrategyType.BOLLINGER, {
            'period': period,
            'std_dev': std_dev,
        })
        self.period = period
        self.std_dev = std_dev
    
    def update(self, data: pd.DataFrame) -> List[Signal]:
        signals = []
        
        if len(data) < self.period:
            return signals
        
        # Bollinger Bands
        data['middle'] = data['close'].rolling(self.period).mean()
        data['std'] = data['close'].rolling(self.period).std()
        data['upper'] = data['middle'] + (self.std_dev * data['std'])
        data['lower'] = data['middle'] - (self.std_dev * data['std'])
        
        last = data.iloc[-1]
        
        # Touch lower band - buy
        if last['close'] <= last['lower']:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.LONG,
                strength=1.0,
                price=last['close'],
                reason="Touch lower BB",
            ))
        
        # Touch upper band - sell
        elif last['close'] >= last['upper']:
            signals.append(Signal(
                timestamp=last.name if isinstance(last.name, datetime) else datetime.now(),
                ticker=data.get('symbol', 'UNKNOWN'),
                side=PositionSide.SHORT,
                strength=1.0,
                price=last['close'],
                reason="Touch upper BB",
            ))
        
        return signals


# ============= FACTORY =============

def create_strategy(
    strategy_type: str,
    **params,
) -> Optional[Strategy]:
    """Create strategy by type"""
    
    strategies = {
        'mean_reversion': MeanReversion,
        'momentum': Momentum,
        'breakout': Breakout,
        'rsi': RSIStrategy,
        'macd': MACDStrategy,
        'bollinger': BollingerBand,
    }
    
    strategy_class = strategies.get(strategy_type.lower())
    if strategy_class:
        return strategy_class(**params)
    
    return None


def get_available_strategies() -> List[dict]:
    """Get list of all strategies"""
    return [
        {'id': 'mean_reversion', 'name': 'Mean Reversion', 'params': ['lookback', 'threshold']},
        {'id': 'momentum', 'name': 'Momentum', 'params': ['fast', 'slow']},
        {'id': 'breakout', 'name': 'Breakout', 'params': ['lookback', 'atr_mult']},
        {'id': 'rsi', 'name': 'RSI', 'params': ['period', 'oversold', 'overbought']},
        {'id': 'macd', 'name': 'MACD', 'params': ['fast', 'slow', 'signal']},
        {'id': 'bollinger', 'name': 'Bollinger Bands', 'params': ['period', 'std_dev']},
    ]


# Export
__all__ = [
    'StrategyType',
    'PositionSide',
    'Signal',
    'Strategy',
    'MeanReversion',
    'Momentum',
    'Breakout',
    'RSIStrategy',
    'MACDStrategy',
    'BollingerBand',
    'create_strategy',
    'get_available_strategies',
]