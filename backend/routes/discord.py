"""
Discord bot and alert patterns endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models import Settings, DiscordAlertPatterns, DiscordAlertPatternsUpdate
import threading
import logging

_bot_start_lock = threading.Lock()  # FIXED M17: prevent double-start race

router = APIRouter(tags=["Discord"])
logger = logging.getLogger(__name__)

# Database reference
db = None

# Discord bot references (will be set by main server)
discord_bot = None
discord_bot_thread = None


def set_db(database):
    """Set the database reference"""
    global db
    db = database


def set_discord_bot(bot, thread):
    """Set discord bot references"""
    global discord_bot, discord_bot_thread
    discord_bot = bot
    discord_bot_thread = thread


def get_discord_bot():
    """Get discord bot for external access"""
    return discord_bot, discord_bot_thread


@router.post("/discord/start")
async def start_discord_bot(background_tasks: BackgroundTasks):
    """Start the Discord bot"""
    global discord_bot_thread
    
    settings = await db.get_settings()
    if not settings or not settings.get('discord_token'):
        raise HTTPException(status_code=400, detail="Discord token not configured")
    
    token = settings['discord_token']
    channel_ids = settings.get('discord_channel_ids', [])
    
    with _bot_start_lock:  # FIXED M17: atomic check-and-start
        if discord_bot_thread and discord_bot_thread.is_alive():
            return {"message": "Discord bot already running"}
        from server import run_discord_bot
        discord_bot_thread = threading.Thread(target=run_discord_bot, args=(token, channel_ids), daemon=True)
        discord_bot_thread.start()
    
    return {"message": "Discord bot starting..."}


@router.post("/discord/stop")
async def stop_discord_bot():
    """Stop the Discord bot"""
    from routes.health import update_bot_status
    
    if discord_bot:
        await discord_bot.close()
        update_bot_status('discord_connected', False)
        return {"message": "Discord bot stopped"}
    return {"message": "Discord bot not running"}


@router.post("/discord/test-connection")
async def test_discord_connection():
    """Test Discord bot connection"""
    from routes.health import bot_status
    
    settings = await db.get_settings()
    if not settings:
        return {"success": False, "status": "not_configured", "message": "Discord not configured", "details": None}
    
    if not settings.get('discord_token'):
        return {"success": False, "status": "no_token", "message": "No Discord bot token configured", "details": None}
    
    bot_running = discord_bot_thread and discord_bot_thread.is_alive()
    bot_connected = bot_status.get('discord_connected', False)
    
    if not bot_running:
        return {
            "success": False, 
            "status": "not_running", 
            "message": "Discord bot not running. Click 'Start Discord Bot'",
            "details": {"token_configured": True, "channel_ids": settings.get('discord_channel_ids', []) or ["All channels"]}
        }
    
    if not bot_connected:
        return {
            "success": False, 
            "status": "connecting", 
            "message": "Discord bot starting up...",
            "details": {"token_configured": True, "channel_ids": settings.get('discord_channel_ids', []) or ["All channels"]}
        }
    
    return {
        "success": True, 
        "status": "connected", 
        "message": "Discord bot connected and listening!",
        "details": {
            "bot_running": True, 
            "monitoring_channels": settings.get('discord_channel_ids', []) or ["All channels"],
            "auto_trading_enabled": bot_status.get('auto_trading_enabled', False),
            "alerts_processed": bot_status.get('alerts_processed', 0)
        }
    }


# Alert Patterns
@router.get("/discord/alert-patterns")
async def get_discord_alert_patterns():
    """Get custom Discord alert patterns"""
    patterns = await db.get_discord_patterns()
    if not patterns:
        default_patterns = DiscordAlertPatterns().model_dump()
        await db.update_discord_patterns(default_patterns)
        return default_patterns
    # Remove internal keys
    patterns.pop('id', None)
    return patterns


@router.put("/discord/alert-patterns")
async def update_discord_alert_patterns(update_data: DiscordAlertPatternsUpdate):
    """Update Discord alert patterns"""
    patterns = await db.get_discord_patterns()
    if not patterns:
        patterns = DiscordAlertPatterns().model_dump()
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    patterns.update(update_dict)
    
    await db.update_discord_patterns(patterns)
    
    # Remove internal keys for response
    patterns.pop('id', None)
    return patterns


@router.post("/discord/alert-patterns/reset")
async def reset_discord_alert_patterns():
    """Reset Discord alert patterns to defaults"""
    default_patterns = DiscordAlertPatterns().model_dump()
    await db.update_discord_patterns(default_patterns)
    return default_patterns


@router.post("/discord/alert-patterns/{pattern_type}/add")
async def add_alert_pattern(pattern_type: str, pattern: str):
    # FIXED M18: validate pattern
    if not pattern or not pattern.strip():
        raise HTTPException(status_code=400, detail="Pattern cannot be empty")
    if len(pattern) > 200:
        raise HTTPException(status_code=400, detail="Pattern too long (max 200 chars)")
    """Add a pattern to a specific pattern list"""
    valid_types = ['buy_patterns', 'sell_patterns', 'partial_sell_patterns', 
                   'average_down_patterns', 'stop_loss_patterns', 'take_profit_patterns', 'ignore_patterns']
    
    if pattern_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid pattern type. Valid: {valid_types}")
    
    patterns = await db.get_discord_patterns()
    if not patterns:
        patterns = DiscordAlertPatterns().model_dump()
    
    current_list = patterns.get(pattern_type, [])
    if pattern not in current_list:
        current_list.append(pattern)
        patterns[pattern_type] = current_list
        await db.update_discord_patterns(patterns)
    
    return {pattern_type: current_list}


@router.post("/discord/alert-patterns/{pattern_type}/remove")
async def remove_alert_pattern(pattern_type: str, pattern: str):
    """Remove a pattern from a specific pattern list"""
    valid_types = ['buy_patterns', 'sell_patterns', 'partial_sell_patterns', 
                   'average_down_patterns', 'stop_loss_patterns', 'take_profit_patterns', 'ignore_patterns']
    
    if pattern_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid pattern type. Valid: {valid_types}")
    
    patterns = await db.get_discord_patterns()
    if not patterns:
        return {pattern_type: []}
    
    current_list = patterns.get(pattern_type, [])
    if pattern in current_list:
        current_list.remove(pattern)
        patterns[pattern_type] = current_list
        await db.update_discord_patterns(patterns)
    
    return {pattern_type: current_list}
