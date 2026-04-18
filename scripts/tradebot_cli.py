"""
Complete CLI and Dashboard Helper
Commands and utilities for managing the trading bot
"""
import os
import sys
import logging
import asyncio
import click
from datetime import datetime, timezone
from typing import Optional, List, Dict
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Trading Bot CLI"""
    pass


@cli.command()
def status():
    """Show bot status"""
    click.echo("=== Trading Bot Status ===")
    click.echo(f"Time: {datetime.now(timezone.utc).isoformat()}")
    # Would load actual status in production
    click.echo("Status: Running")
    click.echo("Auto-trading: Enabled")


@cli.command()
@click.option('--ticker', required=True, help='Ticker symbol')
@click.option('--strike', required=True, type=float, help='Strike price')
@click.option('--option-type', default='CALL', type=click.Choice(['CALL', 'PUT']))
@click.option('--expiration', required=True, help='Expiration date')
@click.option('--quantity', default=1, type=int, help='Quantity')
def execute(ticker, strike, option_type, expiration, quantity):
    """Execute a trade"""
    click.echo(f"Executing: {quantity}x {ticker} ${strike} {option_type}")


@cli.command()
def positions():
    """List open positions"""
    click.echo("=== Open Positions ===")
    # Would load positions in production
    click.echo("No open positions")


@cli.command()
@click.option('--position-id', required=True, help='Position ID to close')
@click.option('--reason', default='manual', help='Close reason')
def close(position_id, reason):
    """Close a position"""
    click.echo(f"Closing position {position_id}: {reason}")


@cli.command()
def stats():
    """Show trading statistics"""
    click.echo("=== Trading Stats ===")
    click.echo("Total Trades: 0")
    click.echo("Win Rate: 0%")
    click.echo("P&L: $0.00")


@cli.command()
@click.option('--ticker', required=True, help='Check specific ticker')
def analyze(ticker):
    """Analyze a ticker"""
    click.echo(f"=== Analysis: {ticker} ===")
    # Would load analysis in production
    click.echo(f"Sector: Tech")
    click.echo("Current Positions: 0")


@cli.command()
def reset():
    """Reset daily counters"""
    click.echo("Resetting daily counters...")
    # Would reset in production
    click.echo("Done")


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to shutdown?')
def shutdown():
    """Shutdown the bot"""
    click.echo("Shutting down trading bot...")
    # Would send shutdown signal in production
    click.echo("Bot stopped")


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run CLI
    cli()


if __name__ == '__main__':
    main()


# ============= DASHBOARD ROUTES =============

def create_dashboard_routes():
    """Create dashboard routes for the API"""
    from fastapi import APIRouter, HTTPException
    import asyncio
    
    router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
    
    @router.get("/summary")
    async def get_summary():
        """Get dashboard summary"""
        return {
            "status": "running",
            "positions": {"open": 0, "total": 0},
            "performance": {
                "today_pnl": 0,
                "win_rate": 0,
                "trade_count": 0
            },
            "risk": {
                "consecutive_losses": 0,
                "can_trade": True
            }
        }
    
    @router.get("/positions")
    async def get_positions_detailed():
        """Get positions with detailed analytics"""
        return {"positions": [], "count": 0}
    
    @router.get("/performance")
    async def get_performance_detailed():
        """Get detailed performance metrics"""
        return {
            "total_trades": 0,
            "win_rate": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "expectancy": 0
        }
    
    @router.get("/risk")
    async def get_risk_detailed():
        """Get detailed risk metrics"""
        return {
            "portfolio": {
                "total_capital": 10000,
                "exposed": 0,
                "available": 10000
            },
            "correlation": {"by_ticker": {}, "by_sector": {}},
            "loss_tracking": {
                "consecutive": 0,
                "daily": 0,
                "can_trade": True
            }
        }
    
    @router.get("/heatmap")
    async def get_trade_heatmap():
        """Get trade heatmap by day/hour"""
        # Simplified - would be computed from trade history
        return {"heatmap": []}
    
    @router.get("/leaderboard")
    async def get_ticker_leaderboard():
        """Get tickers ranked by P&L"""
        return {"tickers": []}
    
    return router


# ============= UTILITY FUNCTIONS =============

def format_currency(amount: float) -> str:
    """Format currency for display"""
    sign = "+" if amount >= 0 else ""
    return f"{sign}${amount:.2f}"


def format_percent(value: float) -> str:
    """Format percentage for display"""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def format_position_summary(positions: List[dict]) -> str:
    """Format positions as readable string"""
    if not positions:
        return "No open positions"
    
    lines = []
    total_pnl = 0
    
    for pos in positions:
        pnl = pos.get('unrealized_pnl', 0)
        total_pnl += pnl
        pnl_str = format_currency(pnl)
        
        lines.append(
            f"{pos['ticker']} ${pos['strike']} {pos['option_type']} "
            f"x{pos['quantity']}: {pnl_str}"
        )
    
    # Add total
    lines.append(f"Total: {format_currency(total_pnl)}")
    
    return "\n".join(lines)


def validate_ticker(ticker: str) -> bool:
    """Validate ticker format"""
    if not ticker:
        return False
    return ticker.isalpha() and len(ticker) <= 5


def validate_expiration(expiration: str) -> bool:
    """Validate expiration format"""
    import re
    # MM/DD/YY or MM/DD/YYYY
    pattern = r'^\d{1,2}/\d{1,2}/\d{2,4}$'
    return bool(re.match(pattern, expiration))


def parse_quantity_from_message(message: str) -> int:
    """Parse quantity from alert message"""
    import re
    
    # Look for "x5" or "5x" or " contracts" etc
    patterns = [
        r'(\d+)x',
        r'x(\d+)',
        r'(\d+)\s*contracts?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return 1  # Default


# ============= TESTING HELPERS =============

def create_test_alert(
    ticker: str = "QQQ",
    strike: float = 653.0,
    option_type: str = "CALL",
    expiration: str = "04/17/2026",
    entry_price: float = 0.29
) -> dict:
    """Create test alert dictionary"""
    return {
        'ticker': ticker,
        'strike': strike,
        'option_type': option_type,
        'expiration': expiration,
        'entry_price': entry_price,
        'alert_type': 'buy',
        'quantity': 1
    }


def create_test_settings() -> dict:
    """Create test settings dictionary"""
    return {
        'auto_trading_enabled': True,
        'simulation_mode': True,
        'premium_buffer_enabled': True,
        'premium_buffer_amount': 3.0,
        'default_quantity': 1,
        'max_position_size': 1000.0,
        'take_profit_enabled': True,
        'take_profit_percentage': 50.0,
        'stop_loss_enabled': True,
        'stop_loss_percentage': 30.0,
        'trailing_stop_enabled': True,
        'trailing_stop_percent': 25.0,
        'max_consecutive_losses': 3,
        'max_daily_losses': 5,
        'max_daily_loss_amount': 500.0,
    }


# Run CLI if called directly
if __name__ == '__main__':
    main()