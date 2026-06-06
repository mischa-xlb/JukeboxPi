import spotipy
from spotipy.oauth2 import SpotifyOAuth
import evdev
from evdev import InputDevice, categorize, ecodes
import time
import json
import os
from pathlib import Path

# ============================================
# LOAD CONFIGURATION FILES
# ============================================

def load_config():
    """Load configuration from JSON files"""
    config_dir = Path(__file__).parent
    
    # Load main config
    with open(config_dir / 'config.json', 'r') as f:
        config = json.load(f)
    
    # Load music mappings
    with open(config_dir / 'music_mappings.json', 'r') as f:
        mappings = json.load(f)
    
    return config, mappings

# Load configs
config, music_map = load_config()

# ============================================
# MAIN CODE
# ============================================

# Initialize Spotify with the necessary scope for playback control
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=config['spotify']['client_id'],
    client_secret=config['spotify']['client_secret'],
    redirect_uri=config['spotify']['redirect_uri'],
    scope='user-modify-playback-state,user-read-playback-state',
    cache_path='.spotify_cache',
    open_browser=False
))

def get_devices():
    """Helper function to list all available Spotify devices"""
    print("[DEBUG] Fetching Spotify devices...")
    devices = sp.devices()
    print(f"[DEBUG] Found {len(devices['devices'])} device(s)")
    print("\n=== Available Spotify Devices ===")
    for device in devices['devices']:
        print(f"Name: {device['name']}")
        print(f"  Type: {device['type']}")
        print(f"  ID: {device['id']}")
        print(f"  Active: {device['is_active']}")
        print()
    return devices

def find_device_id(device_name):
    """Find the device ID for the specified Sonos room"""
    print(f"[DEBUG] Looking for device: '{device_name}'")
    devices = sp.devices()
    for device in devices['devices']:
        print(f"[DEBUG] Checking device: '{device['name']}'")
        if device['name'].lower() == device_name.lower():
            print(f"[DEBUG] Match found! Device ID: {device['id']}")
            return device['id']
    print(f"[DEBUG] No match found for '{device_name}'")
    print(f"Warning: Device '{device_name}' not found!")
    print("Available devices:")
    for device in devices['devices']:
        print(f"  - {device['name']}")
    return None

def announce_selection(number, title):
    """Announce the selection using text-to-speech"""
    if config['announce_selections']:
        message = f"Option {number} selected"
        if title:
            message = f"{title}"
        
        # Use espeak for text-to-speech (install with: sudo apt-get install espeak)
        os.system(f'espeak "{message}" 2>/dev/null')

def play_music(number):
    """Play the album/playlist associated with the pressed number"""
    number_str = str(number)
    
    print(f"[DEBUG] play_music called with number: {number}")
    print(f"[DEBUG] Available mappings: {list(music_map.keys())}")
    
    if number_str not in music_map:
        print(f"[DEBUG] Number {number} not found in music_map")
        print(f"Number {number} not mapped to any music")
        return
    
    mapping = music_map[number_str]
    uri = mapping['uri']
    title = mapping.get('title', f'Option {number}')
    
    print(f"[DEBUG] Found mapping - Title: '{title}', URI: '{uri}'")
    
    device_id = find_device_id(config['sonos_room_name'])
    
    if not device_id:
        print("[DEBUG] Device ID is None, cannot play music")
        print("Could not find the specified Sonos device")
        return
    
    try:
        print(f"[DEBUG] Attempting to announce selection...")
        # Announce selection before playing
        announce_selection(number, title)
        
        # Small delay to let announcement finish
        if config['announce_selections']:
            time.sleep(0.5)
        
        print(f"[DEBUG] Attempting to start playback...")
        print(f"[DEBUG] Device ID: {device_id}")
        print(f"[DEBUG] URI: {uri}")
        
        # Start playback on the specified device
        sp.start_playback(device_id=device_id, context_uri=uri)
        print(f"✓ Playing '{title}' (option {number}) on {config['sonos_room_name']}")
    except Exception as e:
        print(f"[DEBUG] Exception occurred: {type(e).__name__}")
        print(f"[DEBUG] Exception details: {str(e)}")
        print(f"Error playing music: {e}")

def find_keypad():
    """Find the USB numeric keypad device"""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    print(f"[DEBUG] Found {len(devices)} input device(s):")
    for device in devices:
        print(f"[DEBUG]   - {device.name} (path: {device.path})")
    
    # If a specific device path is configured, use that
    if 'keyboard_device_path' in config and config['keyboard_device_path']:
        device_path = config['keyboard_device_path']
        print(f"[DEBUG] Using configured device path: {device_path}")
        try:
            selected_device = evdev.InputDevice(device_path)
            print(f"[DEBUG] Successfully opened: {selected_device.name}")
            return selected_device
        except Exception as e:
            print(f"[DEBUG] Error opening configured device: {e}")
            print(f"[DEBUG] Falling back to auto-detection")
    
    # Auto-detect keyboard
    for device in devices:
        # Most USB keypads will have 'keyboard' or 'keypad' in the name
        if 'keyboard' in device.name.lower() or 'keypad' in device.name.lower():
            print(f"[DEBUG] Selected device: {device.name}")
            return device
    
    # If no keyboard found, return the first device
    if devices:
        print(f"[DEBUG] No keyboard/keypad found, using first device: {devices[0].name}")
        return devices[0]
    return None

def parse_number_input(input_buffer):
    """Convert multi-digit input buffer to number"""
    if not input_buffer:
        return None
    return int(''.join(input_buffer))

def main():
    print("=== Sonos Jukebox Starting ===")
    
    # Uncomment the line below to see all available Spotify devices
    # get_devices()
    
    # Find the numeric keypad
    print("\nLooking for numeric keypad...")
    keypad = find_keypad()
    
    if not keypad:
        print("No input device found! Please connect a USB keypad.")
        return
    
    print(f"Using input device: {keypad.name}")
    print(f"Target room: {config['sonos_room_name']}")
    print(f"Announcements: {'Enabled' if config['announce_selections'] else 'Disabled'}")
    print(f"Multi-digit timeout: {config['multi_digit_timeout']} seconds")
    print("\nJukebox ready! Press numbers to play music.")
    print("For multi-digit numbers, press digits quickly then wait.")
    print("Press Ctrl+C to exit.\n")
    
    # Buffer for multi-digit input
    input_buffer = []
    last_keypress_time = 0
    
    # Listen for keypad input
    for event in keypad.read_loop():
        current_time = time.time()
        
        # Debug: Show all events (can be commented out once working)
        if event.type == ecodes.EV_KEY:
            print(f"[DEBUG] Raw event - Code: {event.code}, Type: {event.type}, Value: {event.value}")
        
        # Check if we should process the buffered input (timeout expired)
        if input_buffer and (current_time - last_keypress_time > config['multi_digit_timeout']):
            print(f"[DEBUG] Timeout reached, processing buffer: {input_buffer}")
            number = parse_number_input(input_buffer)
            if number is not None:
                print(f"[DEBUG] Parsed number: {number}")
                play_music(number)
            input_buffer = []
        
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            print(f"[DEBUG] Key event - Keystate: {key_event.keystate}, Scancode: {key_event.scancode}")
            
            if key_event.keystate == 1:  # Key down event
                # Map keypad numbers to actual numbers
                key_map = {
                    ecodes.KEY_KP0: '0', ecodes.KEY_0: '0',
                    ecodes.KEY_KP1: '1', ecodes.KEY_1: '1',
                    ecodes.KEY_KP2: '2', ecodes.KEY_2: '2',
                    ecodes.KEY_KP3: '3', ecodes.KEY_3: '3',
                    ecodes.KEY_KP4: '4', ecodes.KEY_4: '4',
                    ecodes.KEY_KP5: '5', ecodes.KEY_5: '5',
                    ecodes.KEY_KP6: '6', ecodes.KEY_6: '6',
                    ecodes.KEY_KP7: '7', ecodes.KEY_7: '7',
                    ecodes.KEY_KP8: '8', ecodes.KEY_8: '8',
                    ecodes.KEY_KP9: '9', ecodes.KEY_9: '9',
                    ecodes.KEY_KPENTER: 'ENTER', ecodes.KEY_ENTER: 'ENTER',
                }
                
                print(f"[DEBUG] Checking if code {event.code} is in key_map...")
                
                if event.code in key_map:
                    key = key_map[event.code]
                    print(f"[DEBUG] Mapped to key: '{key}'")
                    
                    # Handle Enter key as immediate trigger
                    if key == 'ENTER':
                        print(f"[DEBUG] Enter pressed, current buffer: {input_buffer}")
                        if input_buffer:
                            number = parse_number_input(input_buffer)
                            if number is not None:
                                print(f"[DEBUG] Triggering playback for number: {number}")
                                play_music(number)
                            input_buffer = []
                    else:
                        # Add digit to buffer
                        input_buffer.append(key)
                        last_keypress_time = current_time
                        print(f"[DEBUG] Added to buffer. Current input: {''.join(input_buffer)}")
                        print(f"Input: {''.join(input_buffer)}")
                else:
                    print(f"[DEBUG] Key code {event.code} not in key_map, ignoring")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nJukebox stopped. Goodbye!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()