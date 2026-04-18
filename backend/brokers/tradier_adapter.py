"""Tradier adapter — developer-friendly broker with REST API."""
import logging
from .base import BrokerAdapter, BrokerOrder, BrokerPosition, BrokerAccountInfo

logger = logging.getLogger("SentinelPulse")
API_BASE = "https://api.tradier.com/v1"


class TradierAdapter(BrokerAdapter):
    broker_id = "tradier"

    def _headers(self):
        return {"Authorization": f"Bearer {self.config.get('access_token', '')}", "Accept": "application/json"}

    def _acct(self):
        return self.config.get("account_id", "")

    async def check_connection(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(f"{API_BASE}/user/profile", headers=self._headers()) as resp:
                self.connected = resp.status == 200
                return self.connected
        except Exception as e:
            logger.error(f"Tradier connection error: {e}")
        return False

    async def get_account(self) -> BrokerAccountInfo:
        session = await self._get_session()
        async with session.get(f"{API_BASE}/accounts/{self._acct()}/balances", headers=self._headers()) as resp:
            data = await resp.json()
            bal = data.get("balances", {})
            return BrokerAccountInfo(
                balance=float(bal.get("total_cash", 0)),
                buying_power=float(bal.get("stock_buying_power", bal.get("buying_power", 0))),
                equity=float(bal.get("total_equity", 0)),
            )

    async def get_positions(self) -> list[BrokerPosition]:
        session = await self._get_session()
        async with session.get(f"{API_BASE}/accounts/{self._acct()}/positions", headers=self._headers()) as resp:
            data = await resp.json()
            positions = data.get("positions", {}).get("position", [])
            if isinstance(positions, dict):
                positions = [positions]
            return [
                BrokerPosition(
                    symbol=p.get("symbol", ""),
                    quantity=float(p.get("quantity", 0)),
                    avg_entry=float(p.get("cost_basis", 0)) / max(float(p.get("quantity", 1)), 1),
                    current_price=0,
                    market_value=float(p.get("cost_basis", 0)),
                    unrealized_pnl=0,
                )
                for p in positions
            ]

    async def place_order(self, order: BrokerOrder) -> BrokerOrder:
        session = await self._get_session()
        payload = {
            "class": "equity",
            "symbol": order.symbol,
            "side": order.side.value.lower(),
            "quantity": str(int(order.quantity)),
            "type": order.order_type.value.lower(),
            "duration": "day",
        }
        if order.limit_price:
            payload["price"] = str(order.limit_price)
        if order.stop_price:
            payload["stop"] = str(order.stop_price)
        async with session.post(f"{API_BASE}/accounts/{self._acct()}/orders",
                                headers=self._headers(), data=payload) as resp:
            data = await resp.json()
            if resp.status in (200, 201):
                oid = data.get("order", {}).get("id", "")
                order.broker_order_id = str(oid)
                order.status = "submitted"
            else:
                order.status = "rejected"
                order.error = str(data.get("error", data))
        return order

    async def cancel_order(self, broker_order_id: str) -> bool:
        session = await self._get_session()
        async with session.delete(f"{API_BASE}/accounts/{self._acct()}/orders/{broker_order_id}",
                                  headers=self._headers()) as resp:
            return resp.status == 200

    async def get_quote(self, symbol: str) -> float:
        session = await self._get_session()
        async with session.get(f"{API_BASE}/markets/quotes", headers=self._headers(),
                               params={"symbols": symbol}) as resp:
            data = await resp.json()
            q = data.get("quotes", {}).get("quote", {})
            return float(q.get("last", 0))
