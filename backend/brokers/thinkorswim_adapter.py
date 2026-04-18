"""Thinkorswim (Schwab) adapter — same API as TD Ameritrade post-acquisition."""
import base64
import logging
from .base import BrokerAdapter, BrokerOrder, BrokerPosition, BrokerAccountInfo

logger = logging.getLogger("SentinelPulse")
API_BASE = "https://api.schwabapi.com"


class ThinkorswimAdapter(BrokerAdapter):
    broker_id = "thinkorswim"

    def __init__(self, config: dict):
        super().__init__(config)
        self._access_token = ""

    def _headers(self):
        return {"Authorization": f"Bearer {self._access_token}"}

    async def _refresh_token(self) -> bool:
        consumer_key = self.config.get("tos_consumer_key", "")
        refresh_token = self.config.get("tos_refresh_token", "")
        if not consumer_key or not refresh_token:
            return False
        try:
            creds = base64.b64encode(f"{consumer_key}:".encode()).decode()
            headers = {"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"}
            session = await self._get_session()
            async with session.post(f"{API_BASE}/v1/oauth/token", headers=headers,
                                    data={"grant_type": "refresh_token", "refresh_token": refresh_token}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._access_token = data.get("access_token", "")
                    self.connected = True
                    return True
        except Exception as e:
            logger.error(f"Thinkorswim token refresh error: {e}")
        return False

    async def check_connection(self) -> bool:
        if self._access_token:
            try:
                session = await self._get_session()
                async with session.get(f"{API_BASE}/trader/v1/accounts", headers=self._headers()) as resp:
                    if resp.status == 200:
                        self.connected = True
                        return True
                    if resp.status == 401:
                        return await self._refresh_token()
            except Exception as e:
                logger.error(f"Thinkorswim connection error: {e}")
        return await self._refresh_token()

    async def get_account(self) -> BrokerAccountInfo:
        session = await self._get_session()
        async with session.get(f"{API_BASE}/trader/v1/accounts", headers=self._headers()) as resp:
            data = await resp.json()
            acct = data[0]["securitiesAccount"] if isinstance(data, list) and data else {}
            bal = acct.get("currentBalances", {})
            return BrokerAccountInfo(
                balance=float(bal.get("cashBalance", 0)),
                buying_power=float(bal.get("buyingPower", 0)),
                equity=float(bal.get("liquidationValue", 0)),
            )

    async def get_positions(self) -> list[BrokerPosition]:
        session = await self._get_session()
        async with session.get(f"{API_BASE}/trader/v1/accounts?fields=positions", headers=self._headers()) as resp:
            data = await resp.json()
            acct = data[0]["securitiesAccount"] if isinstance(data, list) and data else {}
            return [
                BrokerPosition(
                    symbol=p.get("instrument", {}).get("symbol", ""),
                    quantity=float(p.get("longQuantity", 0)),
                    avg_entry=float(p.get("averagePrice", 0)),
                    current_price=0,
                    market_value=float(p.get("marketValue", 0)),
                    unrealized_pnl=float(p.get("currentDayProfitLoss", 0)),
                )
                for p in acct.get("positions", [])
            ]

    async def place_order(self, order: BrokerOrder) -> BrokerOrder:
        # Same API as TD Ameritrade
        session = await self._get_session()
        async with session.get(f"{API_BASE}/trader/v1/accounts", headers=self._headers()) as resp:
            accts = await resp.json()
        acct_id = self.config.get("tos_account_id", "")
        if not acct_id and accts:
            acct_id = accts[0]["securitiesAccount"]["accountId"]
        payload = {
            "orderType": order.order_type.value,
            "session": "NORMAL", "duration": "DAY", "orderStrategyType": "SINGLE",
            "orderLegCollection": [{"instruction": order.side.value, "quantity": order.quantity,
                                     "instrument": {"symbol": order.symbol, "assetType": "EQUITY"}}],
        }
        if order.limit_price:
            payload["price"] = str(order.limit_price)
        async with session.post(f"{API_BASE}/trader/v1/accounts/{acct_id}/orders",
                                headers=self._headers(), json=payload) as resp:
            if resp.status in (200, 201):
                order.broker_order_id = resp.headers.get("Location", "").split("/")[-1]
                order.status = "submitted"
            else:
                order.status = "rejected"
                order.error = await resp.text()
        return order

    async def cancel_order(self, broker_order_id: str) -> bool:
        return False

    async def get_quote(self, symbol: str) -> float:
        session = await self._get_session()
        async with session.get(f"{API_BASE}/marketdata/v1/quotes/{symbol}", headers=self._headers()) as resp:
            data = await resp.json()
            return float(data.get(symbol, {}).get("lastPrice", 0))
