"""
Grid Trading Strategy
Automated grid orders that buy low and sell high in range
Based on OctoBot patterns
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import math

logger = logging.getLogger(__name__)


class GridMode(Enum):
    """Grid trading modes"""
    LONG = "long"  # Buy low, sell high
    SHORT = "short"  # Sell high, buy low
    NEUTRAL = "neutral"  # Both directions


@dataclass
class GridLevel:
    """Single grid level"""
    level: int
    price: float
    quantity: float
    filled: bool = False
    order_id: str = ""


@dataclass
class GridConfig:
    """Grid configuration"""
    # Range
    lower_price: float = 0.0
    upper_price: float = 0.0
    grid_count: int = 10
    
    # Sizing
    position_size: float = 100.0  # $ per grid
    
    # Mode
    mode: GridMode = GridMode.LONG
    
    # Execution
    order_type: str = "LIMIT"  # LIMIT or MARKET
    price_offset: float = 0.01  # Offset from grid price
    
    # Take profit per grid
    profit_per_grid: float = 0.5  # %
    
    # Rebalancing
    auto_rebalance: bool = True
    rebalance_threshold: float = 0.2  # When to add levels


class GridStrategy:
    """Grid trading strategy"""
    
    def __init__(self, config: GridConfig):
        self.config = config
        self.levels: List[GridLevel] = []
        self.active_orders: List[Dict] = []
        self.filled_orders: List[Dict] = []
        
        # Calculate grid
        self._calculate_grid()
    
    def _calculate_grid(self) -> None:
        """Calculate grid levels"""
        if self.config.grid_count <= 0:
            return
        
        price_range = self.config.upper_price - self.config.lower_price
        step = price_range / (self.config.grid_count - 1)
        
        for i in range(self.config.grid_count):
            price = self.config.lower_price + (step * i)
            
            # Calculate quantity
            quantity = self.config.position_size / price
            
            # Determine if buy or sell level
            if self.config.mode == GridMode.LONG:
                # Buy at lower levels, sell at upper
                is_buy = i < self.config.grid_count / 2
            elif self.config.mode == GridMode.SHORT:
                # Sell at upper levels, buy at lower
                is_buy = i >= self.config.grid_count / 2
            else:
                is_buy = True  # Both
            
            level = GridLevel(
                level=i,
                price=price,
                quantity=quantity,
            )
            self.levels.append(level)
        
        logger.info(
            f"[Grid] Created {len(self.levels)} levels from "
            f"${self.config.lower_price} to ${self.config.upper_price}"
        )
    
    def get_pending_orders(self) -> List[Dict]:
        """Get pending orders to place"""
        orders = []
        
        for level in self.levels:
            if not level.filled:
                # Place order
                orders.append({
                    'symbol': 'UNKNOWN',
                    'side': 'BUY' if self.config.mode == GridMode.LONG else 'SELL',
                    'price': level.price * (1 - self.config.price_offset / 100),
                    'quantity': level.quantity,
                    'type': self.config.order_type,
                    'grid_level': level.level,
                })
        
        return orders
    
    def on_fill(self, order: Dict) -> bool:
        """Handle order fill"""
        grid_level = order.get('grid_level', -1)
        
        if grid_level >= 0 and grid_level < len(self.levels):
            level = self.levels[grid_level]
            level.filled = True
            level.order_id = order.get('order_id', '')
            
            self.filled_orders.append(order)
            
            # Check if we need to close position
            if self._should_close_position(level):
                return True  # Signal to close
        
        return False
    
    def _should_close_position(self, level: GridLevel) -> bool:
        """Check if position should be closed"""
        # For grid, we typically hold until profit target
        target_profit = level.price * (1 + self.config.profit_per_grid / 100)
        
        # In real implementation, check current price vs target
        return False
    
    def get_status(self) -> Dict:
        """Get grid status"""
        return {
            'mode': self.config.mode.value,
            'levels': len(self.levels),
            'filled': len([l for l in self.levels if l.filled]),
            'pending': len([l for l in self.levels if not l.filled]),
            'range': f"${self.config.lower_price} - ${self.config.upper_price}",
        }
    
    def estimate_profit(self, current_price: float) -> float:
        """Estimate profit at current price"""
        profit = 0.0
        
        for level in self.levels:
            if level.filled:
                # Calculate profit if closed at current price
                if self.config.mode == GridMode.LONG:
                    pnl = (current_price - level.price) * level.quantity
                else:
                    pnl = (level.price - current_price) * level.quantity
                profit += pnl
        
        return profit


# ============= DCA STRATEGY =============

@dataclass
class DCAStep:
    """Single DCA step"""
    step: int
    price_offset: float  # % from base
    size_multiplier: float  # Size multiplier vs base
    triggered: bool = False


@dataclass
class DCAConfig:
    """DCA (Dollar Cost Averaging) configuration"""
    # Base order
    base_size: float = 100.0  # $
    
    # Steps
    steps: List[DCAStep] = field(default_factory=lambda: [
        DCAStep(1, 2.0, 1.0),    # First dip: 2% below, 1x
        DCAStep(2, 5.0, 2.0),    # Second dip: 5% below, 2x
        DCAStep(3, 10.0, 4.0),   # Third dip: 10% below, 4x
        DCAStep(4, 15.0, 8.0),   # Fourth dip: 15% below, 8x
        DCAStep(5, 20.0, 16.0),  # Fifth dip: 20% below, 16x
    ])
    
    # Take profit
    take_profit_pct: float = 3.0  # % profit to exit
    
    # Stop loss
    stop_loss_pct: float = -15.0  # Max loss %
    
    # Max capital
    max_capital: float = 10000.0  # $


@dataclass
class DCAPosition:
    """DCA position state"""
    entry_price: float = 0.0
    total_size: float = 0.0
    total_cost: float = 0.0
    average_price: float = 0.0
    filled_steps: List[int] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)


class DCAStrategy:
    """DCA (Dollar Cost Averaging) strategy"""
    
    def __init__(self, config: DCAConfig = None):
        self.config = config or DCAConfig()
        self.position: Optional[DCAPosition] = None
        self.closed: bool = False
    
    def open_position(self, price: float) -> Dict:
        """Open initial position"""
        self.position = DCAPosition(
            entry_price=price,
            total_size=self.config.base_size / price,
            total_cost=self.config.base_size,
            average_price=price,
        )
        
        # Place base order
        return {
            'side': 'BUY',
            'price': price,
            'quantity': self.config.base_size / price,
            'type': 'MARKET',
            'reason': 'DCA base order',
        }
    
    def check_dca(self, current_price: float) -> Optional[Dict]:
        """Check if DCA step should trigger"""
        if not self.position or self.closed:
            return None
        
        # Calculate current drawdown
        drawdown = (self.position.average_price - current_price) / self.position.average_price * 100
        
        # Check each step
        for step in self.config.steps:
            if step.triggered:
                continue
            
            # Should we trigger this step?
            if drawdown >= step.price_offset:
                # Calculate new size
                new_cost = self.config.base_size * step.size_multiplier
                
                # Check max capital
                if self.position.total_cost + new_cost > self.config.max_capital:
                    continue
                
                # Trigger step
                step.triggered = True
                self.position.filled_steps.append(step.step)
                
                # Add to position
                new_size = new_cost / current_price
                self.position.total_size += new_size
                self.position.total_cost += new_cost
                self.position.average_price = self.position.total_cost / self.position.total_size
                
                return {
                    'side': 'BUY',
                    'price': current_price,
                    'quantity': new_size,
                    'type': 'MARKET',
                    'step': step.step,
                    'reason': f'DCA step {step.step} at {drawdown:.1f}% drawdown',
                }
        
        return None
    
    def check_exit(self, current_price: float) -> Optional[Dict]:
        """Check exit conditions"""
        if not self.position or self.closed:
            return None
        
        pnl_pct = (current_price - self.position.average_price) / self.position.average_price * 100
        
        # Take profit
        if pnl_pct >= self.config.take_profit_pct:
            self.closed = True
            return {
                'action': 'CLOSE',
                'reason': f'Take profit: {pnl_pct:.1f}%',
                'pnl': (current_price - self.position.average_price) * self.position.total_size,
                'pnl_pct': pnl_pct,
            }
        
        # Stop loss
        if pnl_pct <= self.config.stop_loss_pct:
            self.closed = True
            return {
                'action': 'CLOSE',
                'reason': f'Stop loss: {pnl_pct:.1f}%',
                'pnl': (current_price - self.position.average_price) * self.position.total_size,
                'pnl_pct': pnl_pct,
            }
        
        return None
    
    def get_status(self) -> Dict:
        """Get DCA status"""
        if not self.position:
            return {'state': 'no_position'}
        
        return {
            'state': 'closed' if self.closed else 'open',
            'average_price': self.position.average_price,
            'total_cost': self.position.total_cost,
            'total_size': self.position.total_size,
            'steps_filled': len(self.position.filled_steps),
        }


# ============= HYBRID: GRID + DCA =============

class GridDCAStrategy:
    """Combined Grid and DCA strategy"""
    
    def __init__(
        self,
        grid_config: GridConfig = None,
        dca_config: DCAConfig = None,
    ):
        self.grid = GridStrategy(grid_config or GridConfig()) if grid_config else None
        self.dca = DCAStrategy(dca_config or DCAConfig())
        self.mode = "HYBRID"
    
    def get_orders(self) -> List[Dict]:
        """Get pending orders"""
        orders = []
        
        if self.grid:
            orders.extend(self.grid.get_pending_orders())
        
        return orders
    
    def on_price_update(self, current_price: float) -> List[Dict]:
        """Process price update"""
        actions = []
        
        # Check DCA
        if not self.dca.closed:
            dca_order = self.dca.check_dca(current_price)
            if dca_order:
                actions.append(dca_order)
            
            exit_signal = self.dca.check_exit(current_price)
            if exit_signal:
                actions.append(exit_signal)
        
        return actions
    
    def get_status(self) -> Dict:
        """Get combined status"""
        return {
            'mode': self.mode,
            'grid': self.grid.get_status() if self.grid else None,
            'dca': self.dca.get_status(),
        }


# ============= FACTORY =============

def create_grid_strategy(
    lower_price: float,
    upper_price: float,
    grid_count: int = 10,
    position_size: float = 100.0,
    mode: str = "LONG",
) -> GridStrategy:
    """Create grid strategy"""
    config = GridConfig(
        lower_price=lower_price,
        upper_price=upper_price,
        grid_count=grid_count,
        position_size=position_size,
        mode=GridMode(mode.upper()),
    )
    return GridStrategy(config)


def create_dca_strategy(
    base_size: float = 100.0,
    take_profit_pct: float = 3.0,
    stop_loss_pct: float = -15.0,
    max_capital: float = 10000.0,
) -> DCAStrategy:
    """Create DCA strategy"""
    config = DCAConfig(
        base_size=base_size,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        max_capital=max_capital,
    )
    return DCAStrategy(config)


# Export
__all__ = [
    'GridMode',
    'GridLevel',
    'GridConfig',
    'GridStrategy',
    'DCAStep',
    'DCAConfig',
    'DCAPosition',
    'DCAStrategy',
    'GridDCAStrategy',
    'create_grid_strategy',
    'create_dca_strategy',
]