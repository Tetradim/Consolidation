import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def parse_alert(message: str) -> Optional[dict]:
    """Parse Discord alert - supports buy, sell, and average down alerts"""
    try:
        message_upper = message.upper()
        
        avg_down_keywords = ['AVERAGE DOWN', 'AVG DOWN', 'AVERAGING', 'ADD TO']
        is_avg_down_alert = any(keyword in message_upper for keyword in avg_down_keywords)
        
        if is_avg_down_alert:
            return parse_average_down_alert(message)
        
        sell_keywords = ['SELL', 'TRIM', 'CLOSE', 'EXIT']
        is_sell_alert = any(keyword in message_upper for keyword in sell_keywords)
        
        if is_sell_alert:
            return parse_sell_alert(message)
        else:
            return parse_buy_alert(message)
        
    except Exception as e:
        logger.error(f"Error parsing alert: {e}")
        return None


def parse_average_down_alert(message: str) -> Optional[dict]:
    """Parse average down alert formats"""
    try:
        message_upper = message.upper()
        result = {
            'alert_type': 'average_down',
            'ticker': None, 'strike': None, 'option_type': None,
            'expiration': None, 'entry_price': None, 'sell_percentage': None
        }
        
        ticker_match = re.search(r'\$([A-Z]{1,5})\b', message_upper)
        if ticker_match:
            result['ticker'] = ticker_match.group(1)
        
        strike_patterns = [
            r'\$?(\d+(?:\.\d+)?)\s*(CALLS?|PUTS?)',
            r'\$?(\d+(?:\.\d+)?)(C|P)\b',
        ]
        
        for pattern in strike_patterns:
            match = re.search(pattern, message_upper)
            if match:
                result['strike'] = float(match.group(1))
                opt_type = match.group(2).upper()
                result['option_type'] = 'CALL' if opt_type.startswith('C') else 'PUT'
                break
        
        exp_match = re.search(r'(\d{1,2}/\d{1,2}/?\d{0,4})', message_upper)
        if exp_match:
            result['expiration'] = exp_match.group(1)
        
        entry_patterns = [r'\$?([\d.]+)\s*ENTRY', r'@\s*\$?([\d.]+)', r'AT\s*\$?([\d.]+)']
        for pattern in entry_patterns:
            match = re.search(pattern, message_upper)
            if match:
                result['entry_price'] = float(match.group(1))
                break
        
        if result['ticker']:
            return result
        return None
        
    except Exception as e:
        logger.error(f"Error parsing average down alert: {e}")
        return None


def parse_sell_alert(message: str) -> Optional[dict]:
    """Parse sell/trim/close alert"""
    try:
        message_upper = message.upper()
        result = {
            'alert_type': 'sell',
            'ticker': None, 'strike': None, 'option_type': None,
            'expiration': None, 'entry_price': None, 'sell_percentage': 100.0
        }
        
        if 'TRIM' in message_upper:
            result['alert_type'] = 'trim'
        elif 'CLOSE' in message_upper:
            result['alert_type'] = 'close'
        
        ticker_match = re.search(r'\$([A-Z]{1,5})\b', message_upper)
        if ticker_match:
            result['ticker'] = ticker_match.group(1)
        
        pct_patterns = [
            r'(\d+)\s*%', r'SELL\s+(\d+)', r'TRIM\s+(\d+)'
        ]
        
        for pattern in pct_patterns:
            match = re.search(pattern, message_upper)
            if match:
                pct = float(match.group(1))
                if pct <= 100:
                    result['sell_percentage'] = pct
                break
        
        if 'ALL' in message_upper or result['alert_type'] == 'close':
            result['sell_percentage'] = 100.0
        
        strike_patterns = [
            r'\$?(\d+(?:\.\d+)?)\s*(CALLS?|PUTS?)',
            r'\$?(\d+(?:\.\d+)?)(C|P)\b',
        ]
        
        for pattern in strike_patterns:
            match = re.search(pattern, message_upper)
            if match:
                result['strike'] = float(match.group(1))
                opt_type = match.group(2).upper()
                result['option_type'] = 'CALL' if opt_type.startswith('C') else 'PUT'
                break
        
        exp_match = re.search(r'(\d{1,2}/\d{1,2}/?\d{0,4})', message_upper)
        if exp_match:
            result['expiration'] = exp_match.group(1)
        
        if result['ticker']:
            return result
        return None
        
    except Exception as e:
        logger.error(f"Error parsing sell alert: {e}")
        return None


def parse_buy_alert(message: str) -> Optional[dict]:
    """Parse buy alert format"""
    try:
        result = {
            'alert_type': 'buy',
            'ticker': None, 'strike': None, 'option_type': None,
            'expiration': None, 'entry_price': None, 'sell_percentage': None
        }
        
        ticker_match = re.search(r'\$([A-Z]{1,5})\b', message.upper())
        if ticker_match:
            result['ticker'] = ticker_match.group(1)
        
        strike_patterns = [
            r'\$?(\d+(?:\.\d+)?)\s*(CALLS?|PUTS?)',
            r'\$?(\d+(?:\.\d+)?)\s+(C|P)\b',
        ]
        
        for pattern in strike_patterns:
            match = re.search(pattern, message.upper())
            if match:
                result['strike'] = float(match.group(1))
                opt_type = match.group(2).upper()
                result['option_type'] = 'CALL' if opt_type.startswith('C') else 'PUT'
                break
        
        exp_patterns = [
            r'EXP(?:IRATION)?\s*:?\s*(\d{1,2}/\d{1,2}/?\d{0,4})',
            r'(\d{1,2}/\d{1,2}/\d{2,4})',
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, message.upper())
            if match:
                result['expiration'] = match.group(1)
                break
        
        price_patterns = [
            r'\$?([\d.]+)\s*ENTRY',
            r'ENTRY\s*:?\s*\$?([\d.]+)',
            r'@\s*\$?([\d.]+)',
            r'\$\.([\d]+)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, message.upper())
            if match:
                price_str = match.group(1)
                if '.' not in price_str and len(price_str) <= 2:
                    result['entry_price'] = float(f"0.{price_str}")
                else:
                    result['entry_price'] = float(price_str)
                break
        
        if result['ticker'] and result['strike'] and result['option_type']:
            return result
        return None
        
    except Exception as e:
        logger.error(f"Error parsing buy alert: {e}")
        return None


def calculate_pnl(entry_price: float, current_price: float, quantity: int) -> float:
    """Calculate P&L for options (multiply by 100)"""
    return (current_price - entry_price) * quantity * 100
