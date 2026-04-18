"""
eTrade Broker Adapter
Integrates with eTrade API for trading options

Reference: https://developer.etrade.com/getting-started
"""
import os
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ETradeAdapter:
    """eTrade broker adapter"""
    
    BASE_URL = "https://api.etrade.com"
    
    # For sandbox/testing
    SANDBOX_URL = "https://apisb.etrade.com"
    
    def __init__(
        self,
        consumer_key: str = "",
        consumer_secret: str = "",
        access_token: str = "",
        access_secret: str = "",
        account_id: str = "",
        use_sandbox: bool = True,
    ):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_secret = access_secret
        self.account_id = account_id
        self.use_sandbox = use_sandbox
        
        self.base_url = self.SANDBOX_URL if use_sandbox else self.BASE_URL
        self.session = requests.Session()
        
        # OAuth headers
        self._auth = {
            'oauth_consumer_key': consumer_key,
            'oauth_token': access_token,
        }
    
    def is_configured(self) -> bool:
        """Check if configured"""
        return bool(self.consumer_key and self.access_token)
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        data: Dict = None,
    ) -> Dict:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'OAuth oauth_consumer_key="{self.consumer_key}"',
        }
        
        try:
            if method == "GET":
                resp = self.session.get(url, params=params, headers=headers)
            elif method == "POST":
                resp = self.session.post(url, json=data, headers=headers)
            elif method == "PUT":
                resp = self.session.put(url, json=data, headers=headers)
            elif method == "DELETE":
                resp = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            resp.raise_for_status()
            return resp.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[eTrade] Request failed: {e}")
            return {'error': str(e)}
    
    # ============= ACCOUNT =============
    
    def get_account_balance(self) -> Optional[float]:
        """Get account cash balance"""
        endpoint = f"/v1/accounts/{self.account_id}/balance.json"
        result = self._make_request("GET", endpoint)
        
        if 'cashBalance' in result:
            return float(result['cashBalance'])
        return None
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        endpoint = f"/v1/accounts/{self.account_id}.json"
        return self._make_request("GET", endpoint)
    
    # ============= MARKET DATA =============
    
    def get_quote(self, symbol: str) -> Dict:
        """Get quote for symbol"""
        endpoint = "/v1/market/quote.json"
        params = {'symbol': symbol}
        result = self._make_request("GET", endpoint, params=params)
        
        if 'quoteResponse' in result:
            return result['quoteResponse'].get(symbol, {})
        return {}
    
    def get_option_chain(
        self,
        symbol: str,
        expiry: str = None,
    ) -> List[Dict]:
        """Get option chain for symbol"""
        endpoint = "/v1/market/optionchain.json"
        params = {
            'symbol': symbol,
            'expiry': expiry or '',
            'strikePrice': '',
        }
        
        result = self._make_request("GET", endpoint, params=params)
        
        if 'optionChain' in result:
            return result['optionChain'].get('option', [])
        return []
    
    # ============= ORDERS =============
    
    def place_order(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        quantity: int,
        price: float = 0.0,  # 0 for market
        order_type: str = "LIMIT",  # "LIMIT" or "MARKET"
        expiry: str = "GTC",
    ) -> Dict:
        """Place an order"""
        endpoint = f"/v1/accounts/{self.account_id}/orders.json"
        
        order_data = {
            'order': [
                {
                    'symbol': symbol,
                    'orderType': order_type,
                    'side': side,
                    'quantity': quantity,
                    'price': price,
                    'orderTerm': expiry,
                }
            ]
        }
        
        return self._make_request("POST", endpoint, data=order_data)
    
    def place_option_order(
        self,
        symbol: str,
        strike: float,
        option_type: str,  # "CALL" or "PUT"
        expiry: str,
        side: str,
        quantity: int,
        price: float = 0.0,
    ) -> Dict:
        """Place option order"""
        # Build option symbol
        expiry_formatted = datetime.strptime(expiry, "%m/%d/%Y").strftime("%y%m%d")
        opt_symbol = f"{symbol}{expiry_formatted}{strike}{option_type[0].upper()}"
        
        return self.place_order(opt_symbol, side, quantity, price)
    
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order"""
        endpoint = f"/v1/accounts/{self.account_id}/orders/{order_id}.json"
        return self._make_request("DELETE", endpoint)
    
    def get_orders(self, status: str = "OPEN") -> List[Dict]:
        """Get orders"""
        endpoint = f"/v1/accounts/{self.account_id}/orders.json"
        params = {'status': status}
        
        result = self._make_request("GET", endpoint, params=params)
        
        if 'orderList' in result:
            return result['orderList']
        return []
    
    def get_order(self, order_id: str) -> Dict:
        """Get specific order"""
        endpoint = f"/v1/accounts/{self.account_id}/orders/{order_id}.json"
        return self._make_request("GET", endpoint)
    
    # ============= POSITIONS =============
    
    def get_positions(self) -> List[Dict]:
        """Get open positions"""
        endpoint = f"/v1/accounts/{self.account_id}/positions.json"
        result = self._make_request("GET", endpoint)
        
        if 'positionData' in result:
            return result['positionData']
        return []
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for symbol"""
        positions = self.get_positions()
        
        for pos in positions:
            if pos.get('symbol') == symbol:
                return pos
        return None
    
    # ============= REAL-TIME QUOTES =============
    
    def get_realtime_quote(self, symbol: str) -> Dict:
        """Get real-time quote (requires premium subscription)"""
        endpoint = "/v1/market/quote/realtime.json"
        params = {
            'symbols': symbol,
            'fields': 'ask,bid,last,volume',
        }
        
        result = self._make_request("GET", endpoint, params=params)
        
        if 'quoteResponse' in result:
            return result['quoteResponse'].get(symbol, {})
        return {}


class ETradeConfig:
    """eTrade configuration helper"""
    
    @staticmethod
    def create_from_env() -> ETradeAdapter:
        """Create adapter from environment"""
        return ETradeAdapter(
            consumer_key=os.environ.get('ETRADE_CONSUMER_KEY', ''),
            consumer_secret=os.environ.get('ETRADE_CONSUMER_SECRET', ''),
            access_token=os.environ.get('ETRADE_ACCESS_TOKEN', ''),
            access_secret=os.environ.get('ETRADE_ACCESS_SECRET', ''),
            account_id=os.environ.get('ETRADE_ACCOUNT_ID', ''),
            use_sandbox=os.environ.get('ETRADE_USE_SANDBOX', 'true').lower() == 'true',
        )
    
    @staticmethod
    def get_order_estimate(
        symbol: str,
        side: str,
        quantity: int,
        price: float,
    ) -> Dict:
        """Get order cost estimate"""
        # eTrade requires preview first
        return {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'estimatedCost': price * quantity * 100,
            'commissions': 0.0,
        }


# Export
__all__ = ['ETradeAdapter', 'ETradeConfig']