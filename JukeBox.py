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
    scope='user-modify-playback-state,user-read-playback-state'
))

def get_devices():
    """Helper function to list all available Spotify devices"""
    devices = sp.devices()
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
    devices = sp.devices()
    for device in devices['devices']:
        if device['name'].lower() == device_name.lower():
            return device['id']
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
    
    if number_str not in music_map:
        print(f"Number {number} not mapped to any music")
        return
    
    mapping = music_map[number_str]
    uri = mapping['uri']
    title = mapping.get('title', f'Option {number}')
    
    device_id = find_device_id(config['sonos_room_name'])
    
    if not device_id:
        print("Could not find the specified Sonos device")
        return
    
    try:
        # Announce selection before playing
        announce_selection(number, title)
        
        # Small delay to let announcement finish
        if config['announce_selections']:
            time.sleep(0.5)
        
        # Start playback on the specified device
        sp.start_playback(device_id=device_id, context_uri=uri)
        print(f"✓ Playing '{title}' (option {number}) on {config['sonos_room_name']}")
    except Exception as e:
        print(f"Error playing music: {e}")

def find_keypad():
    """Find the USB numeric keypad device"""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        print(f"Found input device: {device.name}")
        # Most USB keypads will have 'keyboard' or 'keypad' in the name
        if 'keyboard' in device.name.lower() or 'keypad' in device.name.lower():
            return device
    # If no keyboard found, return the first device
    return devices[0] if devices else None

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
        
        # Check if we should process the buffered input (timeout expired)
        if input_buffer and (current_time - last_keypress_time > config['multi_digit_timeout']):
            number = parse_number_input(input_buffer)
            if number is not None:
                play_music(number)
            input_buffer = []
        
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
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
                
                if event.code in key_map:
                    key = key_map[event.code]
                    
                    # Handle Enter key as immediate trigger
                    if key == 'ENTER':
                        if input_buffer:
                            number = parse_number_input(input_buffer)
                            if number is not None:
                                play_music(number)
                            input_buffer = []
                    else:
                        # Add digit to buffer
                        input_buffer.append(key)
                        last_keypress_time = current_time
                        print(f"Input: {''.join(input_buffer)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nJukebox stopped. Goodbye!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()