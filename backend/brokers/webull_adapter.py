"""Webull adapter — unofficial API, high risk of breakage."""
import logging
from .base import BrokerAdapter, BrokerOrder, BrokerPosition, BrokerAccountInfo

logger = logging.getLogger("SentinelPulse")


class WebullAdapter(BrokerAdapter):
    broker_id = "webull"

    async def check_connection(self) -> bool:
        """Webull has no official public API. Connection requires the webull package."""
        try:
            from webull import webull as wb
            w = wb()
            w.login(self.config.get("username", ""), self.config.get("password", ""),
                    device_id=self.config.get("device_id", ""))
            if self.config.get("trade_token"):
                w.get_trade_token(self.config["trade_token"])
            account = w.get_account()
            self.connected = bool(account)
            self._wb = w
            return self.connected
        except ImportError:
            logger.error("webull package not installed: pip install webull")
            return False
        except Exception as e:
            logger.error(f"Webull connection error: {e}")
            return False

    async def get_account(self) -> BrokerAccountInfo:
        acct = self._wb.get_account() if hasattr(self, "_wb") else {}
        return BrokerAccountInfo(
            balance=float(acct.get("cashBalance", 0)),
            buying_power=float(acct.get("dayBuyingPower", 0)),
            equity=float(acct.get("netLiquidation", 0)),
        )

    async def get_positions(self) -> list[BrokerPosition]:
        positions = self._wb.get_positions() if hasattr(self, "_wb") else []
        return [
            BrokerPosition(
                symbol=p.get("ticker", {}).get("symbol", ""),
                quantity=float(p.get("position", 0)),
                avg_entry=float(p.get("costPrice", 0)),
                current_price=float(p.get("lastPrice", 0)),
                market_value=float(p.get("marketValue", 0)),
                unrealized_pnl=float(p.get("unrealizedProfitLoss", 0)),
            )
            for p in positions
        ]

    async def place_order(self, order: BrokerOrder) -> BrokerOrder:
        if not hasattr(self, "_wb"):
            order.status = "rejected"
            order.error = "Not connected to Webull"
            return order
        try:
            if order.order_type.value == "MARKET":
                result = self._wb.place_order(stock=order.symbol, action=order.side.value,
                                               orderType="MKT", quant=int(order.quantity))
            else:
                result = self._wb.place_order(stock=order.symbol, action=order.side.value,
                                               orderType="LMT", quant=int(order.quantity),
                                               price=order.limit_price)
            if result and "orderId" in str(result):
                order.broker_order_id = str(result.get("orderId", result.get("data", {}).get("orderId", "")))
                order.status = "submitted"
            else:
                order.status = "rejected"
                order.error = str(result)
        except Exception as e:
            order.status = "rejected"
            order.error = str(e)
        return order

    async def cancel_order(self, broker_order_id: str) -> bool:
        try:
            self._wb.cancel_order(broker_order_id)
            return True
        except Exception:
            return False

    async def get_quote(self, symbol: str) -> float:
        try:
            q = self._wb.get_quote(stock=symbol)
            return float(q.get("close", 0))
        except Exception:
            return 0.0
