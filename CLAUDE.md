# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**JukeboxPi** is a USB numeric keypad-controlled music jukebox that plays Spotify albums/playlists on Sonos speakers. It listens to hardware input events from a connected USB keypad and triggers music playback through Spotify or Sonos APIs.

### Key Features
- Maps numeric keypad inputs (single or multi-digit) to Spotify albums/playlists
- Supports both Spotify Web API and direct Sonos control methods
- Text-to-speech announcements of song selections
- Multi-digit input buffering with configurable timeout
- Playback controls (play, pause, next, skip)

## Architecture Overview

The single production script is `JukeBoxSonosProd.py`, which uses the `soco` library for Sonos control, `evdev` for USB keypad input, and `gtts` for text-to-speech announcements.

### Core Execution Flow

1. **Config Loading**: Loads settings from JSON configuration files
2. **Device Connection**: Discovers and connects to Spotify device or Sonos speaker
3. **Keypad Discovery**: Finds USB input device with multi-level fallback strategy (configured name → HID detection → configured path → generic keyboard)
4. **Input Loop**: Reads hardware key events using `evdev` library
5. **Number Buffering**: Accumulates digits with timeout-based release (multi-digit support)
6. **Playback Trigger**: Maps number to URI, announces selection, starts playback

### Data Flow

```
USB Keypad (evdev)
    ↓
Input Buffer (number accumulation)
    ↓
music_mappings.json (number → URI mapping)
    ↓
Spotify Web API OR Sonos SOAP/SoCo API
    ↓
Speaker Output
```

## Configuration

### config_sonos.json
```json
{
  "sonos_ip_address": "192.168.1.140",
  "sonos_room_name": "Den",
  "announce_selections": true,
  "announcement_volume": 30,
  "multi_digit_timeout": 2.0,
  "keyboard_device_name": "HID 04f3:0103",
  "keyboard_device_path": null
}
```

### music_mappings.json
Maps numeric inputs to Spotify URIs:
```json
{
  "1": {
    "title": "Album Name",
    "uri": "spotify:album:ID",
    "filename": "optional_image.png"
  },
  "99": {
    "title": "Playlist Name",
    "uri": "spotify:playlist:ID",
    "filename": "optional_image.png"
  }
}
```

## Key Technologies & Dependencies

- **soco**: High-level Sonos control
- **evdev**: Linux input device event handling
- **gtts**: Google Translate TTS for announcements

## Running the Code

### Prerequisites
- Python 3.7+
- USB numeric keypad connected
- Sonos speaker on the local network
- Linux/Raspberry Pi environment for `evdev` and `/dev/input` access

### Installation
```bash
pip install soco evdev gtts
```

### Running
```bash
python JukeBoxSonosProd.py
```

The script will:
1. Load configuration from `config_sonos.json`
2. Connect to Sonos speaker
3. Discover USB keyboard/keypad
4. Wait for numeric input and trigger playback
5. Press Ctrl+C to exit

## Code Patterns & Conventions

### Configuration Management
- Always use `Path(__file__).parent` to locate config files relative to script location
- Load both config and music_mappings at module level after defining load_config()

### Keypad Detection
- Modern variants (JukeBoxSonosProd.py) implement priority-based device detection:
  1. Exact name match (case-insensitive)
  2. Partial name match
  3. HID device detection
  4. Configured device path
  5. Generic keyboard/keypad search
  6. First available device

### Input Processing
- Buffer digits until timeout expires OR Enter key pressed
- Each digit press updates `last_keypress_time`
- Timeout check happens on every event loop iteration

### Error Handling
- Extensive debug logging with `[DEBUG]` prefix in production variants
- Graceful fallbacks for device discovery
- Try/except blocks around Spotify API calls and Sonos SOAP requests

### Announcement Methods
- Google TTS via `gtts` library, streamed to Sonos

## Testing & Debugging

### View Available Devices
Check Sonos device discovery via the `[DEBUG]` output on startup, or inspect via the Sonos app.

### Debug Logging
Modern variants (especially JukeBoxSonosProd.py) include extensive `[DEBUG]` output to stderr showing:
- Device discovery process
- Input event details
- API call progress
- Error stack traces

### Common Issues
1. **Keypad not found**: Check `keyboard_device_name` or `keyboard_device_path` in `config_sonos.json`
2. **Sonos connection fails**: Verify IP address and that Sonos is powered on
3. **Music doesn't play**: Verify Spotify URI format and that Spotify is authorized in the Sonos app

