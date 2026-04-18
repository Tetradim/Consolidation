"""Interactive Brokers adapter — via TWS/Gateway REST API."""
import logging
from .base import BrokerAdapter, BrokerOrder, BrokerPosition, BrokerAccountInfo
import aiohttp

logger = logging.getLogger("SentinelPulse")


class IBKRAdapter(BrokerAdapter):
    broker_id = "ibkr"

    def _gw(self):
        return self.config.get("gateway_url", "https://localhost:5000")

    def _acct(self):
        return self.config.get("account_id", "")

    async def check_connection(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._gw()}/v1/api/iserver/auth/status",
                ssl=False, timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.connected = data.get("authenticated", False)
                    return self.connected
        except Exception as e:
            logger.error(f"IBKR connection error: {e}")
        return False

    async def get_account(self) -> BrokerAccountInfo:
        session = await self._get_session()
        async with session.get(
            f"{self._gw()}/v1/api/portfolio/{self._acct()}/summary", ssl=False,
        ) as resp:
            data = await resp.json()
            return BrokerAccountInfo(
                balance=float(data.get("totalcashvalue", {}).get("amount", 0)),
                buying_power=float(data.get("buyingpower", {}).get("amount", 0)),
                equity=float(data.get("netliquidation", {}).get("amount", 0)),
            )

    async def get_positions(self) -> list[BrokerPosition]:
        session = await self._get_session()
        async with session.get(
            f"{self._gw()}/v1/api/portfolio/{self._acct()}/positions/0", ssl=False,
        ) as resp:
            data = await resp.json()
            return [
                BrokerPosition(
                    symbol=p.get("ticker", p.get("contractDesc", "")),
                    quantity=float(p.get("position", 0)),
                    avg_entry=float(p.get("avgCost", 0)),
                    current_price=float(p.get("mktPrice", 0)),
                    market_value=float(p.get("mktValue", 0)),
                    unrealized_pnl=float(p.get("unrealizedPnl", 0)),
                )
                for p in (data if isinstance(data, list) else [])
            ]

    async def place_order(self, order: BrokerOrder) -> BrokerOrder:
        session = await self._get_session()
        # Look up conid for the symbol
        async with session.post(
            f"{self._gw()}/v1/api/iserver/secdef/search",
            json={"symbol": order.symbol, "secType": "STK", "name": True}, ssl=False,
        ) as resp:
            results = await resp.json()
            if not results:
                order.status = "rejected"
                order.error = f"No contract found for {order.symbol}"
                return order
            conid = results[0].get("conid")

        ot_map = {"MARKET": "MKT", "LIMIT": "LMT", "STOP": "STP", "STOP_LIMIT": "STP_LMT"}
        payload = {"orders": [{"conid": conid, "orderType": ot_map.get(order.order_type.value, "LMT"),
                               "side": order.side.value, "quantity": order.quantity, "tif": "DAY"}]}
        if order.limit_price:
            payload["orders"][0]["price"] = order.limit_price
        if order.stop_price:
            payload["orders"][0]["auxPrice"] = order.stop_price

        async with session.post(
            f"{self._gw()}/v1/api/iserver/account/{self._acct()}/orders",
            json=payload, ssl=False,
        ) as resp:
            data = await resp.json()
            if resp.status == 200 and isinstance(data, list) and data:
                order.broker_order_id = str(data[0].get("order_id", ""))
                order.status = "submitted"
            else:
                order.status = "rejected"
                order.error = str(data)
        return order

    async def cancel_order(self, broker_order_id: str) -> bool:
        session = await self._get_session()
        async with session.delete(
            f"{self._gw()}/v1/api/iserver/account/{self._acct()}/order/{broker_order_id}", ssl=False,
        ) as resp:
            return resp.status == 200

    async def get_quote(self, symbol: str) -> float:
        session = await self._get_session()
        async with session.get(
            f"{self._gw()}/v1/api/iserver/marketdata/snapshot",
            params={"conids": symbol, "fields": "31"}, ssl=False,
        ) as resp:
            data = await resp.json()
            if data and isinstance(data, list):
                return float(data[0].get("31", 0))
        return 0.0
