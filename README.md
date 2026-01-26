# Emby Media Server Integration for Unfolded Circle Remote 2/3

Control your Emby Media Server directly from your Unfolded Circle Remote 2 or Remote 3 with comprehensive media player functionality for active sessions, **real-time session discovery**, and **multi-user support**.

![Emby](https://img.shields.io/badge/Emby-Media%20Server-green)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-emby?style=flat-square)](https://github.com/mase1981/uc-intg-emby/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-emby?style=flat-square)](https://github.com/mase1981/uc-intg-emby/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://unfolded.community/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-emby/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)


## Features

This integration provides comprehensive control of active Emby sessions directly from your Unfolded Circle Remote, with automatic session detection and real-time media player functionality.

---
## ❤️ Support Development ❤️

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️
---

### 📺 **Media Player Functionality**

#### **Real-time Session Discovery**
- **Automatic Detection** - Detects active Emby playback sessions
- **Multi-User Support** - Supports sessions across multiple users (optional filtering)
- **Dynamic Creation** - Media player entities created automatically for active sessions
- **Session Monitoring** - Continuous monitoring for new/ended sessions

#### **Transport Controls**
- **Play/Pause** - Playback control with state feedback
- **Stop** - Stop playback
- **Next** - Skip to next track/episode
- **Previous** - Skip to previous track/episode

#### **Rich Media Information Display**
- **Two-Row Display** - Optimized for TV shows with episode and series information
  - **Row 1**: Episode name for TV shows, track name for music, title for movies
  - **Row 2**: Series name with season/episode info, artist for music
- **Media Types** - Full support for Movies, TV Episodes, Music, and generic video
- **Artwork Display** - Media artwork
- **Progress Tracking** - Real-time position and duration information

#### **Entity Lifecycle Management**
- **Dynamic Creation** - New sessions automatically create media player entities
- **Automatic Cleanup** - Ended sessions remove corresponding entities
- **State Persistence** - Maintains entity state across Remote reboots
- **Connection Monitoring** - Automatic reconnection and status recovery

### **Server Requirements**

#### **Emby Media Server Compatibility**
- **Emby Server**: Version 4.0 or higher recommended
- **Network Access**: HTTP/HTTPS API access to Emby server
- **API Key**: Emby API key for authentication
- **Active Sessions**: Integration controls active playback sessions only
- **Protocol Support**: Both HTTP and HTTPS Emby servers supported

### **Network Requirements**

- **API Access**: HTTP/HTTPS access to Emby server on configured port
- **Default Port**: Port 8096 (HTTP) or 8920 (HTTPS) - custom ports supported
- **Authentication**: Valid Emby API key with session control permissions
- **Local/Remote**: Works with both local network and remote Emby servers

## Installation

### Option 1: Remote Web Interface (Recommended)
1. Navigate to the [**Releases**](https://github.com/mase1981/uc-intg-emby/releases) page
2. Download the latest `uc-intg-emby-<version>-aarch64.tar.gz` file
3. Open your remote's web interface (`http://your-remote-ip`)
4. Go to **Settings** → **Integrations** → **Add Integration**
5. Click **Upload** and select the downloaded `.tar.gz` file

### Option 2: Docker (Advanced Users)

The integration is available as a pre-built Docker image from GitHub Container Registry:

**Image**: `ghcr.io/mase1981/uc-intg-emby:latest`

**Docker Compose:**
```yaml
services:
  uc-intg-emby:
    image: ghcr.io/mase1981/uc-intg-emby:latest
    container_name: uc-intg-emby
    network_mode: host
    volumes:
      - </local/path>:/data
    environment:
      - UC_CONFIG_HOME=/data
      - UC_INTEGRATION_HTTP_PORT=9090
      - UC_INTEGRATION_INTERFACE=0.0.0.0
      - PYTHONPATH=/app
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name uc-emby --restart unless-stopped --network host -v emby-config:/app/config -e UC_CONFIG_HOME=/app/config -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e PYTHONPATH=/app ghcr.io/mase1981/uc-intg-emby:latest
```

## Configuration

### Step 1: Prepare Your Emby Server

**IMPORTANT**: Emby server must be accessible before adding the integration.

#### Enable API Access:
1. Open Emby Server Dashboard
2. Navigate to **Advanced** → **API Keys**
3. Click **New API Key** and create a key for "Unfolded Circle Integration"
4. Copy the generated API key (32-character hex string)

#### Server Information:
- Note your Emby server URL: `http://server-ip:8096` or `https://server-ip:8920`
- For custom ports: `http://server-ip:custom-port`
- Ensure server is accessible from Remote network location

#### Optional User Filtering:
- Find User ID for session filtering (optional)
- Dashboard → Users → Select User → Note the User ID from URL
- Leave blank to show all user sessions

### Step 2: Setup Integration

1. After installation, go to **Settings** → **Integrations**
2. The Emby integration should appear in **Available Integrations**
3. Click **"Configure"** and enter the following:

   **Server Configuration:**
   - **Server URL**: Your Emby server URL (e.g., `http://192.168.1.100:8096` or `https://emby.example.com:8920`)
   - **API Key**: The 32-character API key from Emby Dashboard
   - **User ID** (Optional): Specific user ID to filter sessions (leave blank for all users)

4. Click **"Complete Setup"** - the integration will test the connection
5. Active Emby sessions will automatically appear as media player entities

## Using the Integration

### Media Player Entities

The integration creates media player entities for each active Emby session:

- **Entity Naming**: Named after the playback device/client (e.g., "Fire TV (Emby for Fire TV)")
- **Transport Control**: Play, Pause, Stop, Next, Previous
- **Media Information**: Title, artist/series, album, artwork, duration, position
- **State Feedback**: Real-time playback state updates
- **Dynamic Creation**: Entities appear when sessions start, disappear when sessions end

### Active Session Control

- **Session-Based**: Controls active Emby sessions rather than server itself
- **Real-time Monitoring**: Continuous session monitoring with 5-second updates
- **Client-Based Naming**: Entities named after the playback device/client
- **Rich Information**: Two-row display optimized for different media types

## Credits

- **Developer**: Meir Miyara
- **Emby Protocol**: Built using official Emby Server API documentation
- **Unfolded Circle**: Remote 2/3 integration framework (ucapi)
- **Community**: Testing and feedback from UC community with Emby servers

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0) - see LICENSE file for details.

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-emby/issues)
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)

---

**Made with ❤️ for the Unfolded Circle Community**

**Thank You**: Meir Miyara
