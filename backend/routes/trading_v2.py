"""
Trading Routes - Execute trades, manage positions
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging
import uuid
import asyncio

from models import Settings
from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trading", tags=["trading"])

# Global state
_positions: dict = {}
_order_counter = 0


# ============= REQUEST MODELS =============

class ExecuteTradeRequest(BaseModel):
    """Request to execute a trade"""
    ticker: str
    strike: float
    option_type: str = "CALL"
    expiration: str
    quantity: int = 1
    side: str = "BUY"
    entry_price: float
    use_buffer: bool = True
    buffer_percentage: float = 3.0
    
    # Bracket order settings
    profit_target: Optional[float] = None
    stop_loss: Optional[float] = None
    use_trailing_stop: bool = False
    trailing_percentage: float = 25.0
    
    # Execution
    simulation: bool = True


class ClosePositionRequest(BaseModel):
    """Request to close a position"""
    position_id: str
    reason: str = "manual"


class UpdatePositionRequest(BaseModel):
    """Update position bracket settings"""
    profit_target: Optional[float] = None
    stop_loss: Optional[float] = None
    use_trailing_stop: Optional[bool] = None
    trailing_percentage: Optional[float] = None


# ============= HELPER FUNCTIONS =============

def calculate_buffered_price(entry_price: float, buffer_percentage: float = 3.0) -> float:
    """Calculate limit price with buffer"""
    if entry_price <= 0:
        return 0.01
    buffered = entry_price * (1 - buffer_percentage / 100)
    return round(max(buffered, 0.01), 2)


def calculate_bracket_prices(entry_price: float, profit_target_pct: float = 50.0, 
                        stop_loss_pct: float = 30.0) -> tuple:
    """Calculate profit target and stop loss prices"""
    profit_target = round(entry_price * (1 + profit_target_pct / 100), 2)
    stop_loss = round(entry_price * (1 - stop_loss_pct / 100), 2)
    return profit_target, stop_loss


def generate_order_id() -> str:
    """Generate unique order ID"""
    global _order_counter
    _order_counter += 1
    return f"ord_{datetime.utcnow().timestamp()}_{_order_counter}"


def generate_position_id() -> str:
    """Generate unique position ID"""
    return f"pos_{uuid.uuid4().hex[:12]}"


# ============= ROUTES =============

@router.get("/positions")
async def get_positions(status: Optional[str] = None):
    """Get all positions"""
    db = await get_db()
    
    if status:
        positions = await db.get_positions(status=status)
    else:
        positions = await db.get_positions()
    
    return {
        "positions": positions,
        "count": len(positions),
        "open_count": len([p for p in positions if p.get("status") == "open"])
    }


@router.get("/positions/{position_id}")
async def get_position(position_id: str):
    """Get position by ID"""
    db = await get_db()
    position = await db.get_position(position_id)
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return position


@router.post("/execute")
async def execute_trade(request: ExecuteTradeRequest):
    """Execute a trade from an alert"""
    global _positions
    
    # Get settings
    db = await get_db()
    settings = await db.get_settings()
    
    # Apply settings defaults
    simulation = request.simulation or settings.get("simulation_mode", True)
    buffer_pct = request.buffer_percentage
    if request.use_buffer and settings.get("premium_buffer_enabled"):
        buffer_pct = settings.get("premium_buffer_amount", 3)
    
    # Calculate buffered price
    limit_price = calculate_buffered_price(request.entry_price, buffer_pct)
    buffer_saved = round(request.entry_price - limit_price, 2)
    
    # Generate IDs
    order_id = generate_order_id()
    position_id = generate_position_id()
    alert_id = f"alert_{datetime.utcnow().timestamp()}"
    
    # Calculate bracket prices if enabled
    profit_target = request.profit_target
    stop_loss = request.stop_loss
    
    if settings.get("bracket_order_enabled") and request.side.upper() == "BUY":
        profit_pct = settings.get("take_profit_percentage", 50)
        stop_pct = settings.get("stop_loss_percentage", 30)
        profit_target, stop_loss = calculate_bracket_prices(
            request.entry_price, profit_pct, stop_pct
        )
    
    # Create order
    order = {
        "id": order_id,
        "alert_id": alert_id,
        "ticker": request.ticker.upper(),
        "strike": request.strike,
        "option_type": request.option_type.upper(),
        "expiration": request.expiration,
        "side": request.side.upper(),
        "quantity": request.quantity,
        "order_type": "LIMIT",
        "limit_price": limit_price,
        "alert_price": request.entry_price,
        "buffer_applied": buffer_pct,
        "buffer_saved": buffer_saved,
        "status": "filled" if simulation else "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # Save order
    await db.save_order(order)
    
    # Create position (for simulation, mark as filled immediately)
    position = {
        "id": position_id,
        "order_id": order_id,
        "alert_id": alert_id,
        "ticker": request.ticker.upper(),
        "strike": request.strike,
        "option_type": request.option_type.upper(),
        "expiration": request.expiration,
        "quantity": request.quantity,
        "entry_price": request.entry_price,
        "limit_price": limit_price,
        "buffer_saved": buffer_saved,
        "entry_buffer": buffer_pct,
        "profit_target": profit_target,
        "stop_loss": stop_loss,
        "trailing_stop_enabled": request.use_trailing_stop,
        "trailing_percentage": request.trailing_percentage,
        "status": "open",
        "opened_at": datetime.utcnow().isoformat(),
        "peak_price": request.entry_price,
        "current_price": request.entry_price,
    }
    
    if simulation:
        position["filled_at"] = datetime.utcnow().isoformat()
        position["realized_pnl"] = 0.0
    
    await db.save_position(position)
    _positions[position_id] = position
    
    logger.info(f"[Trading] Executed trade: {request.ticker} ${request.strike} {request.option_type} "
               f"Qty:{request.quantity} @ ${limit_price} (buffer: ${buffer_saved})")
    
    return {
        "success": True,
        "message": f"Trade {'simulated' if simulation else 'submitted'}: "
                   f"{request.ticker} ${request.strike} {request.option_type}",
        "order_id": order_id,
        "position_id": position_id,
        "limit_price": limit_price,
        "buffer_saved": buffer_saved,
        "simulation": simulation,
    }


@router.post("/close")
async def close_position(request: ClosePositionRequest):
    """Close a position"""
    db = await get_db()
    
    position = await db.get_position(request.position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    # Calculate P&L
    current_price = position.get("current_price", position.get("entry_price"))
    entry_price = position.get("entry_price")
    quantity = position.get("quantity", 1)
    realized_pnl = (current_price - entry_price) * quantity * 100
    
    # Update position
    position["status"] = "closed"
    position["close_reason"] = request.reason
    position["closed_at"] = datetime.utcnow().isoformat()
    position["realized_pnl"] = realized_pnl
    position["exit_price"] = current_price
    
    await db.update_position(request.position_id, position)
    
    # Remove from memory
    if request.position_id in _positions:
        del _positions[request.position_id]
    
    logger.info(f"[Trading] Closed position {request.position_id}: {request.reason}, "
               f"P&L: ${realized_pnl:.2f}")
    
    return {
        "success": True,
        "message": f"Position closed: {request.reason}",
        "realized_pnl": realized_pnl,
    }


@router.put("/positions/{position_id}")
async def update_position(position_id: str, request: UpdatePositionRequest):
    """Update position bracket settings"""
    db = await get_db()
    
    position = await db.get_position(position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    # Update fields
    if request.profit_target is not None:
        position["profit_target"] = request.profit_target
    if request.stop_loss is not None:
        position["stop_loss"] = request.stop_loss
    if request.use_trailing_stop is not None:
        position["trailing_stop_enabled"] = request.use_trailing_stop
    if request.trailing_percentage is not None:
        position["trailing_percentage"] = request.trailing_percentage
    
    position["updated_at"] = datetime.utcnow().isoformat()
    
    await db.update_position(position_id, position)
    
    return {
        "success": True,
        "message": "Position updated",
        "position": position,
    }


@router.get("/orders")
async def get_orders(status: Optional[str] = None):
    """Get all orders"""
    db = await get_db()
    orders = await db.get_orders(status)
    
    return {
        "orders": orders,
        "count": len(orders)
    }


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order by ID"""
    db = await get_db()
    order = await db.get_order(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order


@router.get("/stats")
async def get_stats():
    """Get trading statistics"""
    db = await get_db()
    
    positions = await db.get_positions()
    orders = await db.get_orders()
    
    open_positions = [p for p in positions if p.get("status") == "open"]
    closed_positions = [p for p in positions if p.get("status") == "closed"]
    
    # Calculate P&L
    realized_pnl = sum(p.get("realized_pnl", 0) for p in closed_positions)
    unrealized_pnl = 0
    for p in open_positions:
        current = p.get("current_price", p.get("entry_price"))
        unrealized_pnl += (current - p.get("entry_price", 0)) * p.get("quantity", 1) * 100
    
    return {
        "total_positions": len(positions),
        "open_positions": len(open_positions),
        "closed_positions": len(closed_positions),
        "total_orders": len(orders),
        "realized_pnl": round(realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "total_pnl": round(realized_pnl + unrealized_pnl, 2),
    }


@router.post("/cancel/{order_id}")
async def cancel_order(order_id: str):
    """Cancel a pending order"""
    db = await get_db()
    
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")
    
    order["status"] = "cancelled"
    order["cancelled_at"] = datetime.utcnow().isoformat()
    
    await db.update_order(order_id, order)
    
    return {
        "success": True,
        "message": "Order cancelled"
    }


# Export router
trading_router = router