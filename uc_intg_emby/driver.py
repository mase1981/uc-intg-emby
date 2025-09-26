"""
Emby integration driver for Unfolded Circle Remote Two/3.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""
import asyncio
import logging
import os
import sys
from typing import List

import ucapi
from uc_intg_emby.client import EmbyClient
from uc_intg_emby.config import Config
from uc_intg_emby.media_player import EmbyMediaPlayer

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_LOG = logging.getLogger(__name__)

api: ucapi.IntegrationAPI = None
config: Config = None
client: EmbyClient = None
media_players = {}
entities_ready = False
_main_task = None
_connection_monitor_task = None
_initialization_lock = asyncio.Lock()

async def _initialize_entities():
    """Initialize entities with race condition protection - MANDATORY for reboot survival."""
    global config, client, api, entities_ready, media_players
    
    async with _initialization_lock:
        if entities_ready:
            _LOG.debug("Entities already initialized, skipping")
            return
            
        if not config or not config.is_configured():
            _LOG.info("Integration not configured, skipping entity initialization")
            return
            
        _LOG.info("Initializing entities for reboot survival...")
        
        try:
            # Initialize client
            if client:
                await client.close()
            
            client = EmbyClient(config.server_url, config.api_key, config.user_id)
            success, message = await client.test_connection()
            
            if not success:
                _LOG.error(f"Failed to connect to Emby during initialization: {message}")
                return
                
            # Clear existing entities and media players
            for player in media_players.values():
                player.stop_monitoring()
            media_players.clear()
            api.available_entities.clear()
            
            # Mark entities as ready BEFORE setting connected state
            entities_ready = True
            
            _LOG.info(f"Successfully initialized Emby connection: {message}")
            _LOG.info("Entities ready for subscription - starting session polling")
            
            # Start session polling to create dynamic entities
            start_session_polling()
            
        except Exception as e:
            _LOG.error("Failed to initialize entities: %s", e)
            entities_ready = False
            raise

async def process_setup_data(setup_data: dict):
    """Process provided setup data, test connection, and initialize."""
    server_url = setup_data.get("server_url", "").strip()
    api_key = setup_data.get("api_key", "").strip()
    user_id = setup_data.get("user_id", "").strip()

    if not server_url or not api_key:
        return ucapi.SetupError(ucapi.IntegrationSetupError.INVALID_INPUT, "URL and API Key are required.")

    temp_client = EmbyClient(server_url, api_key, user_id)
    success, message = await temp_client.test_connection()
    await temp_client.close()

    if not success:
        return ucapi.SetupError(ucapi.IntegrationSetupError.CONNECTION_REFUSED, message)

    config.update_config({"server_url": server_url, "api_key": api_key, "user_id": user_id})
    
    # Initialize entities after successful setup
    await _initialize_entities()
    return ucapi.SetupComplete()

async def setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """Handles the setup process correctly."""
    global config

    # Handle initial setup request or reconfiguration
    if isinstance(msg, ucapi.DriverSetupRequest):
        # If remote provides data directly, process it without asking user
        if msg.setup_data:
            _LOG.info("Processing setup data provided by remote.")
            return await process_setup_data(msg.setup_data)
        
        # Otherwise, ask the user for input
        _LOG.info("Setup requested. Sending configuration fields to remote.")
        return ucapi.RequestUserInput(
            title={"en": "Emby Server Configuration"},
            settings=[
                {"id": "server_url", "label": {"en": "Server URL"}, "field": {"text": {"value": config.server_url or "http://"}}},
                {"id": "api_key", "label": {"en": "API Key"}, "field": {"text": {"value": config.api_key or ""}}},
                {"id": "user_id", "label": {"en": "User ID (optional)"}, "field": {"text": {"value": config.user_id or ""}}},
            ]
        )

    # Handle the user's submitted data
    if isinstance(msg, ucapi.UserDataResponse):
        _LOG.info("Received user data for setup.")
        return await process_setup_data(msg.input_values)

    # Handle abort message
    if isinstance(msg, ucapi.AbortDriverSetup):
        _LOG.warning(f"Setup aborted by remote: {msg.error}")
        return ucapi.SetupError(msg.error)

    _LOG.error(f"Received unknown setup message type: {type(msg)}")
    return ucapi.SetupError(ucapi.IntegrationSetupError.OTHER)

async def poll_for_sessions():
    """Periodically poll for Emby sessions and update available entities."""
    global client, media_players, api, entities_ready
    
    while entities_ready:
        try:
            sessions = await client.get_sessions() if client else []
            active_session_ids = {s['Id'] for s in sessions}

            for session in sessions:
                session_id = session['Id']
                if session_id not in media_players:
                    _LOG.info(f"Found new session: {session.get('DeviceName')}")
                    player = EmbyMediaPlayer(client, session, api)
                    media_players[session_id] = player
                    api.available_entities.add(player)

            ended_session_ids = set(media_players.keys()) - active_session_ids
            for session_id in ended_session_ids:
                _LOG.info(f"Session ended: {media_players[session_id].name.get('en')}")
                player = media_players.pop(session_id)
                player.stop_monitoring()
                api.available_entities.remove(player.id)
            
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            break
        except Exception as e:
            _LOG.error(f"Error in session polling loop: {e}", exc_info=True)
            await asyncio.sleep(30)

def start_session_polling():
    global _connection_monitor_task
    if _connection_monitor_task and not _connection_monitor_task.done():
        _connection_monitor_task.cancel()
    _connection_monitor_task = asyncio.create_task(poll_for_sessions())

async def on_connect():
    """Handle Remote connection with reboot survival - MANDATORY IMPLEMENTATION."""
    global config, entities_ready
    
    _LOG.info("Remote connected. Checking configuration state...")
    
    if not config:
        config = Config()
    
    config.reload_from_disk()
    
    # If configured but entities not ready, initialize them now
    if config.is_configured() and not entities_ready:
        _LOG.info("Configuration found but entities missing, reinitializing for reboot survival...")
        try:
            await _initialize_entities()
        except Exception as e:
            _LOG.error("Failed to reinitialize entities: %s", e)
            await api.set_device_state(ucapi.DeviceStates.ERROR)
            return
    
    # Set appropriate device state
    if config.is_configured() and entities_ready:
        await api.set_device_state(ucapi.DeviceStates.CONNECTED)
    elif not config.is_configured():
        await api.set_device_state(ucapi.DeviceStates.DISCONNECTED)
    else:
        await api.set_device_state(ucapi.DeviceStates.ERROR)

async def on_subscribe_entities(entity_ids: List[str]):
    """Handle entity subscriptions with race condition protection - CRITICAL FIX."""
    _LOG.info(f"Entities subscription requested: {entity_ids}")
    
    # Guard against race condition - MANDATORY CHECK
    if not entities_ready:
        _LOG.error("RACE CONDITION: Subscription before entities ready! Attempting recovery...")
        if config and config.is_configured():
            await _initialize_entities()
        else:
            _LOG.error("Cannot recover - no configuration available")
            return
    
    available_entity_ids = []
    for player in media_players.values():
        available_entity_ids.append(player.id)
    
    _LOG.info(f"Available entities: {available_entity_ids}")
    
    # Process subscriptions
    for entity_id in entity_ids:
        player = next((p for p in media_players.values() if p.id == entity_id), None)
        if player:
            api.configured_entities.add(player)
            await player.start_monitoring()
        else:
            _LOG.warning(f"Subscription requested for unknown entity: {entity_id}")

async def on_unsubscribe_entities(entity_ids: List[str]):
    _LOG.info(f"Unsubscribe request for: {entity_ids}")
    for entity_id in entity_ids:
        player = next((p for p in media_players.values() if p.id == entity_id), None)
        if player:
            player.stop_monitoring()
            api.configured_entities.remove(player.id)

async def main():
    """Main entry point with pre-initialization for reboot survival - MANDATORY PATTERN."""
    global api, config, _main_task
    
    try:
        loop = asyncio.get_running_loop()
        api = ucapi.IntegrationAPI(loop=loop)
        
        config = Config()
        if config.is_configured():
            _LOG.info("Found existing configuration, pre-initializing entities for reboot survival")
            loop.create_task(_initialize_entities())
        
        driver_path = os.path.join(os.path.dirname(__file__), "..", "driver.json")
        
        # Register event handlers
        api.add_listener(ucapi.Events.CONNECT, on_connect)
        api.add_listener(ucapi.Events.SUBSCRIBE_ENTITIES, on_subscribe_entities)
        api.add_listener(ucapi.Events.UNSUBSCRIBE_ENTITIES, on_unsubscribe_entities)
        
        await api.init(driver_path, setup_handler)
        _LOG.info("Driver initialized. Waiting for connection.")
        
        _main_task = asyncio.Future()
        await _main_task
        
    except asyncio.CancelledError:
        _LOG.info("Main task cancelled.")
    finally:
        if client: 
            await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _LOG.info("Integration stopped by user.")
    except Exception as e:
        _LOG.critical(f"Integration crashed: {e}", exc_info=True)
        sys.exit(1)