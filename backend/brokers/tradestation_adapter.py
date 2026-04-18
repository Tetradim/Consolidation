"""TradeStation adapter — professional trading platform with OAuth REST API."""
import logging
from .base import BrokerAdapter, BrokerOrder, BrokerPosition, BrokerAccountInfo

logger = logging.getLogger("SentinelPulse")
API_BASE = "https://api.tradestation.com/v3"


class TradeStationAdapter(BrokerAdapter):
    broker_id = "tradestation"

    def __init__(self, config: dict):
        super().__init__(config)
        self._access_token = ""

    def _headers(self):
        return {"Authorization": f"Bearer {self._access_token}"}

    async def _refresh_token(self) -> bool:
        try:
            session = await self._get_session()
            data = {
                "grant_type": "refresh_token",
                "client_id": self.config.get("ts_client_id", ""),
                "client_secret": self.config.get("ts_client_secret", ""),
                "refresh_token": self.config.get("ts_refresh_token", ""),
            }
            async with session.post("https://signin.tradestation.com/oauth/token", data=data) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    self._access_token = token_data.get("access_token", "")
                    self.connected = True
                    return True
        except Exception as e:
            logger.error(f"TradeStation token refresh error: {e}")
        return False

    async def check_connection(self) -> bool:
        if self._access_token:
            try:
                session = await self._get_session()
                async with session.get(f"{API_BASE}/brokerage/accounts", headers=self._headers()) as resp:
                    if resp.status == 200:
                        self.connected = True
                        return True
                    if resp.status == 401:
                        return await self._refresh_token()
            except Exception as e:
                logger.error(f"TradeStation connection error: {e}")
        return await self._refresh_token()

    async def get_account(self) -> BrokerAccountInfo:
        session = await self._get_session()
        async with session.get(f"{API_BASE}/brokerage/accounts", headers=self._headers()) as resp:
            data = await resp.json()
            accts = data.get("Accounts", [])
            if accts:
                a = accts[0]
                return BrokerAccountInfo(
                    balance=float(a.get("CashBalance", 0)),
                    buying_power=float(a.get("BuyingPower", 0)),
                    equity=float(a.get("AccountBalance", 0)),
                )
        return BrokerAccountInfo(balance=0, buying_power=0, equity=0)

    async def get_positions(self) -> list[BrokerPosition]:
        session = await self._get_session()
        async with session.get(f"{API_BASE}/brokerage/accounts/positions", headers=self._headers()) as resp:
            data = await resp.json()
            return [
                BrokerPosition(
                    symbol=p.get("Symbol", ""),
                    quantity=float(p.get("Quantity", 0)),
                    avg_entry=float(p.get("AveragePrice", 0)),
                    current_price=float(p.get("Last", 0)),
                    market_value=float(p.get("MarketValue", 0)),
                    unrealized_pnl=float(p.get("UnrealizedProfitLoss", 0)),
                )
                for p in data.get("Positions", [])
            ]

    async def place_order(self, order: BrokerOrder) -> BrokerOrder:
        session = await self._get_session()
        payload = {
            "Symbol": order.symbol,
            "Quantity": str(int(order.quantity)),
            "OrderType": order.order_type.value.capitalize(),
            "TradeAction": order.side.value,
            "TimeInForce": {"Duration": "DAY"},
            "Route": "Intelligent",
        }
        if order.limit_price:
            payload["LimitPrice"] = str(order.limit_price)
        if order.stop_price:
            payload["StopPrice"] = str(order.stop_price)
        async with session.post(f"{API_BASE}/orderexecution/orders", headers=self._headers(), json=payload) as resp:
            data = await resp.json()
            if resp.status in (200, 201):
                orders = data.get("Orders", [])
                order.broker_order_id = str(orders[0].get("OrderID", "")) if orders else ""
                order.status = "submitted"
            else:
                order.status = "rejected"
                order.error = str(data)
        return order

    async def cancel_order(self, broker_order_id: str) -> bool:
        session = await self._get_session()
        async with session.delete(f"{API_BASE}/orderexecution/orders/{broker_order_id}", headers=self._headers()) as resp:
            return resp.status == 200

    async def get_quote(self, symbol: str) -> float:
        session = await self._get_session()
        async with session.get(f"{API_BASE}/marketdata/quotes/{symbol}", headers=self._headers()) as resp:
            data = await resp.json()
            quotes = data.get("Quotes", [])
            return float(quotes[0].get("Last", 0)) if quotes else 0.0
