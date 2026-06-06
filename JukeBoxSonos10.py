import evdev
from evdev import InputDevice, categorize, ecodes
import time
import json
import os
from pathlib import Path
import soco
from soco.music_services import MusicService

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

def get_sonos_device(ip_address):
    """Get the Sonos device object"""
    try:
        print(f"[DEBUG] Connecting to Sonos at {ip_address}...")
        device = soco.SoCo(ip_address)
        
        # Test connection by getting speaker info
        info = device.get_speaker_info()
        print(f"[DEBUG] Connected to: {info['zone_name']} ({info['model_name']})")
        
        return device, info['zone_name']
    except Exception as e:
        print(f"[DEBUG] Error connecting to Sonos: {e}")
        return None, None

def announce_selection(device, number, title):
    """Announce the selection using text-to-speech through Sonos"""
    print(f"[DEBUG] announce_selection called - Number: {number}, Title: {title}")
    print(f"[DEBUG] Announcements enabled: {config['announce_selections']}")
    
    if config['announce_selections']:
        message = f"You have selected number {number}. {title}"
        print(f"[DEBUG] Speaking via Sonos: '{message}'")
        
        try:
            # Save current volume
            original_volume = device.volume
            print(f"[DEBUG] Current volume: {original_volume}")
            
            # Optionally set a specific volume for announcements
            if 'announcement_volume' in config and config['announcement_volume']:
                device.volume = config['announcement_volume']
                print(f"[DEBUG] Set announcement volume to: {config['announcement_volume']}")
            
            # Use Google Translate TTS (works without API keys)
            from gtts import gTTS
            import tempfile
            
            # Create temporary MP3 file
            tts = gTTS(text=message, lang='en', slow=False)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_file = fp.name
                tts.save(temp_file)
            
            print(f"[DEBUG] TTS file created: {temp_file}")
            
            # Play the TTS file on Sonos
            file_uri = f"file://{temp_file}"
            device.play_uri(file_uri)
            
            # Wait for announcement to finish
            print(f"[DEBUG] Waiting for announcement to complete...")
            time.sleep(3)  # Adjust based on message length
            
            # Restore original volume
            device.volume = original_volume
            print(f"[DEBUG] Restored volume to: {original_volume}")
            
            # Clean up temp file
            os.unlink(temp_file)
            print(f"[DEBUG] Announcement complete")
            
        except ImportError:
            print("[WARNING] gTTS not installed. Install with: pip install gTTS")
            print("[INFO] Falling back to no announcement")
        except Exception as e:
            print(f"[WARNING] Could not play announcement: {e}")
            # Restore volume if something went wrong
            try:
                device.volume = original_volume
            except:
                pass

def play_spotify_on_sonos(device, spotify_uri, title):
    """Play a Spotify URI on Sonos using SoCo sharelink method"""
    
    try:
        print(f"[DEBUG] Spotify URI: {spotify_uri}")
        
        # Convert Spotify URI to HTTP sharelink format
        # spotify:album:ID -> https://open.spotify.com/album/ID
        # spotify:playlist:ID -> https://open.spotify.com/playlist/ID
        # spotify:track:ID -> https://open.spotify.com/track/ID
        
        if spotify_uri.startswith('spotify:album:'):
            album_id = spotify_uri.split(':')[-1]
            sharelink = f"https://open.spotify.com/album/{album_id}"
            print(f"[DEBUG] Converted to sharelink: {sharelink}")
        elif spotify_uri.startswith('spotify:playlist:'):
            playlist_id = spotify_uri.split(':')[-1]
            sharelink = f"https://open.spotify.com/playlist/{playlist_id}"
            print(f"[DEBUG] Converted to sharelink: {sharelink}")
        elif spotify_uri.startswith('spotify:track:'):
            track_id = spotify_uri.split(':')[-1]
            sharelink = f"https://open.spotify.com/track/{track_id}"
            print(f"[DEBUG] Converted to sharelink: {sharelink}")
        else:
            print(f"[DEBUG] Unknown Spotify URI format: {spotify_uri}")
            return False
        
        # Use SoCo's sharelink functionality
        print(f"[DEBUG] Adding sharelink to queue...")
        from soco.plugins.sharelink import ShareLinkPlugin
        
        # Get the sharelink plugin
        sharelink_plugin = ShareLinkPlugin(device)
        
        # Add the sharelink to the queue
        position = sharelink_plugin.add_share_link_to_queue(sharelink)
        print(f"[DEBUG] Added to queue at position: {position}")
        
        # Clear queue and add fresh
        print(f"[DEBUG] Clearing queue and playing...")
        device.clear_queue()
        position = sharelink_plugin.add_share_link_to_queue(sharelink)
        
        # Play from the queue
        device.play_from_queue(position - 1)  # Position is 1-indexed
        print(f"[DEBUG] Playback started successfully")
        
        return True
        
    except ImportError as e:
        print(f"[DEBUG] ShareLinkPlugin not available: {e}")
        print(f"[DEBUG] You may need to update SoCo: pip install --upgrade soco")
        return False
    except Exception as e:
        print(f"[DEBUG] Error playing on Sonos: {e}")
        print(f"[DEBUG] Exception type: {type(e).__name__}")
        return False

def play_music(number):
    """Play the album/playlist associated with the pressed number"""
    number_str = str(number)
    
    print(f"\n[DEBUG] play_music called with number: {number}")
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
        announce_selection(sonos_device, number, title)
        
        # Small delay to let announcement finish
        if config['announce_selections']:
            time.sleep(0.5)
        
        print(f"[DEBUG] Attempting to play on Sonos...")
        success = play_spotify_on_sonos(sonos_device, uri, title)
        
        if success:
            print(f"✓ Playing '{title}' (option {number}) on {sonos_room_name}")
        else:
            print(f"✗ Failed to play music on Sonos")
            print(f"\nTroubleshooting:")
            print(f"  1. Make sure Spotify is authorized in the Sonos S1 app")
            print(f"  2. Try playing this album manually in Sonos app first")
            print(f"  3. The Spotify URI might be invalid: {uri}")
            
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
    global sonos_device, sonos_room_name
    
    print("=" * 60)
    print("SONOS JUKEBOX (SoCo Library)")
    print("=" * 60)
    
    # Connect to Sonos
    print(f"\n[1/2] Connecting to Sonos at {config['sonos_ip_address']}...")
    sonos_device, sonos_room_name = get_sonos_device(config['sonos_ip_address'])
    
    if not sonos_device:
        print(f"✗ Could not connect to Sonos at {config['sonos_ip_address']}")
        print("\nPlease check:")
        print("  1. The IP address is correct in config_sonos.json")
        print("  2. The Sonos is powered on and connected to your network")
        print("  3. You can ping the Sonos IP address")
        print("\nTo find your Sonos IP:")
        print("  Sonos S1 app → Settings → System → About My System")
        return
    
    print(f"✓ Connected to Sonos: {sonos_room_name}")
    
    # Find the numeric keypad
    print(f"\n[2/2] Looking for keyboard...")
    keypad = find_keypad()
    
    if not keypad:
        print("✗ No input device found! Please connect a USB keyboard.")
        return
    
    print(f"✓ Using input device: {keypad.name}")
    
    print("\n" + "=" * 60)
    print(f"✓ Target Sonos: {sonos_room_name}")
    print(f"✓ Announcements: {'Enabled' if config['announce_selections'] else 'Disabled'}")
    print(f"✓ Timeout: {config['multi_digit_timeout']} seconds")
    print("=" * 60)
    print("\nJukebox ready! Press numbers to play music.")
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
                    ecodes.KEY_P: 'PAUSE',
                    ecodes.KEY_G: 'PLAY',
                }
                
                if event.code in key_map:
                    key = key_map[event.code]
                    
                    # Handle special control keys
                    if key == 'PAUSE':
                        print("[CONTROL] Pausing playback...")
                        try:
                            sonos_device.pause()
                            print("✓ Playback paused")
                        except Exception as e:
                            print(f"✗ Error pausing: {e}")
                        continue
                    
                    elif key == 'PLAY':
                        print("[CONTROL] Resuming playback...")
                        try:
                            sonos_device.play()
                            print("✓ Playback resumed")
                        except Exception as e:
                            print(f"✗ Error resuming: {e}")
                        continue
                    
                    # Handle Enter key as immediate trigger
                    elif key == 'ENTER':
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