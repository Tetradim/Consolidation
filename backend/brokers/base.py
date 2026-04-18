"""Base broker adapter — all broker implementations inherit from this.
Adapted from user's existing BaseBrokerClient with aiohttp session pooling."""
import aiohttp
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("SentinelPulse")

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10, connect=5)


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


@dataclass
class BrokerOrder:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    broker_order_id: str = ""
    status: str = "pending"
    filled_price: float = 0.0
    filled_quantity: float = 0.0
    error: str = ""
    # Idempotency tracking
    idempotency_key: str = ""  # Unique key to prevent duplicate orders
    client_order_id: str = ""  # Client-provided order ID for tracking
    submitted_at: str = ""     # Timestamp when order was submitted


@dataclass
class BrokerPosition:
    symbol: str
    quantity: float
    avg_entry: float
    current_price: float
    market_value: float
    unrealized_pnl: float


@dataclass
class BrokerAccountInfo:
    balance: float
    buying_power: float
    equity: float
    currency: str = "USD"


class BrokerRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class BrokerRiskWarning:
    level: BrokerRiskLevel
    message: str


@dataclass
class BrokerInfo:
    id: str
    name: str
    description: str
    supported: bool = False
    auth_fields: list = field(default_factory=list)
    risk_warning: Optional[BrokerRiskWarning] = None
    docs_url: str = ""
    color: str = "#666666"


class OrderValidationError(Exception):
    pass


TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}$')


class BrokerAdapter(ABC):
    """Abstract base class for all broker adapters with aiohttp session pooling."""

    broker_id: str = ""

    def __init__(self, config: dict):
        self.config = config
        self.connected = False
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, keepalive_timeout=30)
            self._session = aiohttp.ClientSession(connector=connector, timeout=DEFAULT_TIMEOUT, raise_for_status=False)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def validate_stock_order(self, symbol: str, side: str, quantity: float, price: float) -> tuple[bool, str]:
        errors = []
        if not symbol or not TICKER_PATTERN.match(symbol.upper()):
            errors.append(f"Invalid symbol: '{symbol}'")
        if side.upper() not in ('BUY', 'SELL'):
            errors.append(f"Invalid side: '{side}'")
        if quantity <= 0 or quantity > 100000:
            errors.append(f"Invalid quantity: {quantity}")
        if price < 0 or price > 1000000:
            errors.append(f"Invalid price: {price}")
        return (True, "") if not errors else (False, "; ".join(errors))

    @abstractmethod
    async def check_connection(self) -> bool:
        """Authenticate/verify connection. Returns True on success."""

    @abstractmethod
    async def get_account(self) -> BrokerAccountInfo:
        """Retrieve account balance and buying power."""

    @abstractmethod
    async def get_positions(self) -> list[BrokerPosition]:
        """Retrieve all open positions."""

    @abstractmethod
    async def place_order(self, order: BrokerOrder) -> BrokerOrder:
        """Submit an order. Returns the order with updated status/ID."""

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel a pending order."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> float:
        """Get the latest quote price for a symbol."""
