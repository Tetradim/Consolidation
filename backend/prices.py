"""
Price Service for getting real-time option prices
Supports multiple data providers
"""
import os
import logging
import aiohttp
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class PriceError(Exception):
    """Price service error"""
    pass


@dataclass
class OptionQuote:
    """Option quote data"""
    ticker: str
    strike: float
    option_type: str  # CALL or PUT
    expiration: str
    bid: float
    ask: float
    last: float
    volume: int = 0
    open_interest: int = 0
    iv: float = 0.0  # Implied volatility
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    timestamp: datetime = None
    
    @property
    def mid(self) -> float:
        """Mid price"""
        return round((self.bid + self.ask) / 2, 2)
    
    @property
    def spread(self) -> float:
        """Ask - bid"""
        return round(self.ask - self.bid, 2)


class BasePriceService(ABC):
    """Base price service"""
    
    @abstractmethod
    async def get_quote(
        self,
        ticker: str,
        strike: float,
        option_type: str,
        expiration: str
    ) -> Optional[OptionQuote]:
        """Get option quote"""
        pass
    
    @abstractmethod
    async def get_quotes(
        self,
        ticker: str,
        strikes: List[float],
        option_type: str,
        expiration: str
    ) -> List[OptionQuote]:
        """Get multiple option quotes"""
        pass
    
    @abstractmethod
    async def get_underlying_price(self, ticker: str) -> Optional[float]:
        """Get underlying stock price"""
        pass


class IBKRPriceService(BasePriceService):
    """IBKR Gateway price service"""
    
    def __init__(self, gateway_url: str = "https://localhost:5000"):
        self.gateway_url = gateway_url
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def get_quote(
        self,
        ticker: str,
        strike: float,
        option_type: str,
        expiration: str
    ) -> Optional[OptionQuote]:
        try:
            # Look up contract first
            conid = await self._lookup_conid(ticker, option_type, expiration, strike)
            if not conid:
                return None
            
            session = await self._get_session()
            async with session.get(
                f"{self.gateway_url}/v1/iserver/marketdata/snapshot",
                params={'conids': conid},
                ssl=False
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._parse_snapshot(ticker, strike, option_type, expiration, data)
        except Exception as e:
            logger.error(f"IBKR quote error: {e}")
        return None
    
    async def _lookup_conid(self, ticker: str, option_type: str,
                          expiration: str, strike: float) -> Optional[str]:
        """Look up IBKR contract ID"""
        try:
            # Convert expiration format
            exp_formatted = self._format_expiration(expiration)
            
            session = await self._get_session()
            async with session.get(
                f"{self.gateway_url}/v1/api/iserver/secdef/search",
                params={
                    'symbol': ticker,
                    'secType': 'STK',
                    'underlying': ticker,
                },
                ssl=False
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Find matching option contract
                    for sec in data.get('secdef', []):
                        if sec.get('secType') == 'OPT':
                            if (sec.get('strike', strike) == strike and
                                sec.get('putOrCall', '').upper() == option_type.upper()):
                                return sec.get('conId')
        except Exception as e:
            logger.error(f"IBKR conid lookup error: {e}")
        return None
    
    def _parse_snapshot(
        self,
        ticker: str,
        strike: float,
        option_type: str,
        expiration: str,
        data: dict
    ) -> Optional[OptionQuote]:
        """Parse IBKR snapshot data"""
        for conid, quotes in data.items():
            if not quotes:
                continue
            bid = quotes.get('bid', 0) or 0
            ask = quotes.get('ask', 0) or 0
            last = quotes.get('last', 0) or bid or ask
            return OptionQuote(
                ticker=ticker,
                strike=strike,
                option_type=option_type,
                expiration=expiration,
                bid=bid,
                ask=ask,
                last=last,
                volume=quotes.get('volume', 0) or 0,
                open_interest=quotes.get('open_interest', 0) or 0,
                iv=self._parse_float(quotes.get('impliedVolatility')),
                delta=self._parse_float(quotes.get('delta', 0)),
                gamma=self._parse_float(quotes.get('gamma', 0)),
                theta=self._parse_float(quotes.get('theta', 0)),
                timestamp=datetime.now(timezone.utc)
            )
        return None
    
    def _parse_float(self, value) -> float:
        try:
            return float(value) if value else 0.0
        except:
            return 0.0
    
    def _format_expiration(self, expiration: str) -> str:
        """Convert expiration to IBKR format"""
        # Already in YYMMDD or YYYYMMDD
        return expiration.replace('/', '')
    
    async def get_quotes(
        self,
        ticker: str,
        strikes: List[float],
        option_type: str,
        expiration: str
    ) -> List[OptionQuote]:
        quotes = []
        for strike in strikes:
            quote = await self.get_quote(ticker, strike, option_type, expiration)
            if quote:
                quotes.append(quote)
        return quotes
    
    async def get_underlying_price(self, ticker: str) -> Optional[float]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.gateway_url}/v1/iserver/contract",
                params={'conid': ticker},  # Stock conid
                ssl=False
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._parse_float(data.get('price'))
        except Exception as e:
            logger.error(f"IBKR underlying price error: {e}")
        return None
    
    async def close(self):
        if self._session:
            await self._session.close()


class AlpacaPriceService(BasePriceService):
    """Alpaca market data service"""
    
    def __init__(self, api_key: str = None, secret_key: str = None):
        self.api_key = api_key or os.environ.get('ALPACA_API_KEY', '')
        self.secret_key = secret_key or os.environ.get('ALPACA_SECRET_KEY', '')
        self.base_url = 'https://data.alpaca.markets'
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def get_quote(
        self,
        ticker: str,
        strike: float,
        option_type: str,
        expiration: str
    ) -> Optional[OptionQuote]:
        try:
            symbol = f"{ticker}{expiration.replace('/', '')}{int(strike)}{option_type[0]}"
            
            session = await self._get_session()
            headers = {
                'APCA-API-KEY-ID': self.api_key,
                'APCA-API-SECRET-KEY': self.secret_key,
            }
            
            async with session.get(
                f"{self.base_url}/v2/stocks/{symbol}/quotes/latest",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    quote = data.get('quote', {})
                    return OptionQuote(
                        ticker=ticker,
                        strike=strike,
                        option_type=option_type,
                        expiration=expiration,
                        bid=self._parse_float(quote.get('bid_price')),
                        ask=self._parse_float(quote.get('ask_price')),
                        last=self._parse_float(quote.get('last_price')),
                        timestamp=datetime.now(timezone.utc)
                    )
        except Exception as e:
            logger.error(f"Alpaca quote error: {e}")
        return None
    
    def _parse_float(self, value) -> float:
        try:
            return float(value) if value else 0.0
        except:
            return 0.0
    
    async def get_quotes(
        self,
        ticker: str,
        strikes: List[float],
        option_type: str,
        expiration: str
    ) -> List[OptionQuote]:
        quotes = []
        for strike in strikes:
            quote = await self.get_quote(ticker, strike, option_type, expiration)
            if quote:
                quotes.append(quote)
        return quotes
    
    async def get_underlying_price(self, ticker: str) -> Optional[float]:
        try:
            session = await self._get_session()
            headers = {
                'APCA-API-KEY-ID': self.api_key,
                'APCA-API-SECRET-KEY': self.secret_key,
            }
            
            async with session.get(
                f"{self.base_url}/v2/stocks/{ticker}/quotes/latest",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    quote = data.get('quote', {})
                    return self._parse_float(quote.get('last_price'))
        except Exception as e:
            logger.error(f"Alpaca underlying error: {e}")
        return None
    
    async def close(self):
        if self._session:
            await self._session.close()


class MockPriceService(BasePriceService):
    """Mock price service for testing"""
    
    def __init__(self, base_price: float = 100.0):
        self.base_price = base_price
    
    async def get_quote(
        self,
        ticker: str,
        strike: float,
        option_type: str,
        expiration: str
    ) -> Optional[OptionQuote]:
        # Mock pricing based on moneyness
        itm = (option_type == 'CALL' and strike < self.base_price) or \
              (option_type == 'PUT' and strike > self.base_price)
        
        if itm:
            price = self.base_price - strike if option_type == 'CALL' else strike - self.base_price
            price = max(price * 1.5, 0.5)  # ITM premium
        else:
            # OTM - estimate based on expiration
            price = 1.0  # Default OTM price
        
        return OptionQuote(
            ticker=ticker,
            strike=strike,
            option_type=option_type,
            expiration=expiration,
            bid=round(price * 0.98, 2),
            ask=round(price * 1.02, 2),
            last=price,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def get_quotes(
        self,
        ticker: str,
        strikes: List[float],
        option_type: str,
        expiration: str
    ) -> List[OptionQuote]:
        quotes = []
        for strike in strikes:
            quote = await self.get_quote(ticker, strike, option_type, expiration)
            if quote:
                quotes.append(quote)
        return quotes
    
    async def get_underlying_price(self, ticker: str) -> Optional[float]:
        return self.base_price


class PriceServiceFactory:
    """Factory for creating price services"""
    
    @staticmethod
    def create(service_type: str, **kwargs) -> BasePriceService:
        services = {
            'ibkr': IBKRPriceService,
            'alpaca': AlpacaPriceService,
            'mock': MockPriceService,
        }
        
        if service_type not in services:
            logger.warning(f"Unknown price service: {service_type}, using mock")
            return MockPriceService()
        
        return services[service_type](**kwargs)


# Global price service instance
_price_service: Optional[BasePriceService] = None


def get_price_service() -> BasePriceService:
    """Get global price service"""
    global _price_service
    if _price_service is None:
        service_type = os.environ.get('PRICE_SERVICE', 'mock')
        _price_service = PriceServiceFactory.create(service_type)
    return _price_service


def set_price_service(service: BasePriceService):
    """Set global price service"""
    global _price_service
    _price_service = service