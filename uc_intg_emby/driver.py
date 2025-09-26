"""
Emby integration driver for Unfolded Circle Remote Two/3.
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

# Globals
api: ucapi.IntegrationAPI = None
config: Config = None
client: EmbyClient = None
media_players = {}
entities_ready = False
_main_task = None
_connection_monitor_task = None

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
    asyncio.create_task(initialize_integration())
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


async def initialize_integration():
    """(Re)Initializes the integration, client, and entities."""
    global client, entities_ready, media_players, api
    _LOG.info("Initializing integration...")
    if not config.is_configured():
        _LOG.warning("Integration not configured. Aborting initialization.")
        await api.set_device_state(ucapi.DeviceStates.DISCONNECTED)
        return

    await api.set_device_state(ucapi.DeviceStates.CONNECTING)
    
    if client: await client.close()
    for player in media_players.values(): player.stop_monitoring()
    media_players.clear()
    api.available_entities.clear()

    client = EmbyClient(config.server_url, config.api_key, config.user_id)
    success, message = await client.test_connection()

    if not success:
        _LOG.error(f"Failed to connect to Emby: {message}")
        await api.set_device_state(ucapi.DeviceStates.ERROR)
        return

    _LOG.info(f"Successfully connected to Emby: {message}")
    entities_ready = True
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)
    start_session_polling()

async def poll_for_sessions():
    """Periodically poll for Emby sessions and update available entities."""
    global client, media_players, api
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
    _LOG.info("Remote connected")
    if config.is_configured() and not entities_ready:
        await initialize_integration()
    elif entities_ready:
        await api.set_device_state(ucapi.DeviceStates.CONNECTED)
    else:
        await api.set_device_state(ucapi.DeviceStates.DISCONNECTED)

async def on_subscribe_entities(entity_ids: List[str]):
    _LOG.info(f"Subscription request for: {entity_ids}")
    for entity_id in entity_ids:
        player = next((p for p in media_players.values() if p.id == entity_id), None)
        if player:
            api.configured_entities.add(player)
            await player.start_monitoring()

async def on_unsubscribe_entities(entity_ids: List[str]):
    _LOG.info(f"Unsubscribe request for: {entity_ids}")
    for entity_id in entity_ids:
        player = next((p for p in media_players.values() if p.id == entity_id), None)
        if player:
            player.stop_monitoring()
            api.configured_entities.remove(player.id)

async def main():
    global api, config, _main_task
    try:
        config = Config()
        driver_path = os.path.join(os.path.dirname(__file__), "..", "driver.json")
        api = ucapi.IntegrationAPI(loop=asyncio.get_running_loop())
        
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
        if client: await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _LOG.info("Integration stopped by user.")
    except Exception as e:
        _LOG.critical(f"Integration crashed: {e}", exc_info=True)
        sys.exit(1)