"""
Strategy Optimization - Grid Search & Parameter Tuning
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import itertools

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Result of a backtest"""
    params: Dict
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    profit_factor: float = 0.0
    
    # Additional metrics
    avg_return: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    
    @property
    def score(self) -> float:
        """Optimization score (higher = better)"""
        # Combine metrics - favor sharpe and return
        return self.sharpe_ratio * 0.4 + self.total_return * 0.3 + (self.win_rate / 100) * 0.3
    
    def to_dict(self) -> dict:
        return {
            'params': self.params,
            'total_return': self.total_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'total_trades': self.total_trades,
            'profit_factor': self.profit_factor,
            'score': self.score,
        }


@dataclass
class OptimizationConfig:
    """Configuration for optimization"""
    strategy_type: str
    param_grid: Dict[str, List]  # e.g., {'lookback': [10, 20, 30]}
    
    # Data
    data: pd.DataFrame = None
    
    # Constraints
    min_trades: int = 10
    max_drawdown: float = 50.0  # %
    
    # Performance
    n_jobs: int = 1  # Parallel jobs
    metric: str = "score"  # Optimization metric
    
    # Walk-forward
    walk_forward: bool = False
    train_size: float = 0.7  # Train/test split


class Optimizer:
    """Strategy parameter optimizer"""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.results: List[BacktestResult] = []
    
    def optimize(self) -> List[BacktestResult]:
        """Run optimization"""
        # Generate parameter combinations
        param_names = list(self.config.param_grid.keys())
        param_values = list(self.config.param_grid.values())
        combinations = list(itertools.product(*param_values))
        
        logger.info(f"[Optimizer] Testing {len(combinations)} parameter combinations")
        
        if self.config.n_jobs > 1:
            # Parallel execution
            self.results = self._parallel_optimize(param_names, combinations)
        else:
            # Sequential
            self.results = self._sequential_optimize(param_names, combinations)
        
        # Sort by score
        self.results.sort(key=lambda x: x.score, reverse=True)
        
        return self.results
    
    def _sequential_optimize(
        self,
        param_names: List[str],
        combinations: List[Tuple],
    ) -> List[BacktestResult]:
        """Sequential optimization"""
        results = []
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            result = self._backtest(params)
            
            if result:
                results.append(result)
        
        return results
    
    def _parallel_optimize(
        self,
        param_names: List[str],
        combinations: List[Tuple],
    ) -> List[BacktestResult]:
        """Parallel optimization"""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.config.n_jobs) as executor:
            futures = {}
            
            for combo in combinations:
                params = dict(zip(param_names, combo))
                future = executor.submit(self._backtest, params)
                futures[future] = params
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
        
        return results
    
    def _backtest(self, params: Dict) -> Optional[BacktestResult]:
        """Run backtest for given parameters"""
        from strategies_library import create_strategy
        
        # Create strategy
        strategy = create_strategy(self.config.strategy_type, **params)
        if not strategy:
            return None
        
        # Run on data
        signals = []
        positions = []
        equity = [10000]  # Start with $10k
        
        for i in range(50, len(self.config.data)):
            window = self.config.data.iloc[:i].copy()
            window['symbol'] = self.config.data.get('symbol', 'TEST')
            
            new_signals = strategy.update(window)
            signals.extend(new_signals)
            
            # Simulate trade
            current_price = self.config.data.iloc[i]['close']
            
            # Simple simulation
            for sig in new_signals:
                if sig.side.value == "LONG":
                    positions.append({
                        'entry': sig.price,
                        'exit': current_price,
                        'pnl': (current_price - sig.price) / sig.price * 100
                    })
        
        # Calculate metrics
        if len(positions) < self.config.min_trades:
            return None
        
        pnls = [p['pnl'] for p in positions]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        total_return = sum(pnls)
        max_dd = self._calculate_max_drawdown(equity)
        win_rate = len(wins) / len(pnls) * 100 if pnls else 0
        
        # Sharpe ratio (simplified)
        if np.std(pnls) > 0:
            sharpe = np.mean(pnls) / np.std(pnls) * np.sqrt(252)
        else:
            sharpe = 0
        
        # Profit factor
        profit_factor = abs(sum(wins) / sum(losses)) if losses else 0
        
        # Filter by max drawdown
        if max_dd > self.config.max_drawdown:
            return None
        
        result = BacktestResult(
            params=params,
            total_return=total_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            total_trades=len(positions),
            profit_factor=profit_factor,
            avg_return=np.mean(pnls),
            avg_win=np.mean(wins) if wins else 0,
            avg_loss=np.mean(losses) if losses else 0,
        )
        
        return result
    
    def _calculate_max_drawdown(self, equity: List[float]) -> float:
        """Calculate max drawdown percentage"""
        if not equity:
            return 0
        
        peak = equity[0]
        max_dd = 0
        
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def get_best(self) -> Optional[BacktestResult]:
        """Get best result"""
        return self.results[0] if self.results else None
    
    def get_top_n(self, n: int = 5) -> List[BacktestResult]:
        """Get top N results"""
        return self.results[:n]


class WalkForwardOptimizer(Optimizer):
    """Walk-forward optimization"""
    
    def optimize(self) -> List[BacktestResult]:
        """Run walk-forward optimization"""
        results = []
        
        data = self.config.data
        train_size = int(len(data) * self.config.train_size)
        
        # Walk forward windows
        n_windows = 5
        step = (len(data) - train_size) // n_windows
        
        for i in range(n_windows):
            start = i * step
            end = start + train_size
            
            train_data = data.iloc[start:end]
            test_data = data.iloc[end:end + step] if end + step < len(data) else data.iloc[end:]
            
            # Optimize on train
            self.config.data = train_data
            window_results = super().optimize()
            
            # Get best and test on test
            best = window_results[0] if window_results else None
            
            if best:
                # Run on test
                self.config.data = test_data
                test_result = self._backtest(best.params)
                if test_result:
                    test_result.params['window'] = i
                    results.append(test_result)
        
        results.sort(key=lambda x: x.score, reverse=True)
        self.results = results
        
        return results


# ============= HELPER FUNCTIONS =============

def optimize_strategy(
    strategy_type: str,
    param_grid: Dict[str, List],
    data: pd.DataFrame,
    **kwargs,
) -> List[BacktestResult]:
    """Quick optimize function"""
    config = OptimizationConfig(
        strategy_type=strategy_type,
        param_grid=param_grid,
        data=data,
        **kwargs,
    )
    
    optimizer = Optimizer(config)
    return optimizer.optimize()


# Export
__all__ = [
    'BacktestResult',
    'OptimizationConfig',
    'Optimizer',
    'WalkForwardOptimizer',
    'optimize_strategy',
]