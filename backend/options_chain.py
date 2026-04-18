"""
Options Chain Loader and Smart Strike Selection
Fetches options chain data and helps select optimal strikes
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class OptionType(Enum):
    CALL = "CALL"
    PUT = "PUT"


class StrikeSelectionStrategy(Enum):
    """Strategies for selecting strikes"""
    ATM = "ATM"  # At-the-money
    OTM = "OTM"  # Out-of-the-money
    ITM = "ITM"  # In-the-money
    DELTA = "DELTA"  # Target delta
    RISK_REWARD = "RISK_REWARD"  # Best risk/reward
    HIGH_IV = "HIGH_IV"  # Highest IV
    liquidity = "LIQUIDITY"  # Most liquid


@dataclass
class OptionContract:
    """Single option contract"""
    symbol: str
    ticker: str
    strike: float
    option_type: OptionType
    expiration: datetime
    
    # Prices
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    mid: float = 0.0
    
    # Greeks
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0
    
    # IV
    iv: float = 0.0
    
    # Volume
    volume: int = 0
    open_interest: int = 0
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid
    
    @property
    def spread_pct(self) -> float:
        if self.mid > 0:
            return (self.spread / self.mid) * 100
        return 0.0
    
    @property
    def extrinsic(self) -> float:
        """Time value"""
        if self.option_type == OptionType.CALL:
            return max(0, self.mid - max(0, self.strike - self.underlying_price))
        else:
            return max(0, self.mid - max(0, self.underlying_price - self.strike))
    
    underlying_price: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'ticker': self.ticker,
            'strike': self.strike,
            'option_type': self.option_type.value,
            'expiration': self.expiration.isoformat(),
            'bid': self.bid,
            'ask': self.ask,
            'mid': self.mid,
            'iv': self.iv,
            'delta': self.delta,
            'theta': self.theta,
            'volume': self.volume,
            'spread': self.spread,
        }


@dataclass
class OptionsChain:
    """Full options chain for a ticker"""
    ticker: str
    underlying_price: float
    expiration: datetime
    
    # All strikes
    calls: List[OptionContract] = field(default_factory=list)
    puts: List[OptionContract] = field(default_factory=list)
    
    # Chain metadata
    fetched_at: datetime = field(default_factory=datetime.now)
    
    def get_strikes(self, option_type: OptionType = None) -> List[float]:
        """Get all strikes"""
        contracts = self.calls if option_type == OptionType.CALL or option_type is None else self.puts
        if option_type == OptionType.PUT:
            contracts = self.puts
        return sorted([c.strike for c in contracts])
    
    def get_contracts(
        self,
        option_type: OptionType = None,
        min_bid: float = 0.0,
        min_oi: int = 0,
    ) -> List[OptionContract]:
        """Get contracts with filters"""
        contracts = []
        if option_type == OptionType.CALL or option_type is None:
            contracts.extend(self.calls)
        if option_type == OptionType.PUT or option_type is None:
            contracts.extend(self.puts)
        
        filtered = [c for c in contracts if c.bid >= min_bid and c.open_interest >= min_oi]
        return sorted(filtered, key=lambda x: x.strike)
    
    def find_atm(self, option_type: OptionType = OptionType.CALL) -> Optional[OptionContract]:
        """Find ATM contract"""
        contracts = self.calls if option_type == OptionType.CALL else self.puts
        if not contracts:
            return None
        
        # Find strike closest to underlying
        return min(contracts, key=lambda x: abs(x.strike - self.underlying_price))
    
    def find_otm(
        self,
        option_type: OptionType,
        pct_otm: float = 5.0,
    ) -> Optional[OptionContract]:
        """Find OTM contract"""
        contracts = self.calls if option_type == OptionType.CALL else self.puts
        if not contracts:
            return None
        
        if option_type == OptionType.CALL:
            target = self.underlying_price * (1 + pct_otm / 100)
        else:
            target = self.underlying_price * (1 - pct_otm / 100)
        
        return min(contracts, key=lambda x: abs(x.strike - target))
    
    def find_itm(
        self,
        option_type: OptionType,
        pct_itm: float = 10.0,
    ) -> Optional[OptionContract]:
        """Find ITM contract"""
        contracts = self.calls if option_type == OptionType.CALL else self.puts
        if not contracts:
            return None
        
        if option_type == OptionType.CALL:
            target = self.underlying_price * (1 + pct_itm / 100)
        else:
            target = self.underlying_price * (1 - pct_itm / 100)
        
        return min(contracts, key=lambda x: abs(x.strike - target))
    
    def find_by_delta(
        self,
        option_type: OptionType,
        target_delta: float,
    ) -> Optional[OptionContract]:
        """Find contract by target delta"""
        contracts = self.calls if option_type == OptionType.CALL else self.puts
        if not contracts:
            return None
        
        return min(contracts, key=lambda x: abs(x.delta - target_delta))
    
    def find_best_reward(
        self,
        option_type: OptionType,
        min_prob: float = 10.0,
    ) -> Optional[OptionContract]:
        """Find best risk/reward"""
        contracts = self.calls if option_type == OptionType.CALL else self.puts
        
        best = None
        best_ratio = 0
        
        for c in contracts:
            if c.bid < min_prob:
                continue
            
            # Risk: probability of losing (from delta)
            risk = abs(c.delta) * 100
            
            # Reward: potential gain
            if c.strike > self.underlying_price:
                reward = (c.strike - self.underlying_price) / c.mid * 100
            else:
                reward = c.mid * 100
            
            if risk > 0 and reward > best_ratio:
                best_ratio = reward / risk
                best = c
        
        return best
    
    def find_high_iv(
        self,
        option_type: OptionType,
        top_n: int = 5,
    ) -> List[OptionContract]:
        """Find highest IV contracts"""
        contracts = self.calls if option_type == OptionType.CALL else self.puts
        
        return sorted(contracts, key=lambda x: x.iv, reverse=True)[:top_n]
    
    def find_most_liquid(
        self,
        option_type: OptionType,
        top_n: int = 5,
    ) -> List[OptionContract]:
        """Find most liquid contracts"""
        contracts = self.calls if option_type == OptionType.CALL else self.puts
        
        return sorted(contracts, key=lambda x: x.open_interest, reverse=True)[:top_n]


class StrikeSelector:
    """Smart strike selection"""
    
    def __init__(self, chain: OptionsChain):
        self.chain = chain
    
    def select(
        self,
        strategy: StrikeSelectionStrategy,
        option_type: OptionType = OptionType.CALL,
        **kwargs,
    ) -> Optional[OptionContract]:
        """Select strike based on strategy"""
        
        if strategy == StrikeSelectionStrategy.ATM:
            return self.chain.find_atm(option_type)
        
        elif strategy == StrikeSelectionStrategy.OTM:
            pct = kwargs.get('pct_otm', 5.0)
            return self.chain.find_otm(option_type, pct)
        
        elif strategy == StrikeSelectionStrategy.ITM:
            pct = kwargs.get('pct_itm', 10.0)
            return self.chain.find_itm(option_type, pct)
        
        elif strategy == StrikeSelectionStrategy.DELTA:
            target = kwargs.get('target_delta', 0.30)
            return self.chain.find_by_delta(option_type, target)
        
        elif strategy == StrikeSelectionStrategy.RISK_REWARD:
            min_prob = kwargs.get('min_prob', 10.0)
            return self.chain.find_best_reward(option_type, min_prob)
        
        elif strategy == StrikeSelectionStrategy.HIGH_IV:
            return self.chain.find_high_iv(option_type)[0] if self.chain.find_high_iv(option_type) else None
        
        elif strategy == StrikeSelectionStrategy.liquidity:
            top = self.chain.find_most_liquid(option_type)
            return top[0] if top else None
        
        return None
    
    def select_multi(
        self,
        strategies: List[Tuple[StrikeSelectionStrategy, OptionType]],
    ) -> Dict[str, OptionContract]:
        """Select multiple strikes"""
        results = {}
        
        for strategy, option_type in strategies:
            key = f"{strategy.value}_{option_type.value}"
            results[key] = self.select(strategy, option_type)
        
        return results


# ============= BROKER INTEGRATIONS =============

class OptionsChainProvider:
    """Base provider for options chain"""
    
    async def get_chain(
        self,
        ticker: str,
        expiration: str = None,
    ) -> OptionsChain:
        """Get options chain"""
        raise NotImplementedError


class IBKRChainProvider(OptionsChainProvider):
    """IBKR options chain"""
    
    def __init__(self, gateway_url: str = "https://localhost:5000"):
        self.gateway_url = gateway_url
    
    async def get_chain(
        self,
        ticker: str,
        expiration: str = None,
    ) -> OptionsChain:
        """Get chain from IBKR"""
        # Would use IBKR API
        # Placeholder - returns mock data
        return OptionsChain(
            ticker=ticker,
            underlying_price=450.0,
            expiration=datetime.now() + timedelta(days=30),
        )


class AlpacaChainProvider(OptionsChainProvider):
    """Alpaca options chain"""
    
    def __init__(self, api_key: str = "", secret_key: str = ""):
        self.api_key = api_key
        self.secret_key = secret_key
    
    async def get_chain(
        self,
        ticker: str,
        expiration: str = None,
    ) -> OptionsChain:
        """Get chain from Alpaca"""
        return OptionsChain(
            ticker=ticker,
            underlying_price=450.0,
            expiration=datetime.now() + timedelta(days=30),
        )


class MockChainProvider(OptionsChainProvider):
    """Mock chain for testing"""
    
    async def get_chain(
        self,
        ticker: str,
        expiration: str = None,
    ) -> OptionsChain:
        """Generate mock chain"""
        underlying = 450.0
        exp_date = datetime.now() + timedelta(days=30)
        
        calls = []
        puts = []
        
        for strike in range(int(underlying * 0.7), int(underlying * 1.3), 5):
            # Calls
            call = OptionContract(
                symbol=f"{ticker}{exp_date.strftime('%y%m%d')}{strike}C",
                ticker=ticker,
                strike=float(strike),
                option_type=OptionType.CALL,
                expiration=exp_date,
            )
            call.underlying_price = underlying
            
            if strike < underlying:
                call.bid = (underlying - strike) * 0.9
                call.ask = (underlying - strike) * 1.1
            elif strike == underlying:
                call.bid = 8.0
                call.ask = 9.0
            else:
                call.bid = 1.0
                call.ask = 1.5
            
            call.last = (call.bid + call.ask) / 2
            call.mid = call.last
            call.iv = 25.0 + (abs(strike - underlying) / underlying) * 20
            call.delta = -0.5 if strike > underlying else 0.5
            call.gamma = 0.05
            call.theta = -0.10
            call.volume = 1000
            call.open_interest = 5000
            
            calls.append(call)
            
            # Puts
            put = OptionContract(
                symbol=f"{ticker}{exp_date.strftime('%y%m%d')}{strike}P",
                ticker=ticker,
                strike=float(strike),
                option_type=OptionType.PUT,
                expiration=exp_date,
            )
            put.underlying_price = underlying
            
            if strike > underlying:
                put.bid = (strike - underlying) * 0.9
                put.ask = (strike - underlying) * 1.1
            elif strike == underlying:
                put.bid = 8.0
                put.ask = 9.0
            else:
                put.bid = 1.0
                put.ask = 1.5
            
            put.last = (put.bid + put.ask) / 2
            put.mid = put.last
            put.iv = 25.0 + (abs(strike - underlying) / underlying) * 20
            put.delta = 0.5 if strike < underlying else -0.5
            put.gamma = 0.05
            put.theta = -0.10
            put.volume = 1000
            put.open_interest = 5000
            
            puts.append(put)
        
        return OptionsChain(
            ticker=ticker,
            underlying_price=underlying,
            expiration=exp_date,
            calls=calls,
            puts=puts,
        )


# ============= HELPER FUNCTIONS =============

async def get_options_chain(
    ticker: str,
    broker: str = "MOCK",
    **kwargs,
) -> OptionsChain:
    """Get options chain"""
    
    providers = {
        "IBKR": IBKRChainProvider,
        "ALPACA": AlpacaChainProvider,
        "MOCK": MockChainProvider,
    }
    
    provider_class = providers.get(broker, MockChainProvider)
    provider = provider_class(**kwargs)
    
    return await provider.get_chain(ticker)


async def select_strike(
    ticker: str,
    strategy: StrikeSelectionStrategy,
    option_type: OptionType = OptionType.CALL,
    broker: str = "MOCK",
    **kwargs,
) -> Optional[OptionContract]:
    """Select optimal strike"""
    chain = await get_options_chain(ticker, broker)
    selector = StrikeSelector(chain)
    
    return selector.select(strategy, option_type, **kwargs)


# Export
__all__ = [
    'OptionType',
    'StrikeSelectionStrategy',
    'OptionContract',
    'OptionsChain',
    'StrikeSelector',
    'OptionsChainProvider',
    'IBKRChainProvider',
    'AlpacaChainProvider',
    'MockChainProvider',
    'get_options_chain',
    'select_strike',
]