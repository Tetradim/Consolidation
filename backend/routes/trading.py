"""
Trading endpoints - alerts, trades, positions, portfolio
"""
from fastapi import APIRouter, HTTPException
from models import Settings, Trade, Position
from typing import Optional
from datetime import datetime, timezone

router = APIRouter(tags=["Trading"])

# Database reference
db = None


def set_db(database):
    """Set the database reference"""
    global db
    db = database


# Helper function
def calculate_pnl(entry_price: float, exit_price: float, quantity: int) -> float:
    """Calculate realized P&L for a trade"""
    return (exit_price - entry_price) * quantity * 100


# Alerts
@router.get("/alerts")
async def get_alerts(limit: int = 50):
    """Get recent alerts"""
    return await db.get_alerts(limit)


# Trades
@router.get("/trades")
async def get_trades(limit: int = 50):
    """Get recent trades"""
    return await db.get_trades(limit)


# Positions
@router.get("/positions")
async def get_positions(status: Optional[str] = None):
    """Get positions, optionally filtered by status"""
    return await db.get_positions(status)


@router.post("/sell-position/{position_id}")
async def sell_position(position_id: str, percentage: float = 100):
    """Sell a position (full or partial)"""
    from routes.settings import check_and_trigger_shutdown
    
    position_doc = await db.get_position_by_id(position_id)
    if not position_doc:
        raise HTTPException(status_code=404, detail="Position not found")
    
    position = Position(**position_doc)
    sell_qty = max(1, int(position.remaining_quantity * (percentage / 100)))
    
    settings = await db.get_settings()
    active_broker = settings.get('active_broker', 'ibkr')
    simulation_mode = settings.get('simulation_mode', True)
    
    # FIXED C19: refuse to sell at entry price when current_price unknown
    if position.current_price is None:
        raise HTTPException(
            status_code=400,
            detail="Cannot sell: current_price is not set. Update the position price first."
        )
    trade = Trade(
        ticker=position.ticker,
        strike=position.strike,
        option_type=position.option_type,
        expiration=position.expiration,
        entry_price=position.entry_price,
        exit_price=position.current_price,
        quantity=sell_qty,
        side="SELL",
        broker=active_broker,
        simulated=simulation_mode
    )
    
    if simulation_mode:
        trade.status = "simulated"
        trade.executed_at = datetime.now(timezone.utc)
    
    realized_pnl = calculate_pnl(position.entry_price, trade.exit_price or position.entry_price, sell_qty)
    trade.realized_pnl = realized_pnl
    
    await db.insert_trade(trade.model_dump())
    
    new_remaining = position.remaining_quantity - sell_qty
    update_data = {
        '$set': {
            'remaining_quantity': new_remaining,
            'realized_pnl': position.realized_pnl + realized_pnl,
            'status': 'closed' if new_remaining <= 0 else 'partial'
        },
        '$push': {'trade_ids': trade.id}
    }
    if new_remaining <= 0:
        update_data['$set']['closed_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.update_position(position_id, update_data)
    
    # Check for auto shutdown if this was a losing trade
    shutdown_reason = await check_and_trigger_shutdown(realized_pnl)
    
    result = {"message": f"Sold {sell_qty} contracts", "realized_pnl": realized_pnl}
    if shutdown_reason:
        result["shutdown_triggered"] = True
        result["shutdown_reason"] = shutdown_reason
    
    return result


# Portfolio
@router.get("/portfolio")
async def get_portfolio():
    """Get portfolio summary"""
    return await db.get_portfolio_summary()
