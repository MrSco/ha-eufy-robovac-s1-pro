# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for the Eufy RoboVac S1 Pro (model T2080). It uses local network communication via the Tuya protocol to control the vacuum cleaner without cloud dependency.

## Architecture

### Authentication Flow
1. User provides Eufy account credentials (username/password)
2. Integration authenticates with Eufy API to get user info
3. User ID is prefixed with "eh-" to create Tuya username
4. Tuya API session is established to list homes and devices
5. Local keys are retrieved for each device from Tuya API

### Device Discovery
- Uses UDP broadcast listeners on ports 6666 and 6667
- Devices broadcast their presence on local network
- Discovery matches Tuya device IDs with local IPs
- **Docker users**: Must expose ports 6666/udp and 6667/udp

### Communication Protocol
- Uses Tuya protocol v3.3 with local encryption (AES ECB mode)
- Device communicates via TCP port 6668
- Messages include CRC32 validation and sequence numbers
- DPS (Data Point) system: Each device function maps to a numbered DPS

### Core Components

**custom_components/eufy_robovac_s1_pro/__init__.py**
- Entry point for the integration
- Sets up coordinator for each discovered device
- Update interval: 30 seconds

**coordinators.py**
- `EufyTuyaDataUpdateCoordinator`: Manages data updates from Tuya device
- Handles incoming messages (GET_COMMAND, GRATUITOUS_UPDATE)
- Includes DPS discovery logging (useful for debugging new features)

**tuya.py**
- Low-level Tuya protocol implementation
- `TuyaDevice`: Handles connection, encryption, message parsing
- `TuyaCipher`: AES encryption/decryption for Tuya v3.3
- Implements ping/pong keepalive mechanism

**vacuum.py**
- Main vacuum entity implementation
- State detection via DPS 153 (most reliable) with DPS 152/6/7 fallbacks
- Uses base64-decoded byte patterns for state interpretation
- Critical DPS mappings:
  - DPS 8: Battery level (0-100)
  - DPS 9: Fan speed (gentle/normal/strong/max)
  - DPS 152: Command input (base64 encoded)
  - DPS 153: Status output (base64 encoded byte patterns)
  - DPS 158: Fan speed display name
- State machine tracks pause/resume correctly

**discovery.py**
- UDP datagram protocol handler
- Decrypts broadcasts using MD5-derived key
- Timeout: 6 seconds for discovery

**eufy_local_id_grabber/**
- Authenticates with Eufy cloud API
- Retrieves Tuya credentials and local keys
- Implements Tuya's HMAC signature algorithm
- Constants include API endpoints and client IDs

**config_flow.py**
- Configuration UI for Home Assistant
- Validates credentials by attempting login

### Platform Files
- **button.py**: Maintenance reset buttons (side brush, main brush, filter, sensor)
- **sensor.py**: Battery, status, cleaning statistics
- **switch.py**: Auto-return toggle
- **number.py**: Numeric controls (if any)
- **select.py**: Cleaning mode, water level, suction power selection

## Key DPS Values for S1 Pro

Critical data points (from logs and code):
- **5**: Cleaning mode (auto/smart/pause/charge)
- **6**: Status indicator 1 (values >=100 indicate errors)
- **7**: Status indicator 2
- **8**: Battery level percentage
- **9**: Fan speed raw value (gentle/normal/strong/max)
- **152**: Command input (base64: AA==, AggO, AggN, AggG)
- **153**: Status byte pattern (base64 encoded, see decode_dps153_to_state)
- **158**: Fan speed display name (Quiet/Standard/Turbo/Max)

State detection pattern (DPS 153):
- Cleaning: Byte[1]=0x0a, Byte[2]=0x00, Byte[3]=0x10, Byte[4]=0x05, length=7
- Paused: Same as cleaning but length>=9 and Byte[6]=0x02
- Returning: Byte[1]=0x10, Byte[2]=0x07, Byte[3]=0x42
- Docked: Byte[1]=0x10 with various Byte[2] values for substatus

## Development Commands

### Testing
No formal test suite exists. Manual testing required with actual hardware.

### Installation Testing
```bash
# Copy to Home Assistant config directory
cp -r custom_components/eufy_robovac_s1_pro /config/custom_components/

# Restart Home Assistant
# Via Home Assistant UI: Settings > System > Restart
```

### Debugging
Enable debug logging in Home Assistant's configuration.yaml:
```yaml
logger:
  default: info
  logs:
    custom_components.eufy_robovac_s1_pro: debug
```

Key debug logs to watch:
- DPS discovery logs show all available data points
- State transition logs in vacuum.py
- Tuya message handling in coordinators.py

### Version Updates
Update version in manifest.json before release.

## Common Pitfalls

1. **Docker networking**: Ports 6666/6667 UDP must be exposed
2. **Local key changes**: If devices are removed/re-added in Eufy app, local keys change
3. **State detection**: DPS 153 is most reliable; don't rely solely on DPS 152
4. **Encryption requirement**: Messages to device must use AES encryption (v3.3+)
5. **Command timing**: Allow 0.5-2 seconds between commands for device to process
6. **Resume vs Start**: Use different commands based on pause state flag

## Protocol Notes

- Tuya protocol is polling-based (30s default) with gratuitous updates
- Device broadcasts status changes independently
- Commands are fire-and-forget; verify success by checking state
- CRC32 validation prevents message corruption
- Sequence numbers track request/response pairs

## Related Projects

Based on [ha-eufy-robovac-g10-hybrid](https://github.com/Rjevski/ha-eufy-robovac-g10-hybrid) with modifications for S1 Pro.

Discovery code from [localtuya](https://github.com/rospogrigio/localtuya) project.
