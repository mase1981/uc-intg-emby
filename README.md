# Emby Media Server Integration for Unfolded Circle Remote 2/3

Control your Emby Media Server directly from your Unfolded Circle Remote 2 or Remote 3 with comprehensive media player functionality for active sessions.

![Emby](https://img.shields.io/badge/Emby-Media%20Server-green)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-emby)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-emby/total)
![License](https://img.shields.io/badge/license-MPL--2.0-blue)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA)](https://github.com/sponsors/mase1981/button)

## Features

This integration provides comprehensive control of active Emby sessions directly from your Unfolded Circle Remote, with automatic session detection and real-time media player functionality.

### 📺 **Media Player Functionality**

#### **Features**
- **Real-time Session Discovery**: Automatically detects active Emby playback sessions
- **Multi-User Support**: Supports sessions across multiple users (optional user filtering)
- **Dynamic Entity Creation**: Media player entities created automatically for active sessions
- **Session Monitoring**: Continuous monitoring for new/ended sessions
- **Transport Controls**: Basic Commands: Play/Pause, Stop, Next, Previous, etc

#### **Rich Media Information Display**
- **Two-Row Display**: Optimized for TV shows with episode and series information
  - **Row 1**: Episode name for TV shows, track name for music, title for movies
  - **Row 2**: Series name with season/episode info, artist for music
- **Media Types**: Full support for Movies, TV Episodes, Music, and generic video
- **Artwork Display**: Media artwork
- **Progress Tracking**: Real-time position and duration information

#### **Entity Lifecycle Management**
- **Dynamic Creation**: New sessions automatically create media player entities
- **Automatic Cleanup**: Ended sessions remove corresponding entities
- **State Persistence**: Maintains entity state across Remote reboots
- **Connection Monitoring**: Automatic reconnection and status recovery

## Server Requirements

### **Emby Media Server Compatibility**
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

### **API Key Requirements**
- **Server Settings**: Generated from Emby Server Dashboard → API Keys (This is a Must)
- **Permissions**: Must allow session control and media information access
- **User Association**: Optional - can filter sessions by specific user ID

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
      - ./data:/config
    environment:
      - UC_INTEGRATION_HTTP_PORT=9090
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name=uc-intg-emby --network host -v </local/path>:/config --restart unless-stopped ghcr.io/mase1981/uc-intg-emby:latest
```

## Configuration

### Step 1: Prepare Your Emby Server

1. **Enable API Access:**
   - Open Emby Server Dashboard
   - Navigate to **Advanced** → **API Keys**
   - Click **New API Key** and create a key for "Unfolded Circle Integration"
   - Copy the generated API key (32-character hex string)

2. **Server Information:**
   - Note your Emby server URL: `http://server-ip:8096` or `https://server-ip:8920`
   - For custom ports: `http://server-ip:custom-port`
   - Ensure server is accessible from Remote network location

3. **Optional User Filtering:**
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

## Usage Examples

### Basic Setup
```
Setup Input:
- Server URL: http://192.168.1.100:8096
- API Key: f8639b50563349b8b8c56b9015b75b48
- User ID: (blank - all users)

Result:
- Active sessions automatically detected
- Media players created per active session
- Real-time control and status updates
```

### Secure Server Setup
```
Setup Input:
- Server URL: https://emby.mydomain.com:8920
- API Key: a1b2c3d4e5f6789012345678901234ab
- User ID: e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3

Result:
- HTTPS connection to remote Emby server
- Sessions filtered to specific user only
- Secure API communication
```

### Multiple Clients
```
Active Sessions:
- Living Room TV (Fire TV) → "Fire TV (Emby for Fire TV)"
- Bedroom Tablet (Android) → "Samsung Tablet (Emby Mobile)"
- Kitchen Display (Web) → "Chrome Browser (Emby Web)"

All sessions controllable simultaneously from Remote
```

## Troubleshooting

### Common Issues

**Server Connection Failed:**
- Verify Emby server URL is correct and accessible
- Test URL in browser: should show Emby web interface
- Check API key is valid (32-character hex string)
- Ensure server is running and network accessible

**Authentication Error:**
- Verify API key is correct from Emby Dashboard → API Keys
- Check API key permissions allow session access
- Try regenerating API key if connection fails

**No Media Players Appear:**
- Start playing content on an Emby client first
- Check User ID filter - leave blank to see all sessions
- Verify active sessions exist in Emby Dashboard → Activity
- Check integration logs for session detection errors

**Commands Not Working:**
- Ensure target session is still active
- Check client supports remote control (most do)
- Verify network connectivity to Emby server
- Some clients may have limited command support

**HTTPS Connection Issues:**
- Verify SSL certificate is valid (or use HTTP for testing)
- Check firewall allows HTTPS traffic on Emby port
- Ensure Remote can access HTTPS URLs
- Test with HTTP first to isolate SSL issues

### Debug Information

Enable detailed logging for troubleshooting:

**Docker Environment:**
```bash
# Add to docker-compose.yml environment section
- LOG_LEVEL=DEBUG

# View logs
docker logs uc-intg-emby
```

**Integration Logs:**
- **Remote Interface**: Settings → Integrations → Emby → View Logs
- **Common Errors**: API authentication, session detection, command failures

**Server Verification:**
Test Emby server API access:
```bash
# Test server info
curl "http://server-ip:8096/System/Info?api_key=YOUR_API_KEY"

# Test sessions endpoint
curl "http://server-ip:8096/Sessions?api_key=YOUR_API_KEY"

# HTTPS example
curl "https://server-ip:8920/System/Info?api_key=YOUR_API_KEY"
```

**Network Connectivity:**
```bash
# Test basic connectivity
ping server-ip

# Test port access
telnet server-ip 8096
nmap -p 8096 server-ip

# HTTPS port test
openssl s_client -connect server-ip:8920
```

## For Developers

### Local Development

1. **Clone and setup:**
   ```bash
   git clone https://github.com/mase1981/uc-intg-emby.git
   cd uc-intg-emby
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configuration:**
   ```bash
   # Development configuration
   # Run integration and configure via Remote interface
   python -m uc_intg_emby.driver
   # Integration runs on localhost:9090
   ```

3. **VS Code debugging:**
   - Open project in VS Code
   - Use F5 to start debugging session
   - Configure integration with your Emby server

### Project Structure

```
uc-intg-emby/
├── uc_intg_emby/              # Main package
│   ├── __init__.py            # Package info
│   ├── client.py              # Emby HTTP API client
│   ├── config.py              # Configuration management
│   ├── driver.py              # Main integration driver
│   ├── media_player.py        # Media player entity
│   └── setup.py               # Setup flow handler
├── .github/workflows/         # GitHub Actions CI/CD
│   └── build.yml              # Automated build pipeline
├── docker-compose.yml         # Docker deployment
├── Dockerfile                 # Container build instructions
├── docker-entry.sh            # Container entry point
├── driver.json                # Integration metadata
├── requirements.txt           # Dependencies
├── pyproject.toml             # Python project config
└── README.md                  # This file
```

### Development Features

#### **Emby API Implementation**
Complete Emby server API integration:
- **HTTP Client**: Comprehensive HTTP API client with session management
- **Authentication**: API key-based authentication with connection testing
- **Session Control**: Full session command support (play, pause, seek, volume)
- **Status Monitoring**: Real-time session status and media information

#### **Entity Architecture**
Production-ready media player entities:
- **Dynamic Creation**: Automatic entity creation for active sessions
- **State Persistence**: Entity state survives Remote reboots
- **Real-time Updates**: Continuous session monitoring and updates
- **Clean Naming**: User-friendly entity names based on client information

#### **Protocol Support**
Comprehensive server support:
- **HTTP/HTTPS**: Full support for both secure and standard connections
- **Custom Ports**: Flexible port configuration beyond defaults
- **Error Handling**: Robust connection management and recovery
- **User Filtering**: Optional session filtering by user ID

### Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run integration
python -m uc_intg_emby.driver

# Configure with your Emby server
# Start media playback on Emby clients
# Test all media player controls from Remote
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test with Emby server
4. Test with multiple session types (TV, movies, music)
5. Verify HTTPS and HTTP server support
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## Architecture Notes

### **Current Implementation**
- **Session-Based Control**: Controls active Emby sessions rather than server itself
- **Dynamic Entities**: Media players created/removed based on session activity
- **Real-time Monitoring**: Continuous session monitoring with 5-second updates
- **HTTP API Communication**: Direct REST API communication with Emby server

### **Entity Design Philosophy**
- **Active Sessions Only**: Only shows entities for sessions with active playback
- **Client-Based Naming**: Entities named after the playback device/client
- **Rich Information**: Two-row display optimized for different media types
- **Transport Control**: Full playback control matching client capabilities

### **Protocol Implementation**
- **RESTful API**: HTTP-based communication using Emby's REST API
- **Session Commands**: Direct session control via `/Sessions/{id}/Command` endpoints
- **Status Polling**: Regular status updates via `/Sessions` endpoint
- **Secure Communication**: Full HTTPS support with proper SSL handling

## Credits

- **Developer**: Meir Miyara
- **Emby Protocol**: Built using official Emby Server API documentation
- **Unfolded Circle**: Remote 2/3 integration framework (ucapi)
- **Community**: Testing and feedback from UC community with Emby servers

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-emby/issues)
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)

---

**Made with ❤️ for the Unfolded Circle Community**

**Thank You**: Meir Miyara