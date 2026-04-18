"""
Profile management and per-broker settings endpoints
"""
from fastapi import APIRouter, HTTPException
import asyncio
_profile_lock = asyncio.Lock()  # FIXED C18: atomic profile activation
from models import (
    Profile, ProfileCreate, ProfileUpdate,
    BrokerSettings, BrokerSettingsUpdate
)
# M5: ProfileSettings and ProfileSettingsUpdate no longer imported --
#     the legacy /settings endpoints now return 410 Gone.

router = APIRouter(tags=["Profiles"])

# Database reference
db = None


def set_db(database):
    """Set the database reference"""
    global db
    db = database


# Profile CRUD
@router.get("/profiles")
async def get_profiles():
    """Get all profiles"""
    profiles = await db.get_profiles()
    if not profiles:
        default_profile = Profile(
            name="Default Profile",
            description="Default trading profile",
            active_brokers=[],
            is_active=True
        ).model_dump()
        await db.insert_profile(default_profile)
        profiles = [default_profile]
    return profiles


@router.get("/profiles/active")
async def get_active_profile():
    """Get the currently active profile"""
    profiles = await db.get_profiles()
    active = next((p for p in profiles if p.get('is_active')), None)
    if not active:
        default_profile = Profile(
            name="Default Profile",
            description="Default trading profile",
            active_brokers=[],
            is_active=True
        ).model_dump()
        await db.insert_profile(default_profile)
        return default_profile
    return active


@router.post("/profiles")
async def create_profile(profile_data: ProfileCreate):
    """Create a new profile"""
    profile = Profile(
        name=profile_data.name,
        description=profile_data.description,
        active_brokers=[],
        is_active=False
    ).model_dump()
    await db.insert_profile(profile)
    return profile


@router.put("/profiles/{profile_id}")
async def update_profile(profile_id: str, update_data: ProfileUpdate):
    """Update a profile — FIXED M22: existence check before write"""
    profile = await db.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if update_dict:
        await db.update_profile(profile_id, update_dict)
    return await db.get_profile_by_id(profile_id)


@router.post("/profiles/{profile_id}/activate")
async def activate_profile(profile_id: str):
    """Set a profile as the active profile — FIXED C18: atomic"""
    async with _profile_lock:
        profile = await db.get_profile_by_id(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        await db.set_all_profiles_inactive()
        await db.update_profile(profile_id, {"is_active": True})
        return await db.get_profile_by_id(profile_id)


@router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    """Delete a profile"""
    count = await db.count_profiles()
    if count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last profile")
    
    profile = await db.get_profile_by_id(profile_id)
    if profile and profile.get('is_active'):
        raise HTTPException(status_code=400, detail="Cannot delete the active profile. Activate another profile first.")
    
    deleted = await db.delete_profile(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"deleted": True}


# Profile Broker Management
@router.post("/profiles/{profile_id}/brokers/{broker_type}/toggle")
async def toggle_profile_broker(profile_id: str, broker_type: str):
    """Toggle a broker's active status within a profile"""
    # FIXED M23: validate broker_type
    from models import BrokerType
    try:
        BrokerType(broker_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid broker type: {broker_type}")
    profile = await db.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    active_brokers = profile.get('active_brokers', [])
    if broker_type in active_brokers:
        active_brokers.remove(broker_type)
    else:
        active_brokers.append(broker_type)
    
    await db.update_profile(profile_id, {'active_brokers': active_brokers})
    
    return {'active_brokers': active_brokers, 'broker_type': broker_type, 'is_active': broker_type in active_brokers}


@router.get("/profiles/{profile_id}/active-brokers")
async def get_profile_active_brokers(profile_id: str):
    """Get list of active brokers for a profile"""
    profile = await db.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {'active_brokers': profile.get('active_brokers', [])}


# Profile Settings (Legacy -- M5: replaced by per-broker settings endpoints below)
# These three endpoints are kept as 410 Gone stubs so existing clients get a
# clear error message rather than a 404, and can be removed in a future release.

@router.get("/profiles/{profile_id}/settings")
async def get_profile_settings_deprecated(profile_id: str):
    """Deprecated -- use GET /profiles/{id}/brokers/{broker_id}/settings instead."""
    raise HTTPException(
        status_code=410,
        detail=(
            "This endpoint is removed. "
            "Use GET /api/profiles/{id}/all-broker-settings or "
            "GET /api/profiles/{id}/brokers/{broker_id}/settings instead."
        )
    )


@router.put("/profiles/{profile_id}/settings")
async def update_profile_settings_deprecated(profile_id: str):
    """Deprecated -- use PUT /profiles/{id}/brokers/{broker_id}/settings instead."""
    raise HTTPException(
        status_code=410,
        detail=(
            "This endpoint is removed. "
            "Use PUT /api/profiles/{id}/brokers/{broker_id}/settings instead."
        )
    )


@router.post("/profiles/{profile_id}/settings/toggle/{setting_name}")
async def toggle_profile_setting_deprecated(profile_id: str, setting_name: str):
    """Deprecated -- use POST /profiles/{id}/brokers/{broker_id}/settings/toggle/{setting}."""
    raise HTTPException(
        status_code=410,
        detail=(
            "This endpoint is removed. "
            "Use POST /api/profiles/{id}/brokers/{broker_id}/settings/toggle/{setting} instead."
        )
    )


# Per-Broker Settings
@router.get("/profiles/{profile_id}/brokers/{broker_id}/settings")
async def get_broker_settings(profile_id: str, broker_id: str):
    """Get settings for a specific broker within a profile"""
    profile = await db.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    broker_settings = profile.get('broker_settings', {})
    if broker_id in broker_settings:
        return broker_settings[broker_id]
    
    default = BrokerSettings(broker_id=broker_id, enabled=broker_id in profile.get('active_brokers', []))
    return default.model_dump()


@router.put("/profiles/{profile_id}/brokers/{broker_id}/settings")
async def update_broker_settings(profile_id: str, broker_id: str, update_data: BrokerSettingsUpdate):
    """Update settings for a specific broker within a profile"""
    profile = await db.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    broker_settings = profile.get('broker_settings', {})
    
    if broker_id in broker_settings:
        current = broker_settings[broker_id]
    else:
        current = BrokerSettings(broker_id=broker_id).model_dump()
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    current.update(update_dict)
    current['broker_id'] = broker_id
    
    # Update active_brokers list if enabled changed
    active_brokers = profile.get('active_brokers', [])
    if 'enabled' in update_dict:
        if update_dict['enabled'] and broker_id not in active_brokers:
            active_brokers.append(broker_id)
        elif not update_dict['enabled'] and broker_id in active_brokers:
            active_brokers.remove(broker_id)
    
    broker_settings[broker_id] = current
    
    await db.update_profile(profile_id, {'broker_settings': broker_settings, 'active_brokers': active_brokers})
    
    return current


@router.post("/profiles/{profile_id}/brokers/{broker_id}/settings/toggle/{setting_name}")
async def toggle_broker_setting(profile_id: str, broker_id: str, setting_name: str):
    """Toggle a boolean setting for a specific broker"""
    valid_toggles = [
        'enabled', 'auto_trading_enabled', 'alerts_only', 'premium_buffer_enabled',
        'averaging_down_enabled', 'take_profit_enabled', 'bracket_order_enabled',
        'stop_loss_enabled', 'trailing_stop_enabled', 'auto_shutdown_enabled'
    ]
    
    if setting_name not in valid_toggles:
        raise HTTPException(status_code=400, detail=f"Invalid setting. Valid: {valid_toggles}")
    
    profile = await db.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    broker_settings = profile.get('broker_settings', {})
    
    if broker_id in broker_settings:
        current = broker_settings[broker_id]
    else:
        current = BrokerSettings(broker_id=broker_id).model_dump()
    
    current_value = current.get(setting_name, False)
    current[setting_name] = not current_value
    current['broker_id'] = broker_id
    
    # Update active_brokers list if enabled changed
    active_brokers = profile.get('active_brokers', [])
    if setting_name == 'enabled':
        if current['enabled'] and broker_id not in active_brokers:
            active_brokers.append(broker_id)
        elif not current['enabled'] and broker_id in active_brokers:
            active_brokers.remove(broker_id)
    
    broker_settings[broker_id] = current
    
    await db.update_profile(profile_id, {'broker_settings': broker_settings, 'active_brokers': active_brokers})
    
    return {setting_name: current[setting_name], 'broker_settings': current}


@router.get("/profiles/{profile_id}/all-broker-settings")
async def get_all_broker_settings(profile_id: str):
    """Get settings for all brokers in a profile"""
    profile = await db.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    broker_settings = profile.get('broker_settings', {})
    active_brokers = profile.get('active_brokers', [])
    
    from models import BrokerType
    all_brokers = [b.value for b in BrokerType]  # FIXED M24: driven by enum
    
    result = {}
    for broker_id in all_brokers:
        if broker_id in broker_settings:
            result[broker_id] = broker_settings[broker_id]
        else:
            result[broker_id] = BrokerSettings(
                broker_id=broker_id, 
                enabled=broker_id in active_brokers
            ).model_dump()
    
    return result
