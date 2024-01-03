#!/usr/bin/python
from __future__ import print_function
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import subprocess, os, time, json, evdev, select, board, neopixel, pyttsx3, random

# Initialize NeoPixel LED
pixels = neopixel.NeoPixel(board.D10, 3)

# Initialize input devices
devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
devices = {dev.fd: dev for dev in devices}
current_playlist_index = 0
last_playlist_update = 0
cached_playlists = []
last_control_spotify_call = 0
cached_volume = 0
last_volume_update = 0
api_calls = 0
playlist_selection_delay = 2  # Delay in seconds

# Spotify API credentials and scope
scope = "user-modify-playback-state user-read-playback-state"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                                               client_secret="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                                               redirect_uri="http://localhost:8080",
                                               scope=scope,
                                               open_browser=False,
                                               cache_path='/home/pi/westinghouse/spotify-token-cache.txt'))

# Initialize Text-to-Speech engine
engine = pyttsx3.init()

def speak(text):
    print(f"speak: {text}")
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"Error in TTS: {e}")

def is_active_device_available():
    print("is_active_device_available")
    devices = get_spotify_data(lambda: sp.devices())
    return any(device['is_active'] for device in devices['devices']) if devices else False

def check_spotify_connection():
    print("check_spotify_connection")
    try:
        sp.me()  # Simple call to check if connected to Spotify
        return True
    except Exception as e:
        #speak(f"Spotify connection error: {e}")
        print(f"Spotify connection error: {e}")
        return False

def get_spotify_data(func):
    print(f"control_spotify: {func}")
    global api_calls
    try:
        response = func()
        if response is not None:
            api_calls = api_calls + 1
            return response
        else:
            raise Exception("Received None response from Spotify API")
    except Exception as e:
        #speak(f"Spotify API error: {e}")
        print(f"Spotify API error: {e}")
        return None

def control_spotify(action, **kwargs):
    print(f"control_spotify: {action}")
    global last_control_spotify_call
    global api_calls
    current_time = time.time()

    if check_spotify_connection():
        try:
            getattr(sp, action)(**kwargs)
            last_control_spotify_call = current_time  # Update the last call time after successful execution
            api_calls = api_calls + 1
        except Exception as e:
            #speak(f"Spotify control error: {e}")
            print(f"Spotify control error: {e}")

def update_playlists():
    print("update_playlists")
    global last_playlist_update, cached_playlists
    current_time = time.time()
    if current_time - last_playlist_update > 30:
        print("actually update_playlists")
        cached_playlists = get_spotify_data(lambda: [(playlist['name'], playlist['uri']) for playlist in sp.current_user_playlists()['items']])
        last_playlist_update = current_time
    return cached_playlists

def update_volume():
    global last_volume_update, cached_volume
    current_time = time.time()
    if current_time - last_volume_update > 30:
        print("actually update_volume")
        cached_volume = get_spotify_data(lambda: sp.current_playback()['device']['volume_percent'])
        last_volume_update = current_time
    return cached_volume
    
def get_active_devices():
    print("get_active_devices")
    devices = get_spotify_data(lambda: sp.devices())
    if devices:
        for device in devices['devices']:
            if device['name'] == 'Westinghouse Clock':
                return device['id']
    return None

def is_current_player():
    print("is_current_player")
    current_playback_info = get_spotify_data(lambda: sp.current_playback())
    if current_playback_info and current_playback_info['device']['name'] == 'Westinghouse Clock':
        return True
    return False

def update_led_status():
    print("update_led_status")
    global api_calls
    shuffle_state = get_spotify_data(lambda: sp.current_playback()['shuffle_state'])
    is_playing = get_spotify_data(lambda: sp.current_playback()['is_playing'])
    pixels.fill((10, 10, 10))
    if shuffle_state and is_playing:
        pixels.fill((10, 128, 10))
    elif not shuffle_state and is_playing:
        pixels.fill((128, 128, 10))
    pixels.show()
    print(f"Spotify API calls: {api_calls}")

def select_playlist():
    global current_playlist_index, last_control_spotify_call, cached_playlists
    selection_time = time.time()

    while True:
        readable, _, _ = select.select(devices.values(), [], [], playlist_selection_delay)
        if not readable:  # No input for the duration of the delay
            playlist_name, playlist_uri = cached_playlists[current_playlist_index]
            print(f"Starting playback: {playlist_name}")
            control_spotify('start_playback', context_uri=playlist_uri)
            break  # Exit the playlist selection loop

        for device in readable:
            for event in device.read():
                categorized_event = evdev.util.categorize(event)
                if isinstance(categorized_event, evdev.events.RelEvent) and device.fd == 7:
                    step = 1 if categorized_event.event.value > 0 else -1
                    current_playlist_index = (current_playlist_index + step) % len(cached_playlists)
                    playlist_name, playlist_uri = cached_playlists[current_playlist_index]
                    print(f"Selected playlist: {playlist_name}")
                    speak(playlist_name)
                    selection_time = time.time()

def handle_event(event, fd):
    print("handle_event")
    global current_playlist_index, last_control_spotify_call, cached_volume
    current_time = time.time()
    # Check if we are in the cooldown period
    if current_time - last_control_spotify_call < 0.5:
        return  # Ignore events during cooldown
    if isinstance(event, evdev.events.RelEvent):
        if fd == 5 and event.event.value == 1:
            control_spotify('next_track')
            print("Next Track")
        elif fd == 5 and event.event.value != 1:
            control_spotify('previous_track')
            print("Previous Track")
        elif fd == 6:
            volume_step = 5
            volume = update_volume()
            new_volume = min(100, max(0, volume + volume_step * event.event.value))
            control_spotify('volume', volume_percent=new_volume)
            cached_volume = new_volume
            print("Volume set to " + str(new_volume))
        elif fd == 7:  # playlist knob event
            if is_active_device_available():
                update_playlists()
                select_playlist()  # Enter the playlist selection loop
            else: 
                #speak("No active device found")
                print("No active device found")
    elif isinstance(event, evdev.events.KeyEvent):
        if event.keycode == "KEY_A" and event.keystate == event.key_up:
            shuffle_state = get_spotify_data(lambda: sp.current_playback()['shuffle_state'])
            new_shuffle_state = not shuffle_state
            control_spotify('shuffle', state=new_shuffle_state)
            speak("Shuffle " + ("On" if new_shuffle_state else "Off"))
            print("Set shuffle to " + str(new_shuffle_state))
        elif event.keycode == "KEY_B" and event.keystate == event.key_up:
            if is_current_player():
                is_playing = get_spotify_data(lambda: sp.current_playback()['is_playing'])
                if is_playing:
                    control_spotify('pause_playback')
                    speak("Paused")
                else:
                    control_spotify('start_playback')
                    speak("Playing")
                print("Playback toggled")
            else:
                device_id = get_active_devices()
                if device_id:
                    speak("Acquiring Spotify Stream")
                    control_spotify('transfer_playback', device_id=device_id, force_play=True)
                else:
                    print("Westinghouse Clock not found or not active")
                    speak("Westinghouse Clock not found or not active")
        elif event.keycode == "KEY_C" and event.keystate == event.key_up:
            playlists = update_playlists()
            if playlists:
                current_playlist_index = random.randint(0, len(playlists) - 1)
                playlist_name, playlist_uri = playlists[current_playlist_index]
                print(f"Selected random playlist: {playlist_name}")
                speak(playlist_name)
                control_spotify('start_playback', context_uri=playlist_uri)
            else:
                print("No playlists available.")
                speak("No playlists available.")
    update_led_status()

# Main loop
while True:
    r, w, x = select.select(devices, [], [])
    for fd in r:
        for event in devices[fd].read():
            event = evdev.util.categorize(event)
            handle_event(event, fd)

# ... End of script ...