"""
Universe Selection - Stock Screening & Filtering
Filter stocks by criteria, sector, technicals, etc.
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class UniverseFilter(Enum):
    """Types of universe filters"""
    SECTOR = "sector"
    MARKET_CAP = "market_cap"
    VOLUME = "volume"
    PRICE = "price"
    IV = "iv"
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"
    RSI = "rsi"
    CUSTOM = "custom"


@dataclass
class UniverseConfig:
    """Universe selection configuration"""
    # Sector filters
    sectors: List[str] = field(default_factory=list)  # Tech, Finance, etc.
    
    # Price filters
    min_price: float = 1.0
    max_price: float = 10000.0
    
    # Volume filters
    min_volume: int = 1000000
    min_avg_volume: int = 500000
    
    # Market cap filters
    min_market_cap: float = 0  # In billions
    max_market_cap: float = float('inf')
    
    # IV filters
    min_iv: float = 0
    max_iv: float = 200
    
    # Technical filters
    min_momentum: float = -50  # % change
    max_momentum: float = 50
    rsi_min: float = 0
    rsi_max: float = 100
    
    # Option filters
    has_options: bool = True
    min_option_volume: int = 1000
    
    # Count limits
    max_stocks: int = 100
    rank_by: str = "volume"  # volume, momentum, iv


@dataclass
class Stock:
    """Stock data"""
    symbol: str
    name: str = ""
    sector: str = ""
    
    # Price data
    price: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    
    # Volume
    volume: int = 0
    avg_volume: int = 0
    
    # Market data
    market_cap: float = 0.0
    
    # Technicals
    rsi: float = 50.0
    momentum: float = 0.0
    
    # Options
    has_options: bool = False
    option_volume: int = 0
    iv: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'sector': self.sector,
            'price': self.price,
            'change': self.change,
            'change_pct': self.change_pct,
            'volume': self.volume,
            'avg_volume': self.avg_volume,
            'market_cap': self.market_cap,
            'rsi': self.rsi,
            'momentum': self.momentum,
            'iv': self.iv,
        }


class UniverseSelector:
    """Stock universe selector"""
    
    # Sector mapping
    SECTOR_MAP = {
        # Tech
        'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
        'GOOG': 'Technology', 'META': 'Technology', 'NVDA': 'Technology',
        'AMD': 'Technology', 'INTC': 'Technology', 'CRM': 'Technology',
        'ADBE': 'Technology', 'ORCL': 'Technology', 'CSCO': 'Technology',
        'IBM': 'Technology', 'QCOM': 'Technology', 'TXN': 'Technology',
        # Finance
        'JPM': 'Financial', 'BAC': 'Financial', 'WFC': 'Financial',
        'GS': 'Financial', 'MS': 'Financial', 'C': 'Financial',
        'BLK': 'Financial', 'AXP': 'Financial', 'V': 'Financial',
        'MA': 'Financial', 'PYPL': 'Financial', 'SQ': 'Financial',
        # Healthcare
        'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare',
        'ABBV': 'Healthcare', 'MRK': 'Healthcare', 'LLY': 'Healthcare',
        'TMO': 'Healthcare', 'DHR': 'Healthcare', 'ABT': 'Healthcare',
        # Energy
        'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy',
        'SLB': 'Energy', 'EOG': 'Energy', 'MPC': 'Energy',
        # Consumer
        'AMZN': 'Consumer', 'WMT': 'Consumer', 'HD': 'Consumer',
        'TGT': 'Consumer', 'LOW': 'Consumer', 'NKE': 'Consumer',
        'SBUX': 'Consumer', 'MCD': 'Consumer', 'DIS': 'Consumer',
        # Industrial
        'BA': 'Industrial', 'CAT': 'Industrial', 'GE': 'Industrial',
        'MMM': 'Industrial', 'RTX': 'Industrial', 'UPS': 'Industrial',
        # Telecom
        'T': 'Telecom', 'VZ': 'Telecom', 'TMUS': 'Telecom',
        # Real Estate
        'PLD': 'Real Estate', 'AMT': 'Real Estate', 'CCI': 'Real Estate',
    }
    
    def __init__(self, config: UniverseConfig = None):
        self.config = config or UniverseConfig()
        self._stocks: Dict[str, Stock] = {}
    
    def add_stock(self, stock: Stock) -> None:
        """Add stock to universe"""
        self._stocks[stock.symbol] = stock
    
    def add_stocks(self, stocks: List[Stock]) -> None:
        """Add multiple stocks"""
        for stock in stocks:
            self.add_stock(stock)
    
    def get_stock(self, symbol: str) -> Optional[Stock]:
        """Get stock by symbol"""
        return self._stocks.get(symbol)
    
    def filter(self) -> List[Stock]:
        """Apply filters and return filtered universe"""
        results = []
        
        for stock in self._stocks.values():
            # Sector filter
            if self.config.sectors:
                if stock.sector not in self.config.sectors:
                    continue
            
            # Price filter
            if stock.price < self.config.min_price or stock.price > self.config.max_price:
                continue
            
            # Volume filter
            if stock.volume < self.config.min_volume:
                continue
            if stock.avg_volume < self.config.min_avg_volume:
                continue
            
            # Market cap filter
            if stock.market_cap > 0:
                if stock.market_cap < self.config.min_market_cap * 1e9:
                    continue
                if stock.market_cap > self.config.max_market_cap * 1e9:
                    continue
            
            # IV filter
            if stock.iv > 0:
                if stock.iv < self.config.min_iv or stock.iv > self.config.max_iv:
                    continue
            
            # Momentum filter
            if stock.momentum < self.config.min_momentum or stock.momentum > self.config.max_momentum:
                continue
            
            # RSI filter
            if stock.rsi < self.config.rsi_min or stock.rsi > self.config.rsi_max:
                continue
            
            # Options filter
            if self.config.has_options and not stock.has_options:
                continue
            
            results.append(stock)
        
        # Rank and limit
        results = self._rank(results)
        
        return results[:self.config.max_stocks]
    
    def _rank(self, stocks: List[Stock]) -> List[Stock]:
        """Rank stocks by configured metric"""
        if self.config.rank_by == "volume":
            return sorted(stocks, key=lambda x: x.volume, reverse=True)
        elif self.config.rank_by == "momentum":
            return sorted(stocks, key=lambda x: x.momentum, reverse=True)
        elif self.config.rank_by == "iv":
            return sorted(stocks, key=lambda x: x.iv, reverse=True)
        elif self.config.rank_by == "price":
            return sorted(stocks, key=lambda x: x.price)
        
        return stocks
    
    def get_sectors(self) -> Dict[str, int]:
        """Get sector distribution"""
        sectors = {}
        for stock in self._stocks.values():
            sectors[stock.sector] = sectors.get(stock.sector, 0) + 1
        return sectors
    
    def get_top_by_sector(self, n: int = 5) -> Dict[str, List[Stock]]:
        """Get top N stocks per sector"""
        by_sector = {}
        
        for stock in self._stocks.values():
            if stock.sector not in by_sector:
                by_sector[stock.sector] = []
            by_sector[stock.sector].append(stock)
        
        # Sort each sector
        for sector in by_sector:
            by_sector[sector] = sorted(
                by_sector[sector],
                key=lambda x: x.volume,
                reverse=True
            )[:n]
        
        return by_sector


class UniverseProvider:
    """Base class for universe data providers"""
    
    async def get_universe(self) -> List[Stock]:
        """Get full universe"""
        raise NotImplementedError
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Stock]:
        """Get quotes for symbols"""
        raise NotImplementedError


class MockUniverseProvider(UniverseProvider):
    """Mock universe for testing"""
    
    async def get_universe(self) -> List[Stock]:
        """Generate mock universe"""
        stocks = []
        
        # Popular tickers
        tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META',  # Tech
            'JPM', 'BAC', 'WFC', 'GS',  # Finance
            'JNJ', 'PFE', 'UNH', 'MRK',  # Healthcare
            'XOM', 'CVX', 'COP',  # Energy
            'WMT', 'HD', 'TGT',  # Consumer
            'BA', 'CAT', 'GE',  # Industrial
            'T', 'VZ',  # Telecom
            'PLD', 'AMT',  # Real Estate
        ]
        
        import random
        random.seed(42)
        
        for ticker in tickers:
            price = random.uniform(20, 500)
            stock = Stock(
                symbol=ticker,
                name=ticker,
                sector=UniverseSelector.SECTOR_MAP.get(ticker, 'Other'),
                price=price,
                change=random.uniform(-5, 5),
                change_pct=random.uniform(-10, 10),
                volume=random.randint(1000000, 50000000),
                avg_volume=random.randint(500000, 20000000),
                market_cap=random.uniform(10, 2000) * 1e9,
                rsi=random.uniform(30, 70),
                momentum=random.uniform(-20, 20),
                has_options=random.random() > 0.1,
                option_volume=random.randint(1000, 50000),
                iv=random.uniform(15, 60),
            )
            stocks.append(stock)
        
        return stocks


# ============= FACTORY =============

async def get_universe(provider: str = "MOCK") -> List[Stock]:
    """Get stock universe"""
    providers = {
        "MOCK": MockUniverseProvider,
    }
    
    provider_class = providers.get(provider, MockUniverseProvider)
    p = provider_class()
    
    return await p.get_universe()


def create_universe_config(
    sectors: List[str] = None,
    min_price: float = 1.0,
    max_price: float = 10000.0,
    min_volume: int = 1000000,
    **kwargs,
) -> UniverseConfig:
    """Create universe config"""
    return UniverseConfig(
        sectors=sectors or [],
        min_price=min_price,
        max_price=max_price,
        min_volume=min_volume,
        **kwargs,
    )


# Export
__all__ = [
    'UniverseFilter',
    'UniverseConfig',
    'Stock',
    'UniverseSelector',
    'UniverseProvider',
    'MockUniverseProvider',
    'get_universe',
    'create_universe_config',
]