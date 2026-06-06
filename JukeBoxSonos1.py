import evdev
from evdev import InputDevice, categorize, ecodes
import time
import json
import os
import requests
from pathlib import Path
import xml.etree.ElementTree as ET

# ============================================
# LOAD CONFIGURATION FILES
# ============================================

def load_config():
    """Load configuration from JSON files"""
    config_dir = Path(__file__).parent
    
    # Load main config
    with open(config_dir / 'config_sonos.json', 'r') as f:
        config = json.load(f)
    
    # Load music mappings
    with open(config_dir / 'music_mappings.json', 'r') as f:
        mappings = json.load(f)
    
    return config, mappings

# Load configs
config, music_map = load_config()

# ============================================
# SONOS CONTROL FUNCTIONS
# ============================================

def get_sonos_info(ip_address):
    """Get information about the Sonos device"""
    try:
        url = f"http://{ip_address}:1400/xml/device_description.xml"
        print(f"[DEBUG] Fetching Sonos info from {url}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            # Parse XML namespace
            ns = {'ns': 'urn:schemas-upnp-org:device-1-0'}
            room_name = root.find('.//ns:roomName', ns)
            model_name = root.find('.//ns:modelName', ns)
            
            if room_name is not None and model_name is not None:
                print(f"[DEBUG] Found Sonos: {room_name.text} ({model_name.text})")
                return room_name.text, model_name.text
        return None, None
    except Exception as e:
        print(f"[DEBUG] Error getting Sonos info: {e}")
        return None, None

def announce_selection(number, title):
    """Announce the selection using text-to-speech"""
    if config['announce_selections']:
        message = f"{title}"
        # Use espeak for text-to-speech
        os.system(f'espeak "{message}" 2>/dev/null')

def play_spotify_on_sonos(ip_address, spotify_uri, title):
    """Play a Spotify URI on Sonos using SOAP API"""
    
    # Sonos uses a specific format for Spotify URIs
    # spotify:album:ID becomes x-sonos-spotify:spotify:album:ID
    # We need to encode the URI properly
    if spotify_uri.startswith('spotify:album:'):
        album_id = spotify_uri.split(':')[-1]
        sonos_uri = f"x-sonos-spotify:spotify%3aalbum%3a{album_id}?sid=12&flags=8224&sn=7"
        metadata_type = "object.container.album.musicAlbum"
    elif spotify_uri.startswith('spotify:playlist:'):
        playlist_id = spotify_uri.split(':')[-1]
        sonos_uri = f"x-sonos-spotify:spotify%3aplaylist%3a{playlist_id}?sid=12&flags=8224&sn=7"
        metadata_type = "object.container.playlistContainer"
    elif spotify_uri.startswith('spotify:track:'):
        track_id = spotify_uri.split(':')[-1]
        sonos_uri = f"x-sonos-spotify:spotify%3atrack%3a{track_id}?sid=12&flags=8224&sn=7"
        metadata_type = "object.item.audioItem.musicTrack"
    else:
        print(f"[DEBUG] Unknown Spotify URI format: {spotify_uri}")
        return False
    
    # Build DIDL metadata
    metadata = f'''<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/" xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
<item id="00030020{sonos_uri}" restricted="true">
<dc:title>{title}</dc:title>
<upnp:class>{metadata_type}</upnp:class>
<desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">SA_RINCON2311_X_#Svc2311-0-Token</desc>
</item>
</DIDL-Lite>'''
    
    # SOAP request to set the URI
    soap_body_set = f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<s:Body>
<u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
<InstanceID>0</InstanceID>
<CurrentURI>{sonos_uri}</CurrentURI>
<CurrentURIMetaData>{metadata}</CurrentURIMetaData>
</u:SetAVTransportURI>
</s:Body>
</s:Envelope>'''
    
    # SOAP request to play
    soap_body_play = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<s:Body>
<u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
<InstanceID>0</InstanceID>
<Speed>1</Speed>
</u:Play>
</s:Body>
</s:Envelope>'''
    
    headers = {
        'Content-Type': 'text/xml; charset="utf-8"',
        'SOAPACTION': 'urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI'
    }
    
    try:
        # Set the URI
        print(f"[DEBUG] Setting URI on Sonos...")
        print(f"[DEBUG] Sonos URI: {sonos_uri}")
        url = f"http://{ip_address}:1400/MediaRenderer/AVTransport/Control"
        response = requests.post(url, data=soap_body_set, headers=headers, timeout=5)
        print(f"[DEBUG] SetURI Response: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[DEBUG] SetURI Response body: {response.text}")
            return False
        
        # Play
        headers['SOAPACTION'] = 'urn:schemas-upnp-org:service:AVTransport:1#Play'
        print(f"[DEBUG] Sending Play command...")
        response = requests.post(url, data=soap_body_play, headers=headers, timeout=5)
        print(f"[DEBUG] Play Response: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[DEBUG] Play Response body: {response.text}")
            return False
        
        return True
        
    except Exception as e:
        print(f"[DEBUG] Error controlling Sonos: {e}")
        return False

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
    
    try:
        # Announce selection before playing
        print(f"[DEBUG] Announcing selection...")
        announce_selection(number, title)
        
        # Small delay to let announcement finish
        if config['announce_selections']:
            time.sleep(0.5)
        
        print(f"[DEBUG] Attempting to play on Sonos...")
        success = play_spotify_on_sonos(config['sonos_ip_address'], uri, title)
        
        if success:
            print(f"✓ Playing '{title}' (option {number}) on {config['sonos_room_name']}")
        else:
            print(f"✗ Failed to play music on Sonos")
            
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
        if 'keyboard' in device.name.lower() or 'keypad' in device.name.lower():
            print(f"[DEBUG] Selected device: {device.name}")
            return device
    
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
    print("=" * 60)
    print("SONOS JUKEBOX (Direct Control)")
    print("=" * 60)
    
    # Check Sonos connection
    print(f"\n[DEBUG] Checking Sonos at {config['sonos_ip_address']}...")
    room_name, model_name = get_sonos_info(config['sonos_ip_address'])
    
    if room_name:
        print(f"✓ Connected to Sonos: {room_name} ({model_name})")
    else:
        print(f"✗ Could not connect to Sonos at {config['sonos_ip_address']}")
        print("\nPlease check:")
        print("  1. The IP address is correct in config_sonos.json")
        print("  2. The Sonos is powered on and connected to your network")
        print("  3. You can ping the Sonos IP address")
        return
    
    # Find the numeric keypad
    print("\n[DEBUG] Looking for numeric keypad...")
    keypad = find_keypad()
    
    if not keypad:
        print("✗ No input device found! Please connect a USB keyboard.")
        return
    
    print(f"✓ Using input device: {keypad.name}")
    print(f"✓ Target Sonos: {config['sonos_room_name']}")
    print(f"✓ Announcements: {'Enabled' if config['announce_selections'] else 'Disabled'}")
    print(f"✓ Multi-digit timeout: {config['multi_digit_timeout']} seconds")
    print("\n" + "=" * 60)
    print("Jukebox ready! Press numbers to play music.")
    print("For multi-digit numbers, press digits quickly then wait.")
    print("Press Ctrl+C to exit.")
    print("=" * 60 + "\n")
    
    # Buffer for multi-digit input
    input_buffer = []
    last_keypress_time = 0
    
    # Listen for keypad input
    for event in keypad.read_loop():
        current_time = time.time()
        
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