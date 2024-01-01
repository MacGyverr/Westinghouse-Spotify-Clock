# Westinghouse H816L5 Clock Spotify Conversion

## Overview
I replicated a Westinghouse H816L5 clock in TinkerCAD to design parts for mounting a Raspberry Pi and a modern clock, transforming it into a Spotify speaker.

- TinkerCAD Model: [Westinghouse H816L5 Clock Conversion - WIP](https://www.tinkercad.com/things/fx6p13KGLE0-westinghouse-h816l5-clock-conversion-wip)
  
The project involved some modifications to the original structure, including grinding down the internal lip. It uses Raspotify and Spotipy, controlled by a Python script. It features three rotary encoders for track control, power/play/pause/volume, and playlist navigation.

## Hardware Requirements
- Raspberry Pi
- MIC ULTRA+ (as an amplifier)
- 3 Rotary Encoders

## Software
- Raspotify
- Spotipy

## Installation and Setup
1. **Prepare the Raspberry Pi:**
    ```bash
    sudo apt-get -y update
    sudo apt-get -y upgrade
    sudo apt-get -y install git pip espeak
    ```

2. **Configure Rotary Encoders in `config.txt`:**
    ```bash
    sudo nano /boot/config.txt
    # Add the following lines
    dtoverlay=rotary-encoder,pin_a=16,pin_b=12,relative_axis=1
    dtoverlay=gpio-key,gpio=26,keycode=30,label="A"
    dtoverlay=rotary-encoder,pin_a=5,pin_b=6,relative_axis=1
    dtoverlay=gpio-key,gpio=13,keycode=48,label="B"
    dtoverlay=rotary-encoder,pin_a=22,pin_b=27,relative_axis=1
    dtoverlay=gpio-key,gpio=17,keycode=46,label="C"
    ```
    After editing, reboot and test with `evtest`.

3. **Install Audio Hat Drivers for MIC ULTRA+:**
    ```bash
    git clone https://github.com/RASPIAUDIO/ultra2
    cd ultra2
    sudo ./install.sh
    sudo reboot
    ```

4. **Install and Configure Raspotify:**
    - Follow the guide at [Raspotify](https://dtcooper.github.io/raspotify/)
    - Edit `/etc/raspotify/conf` as per the provided `conf` file.
    - Restart the service and set volumes using `alsamixer`.

5. **Install Spotipy and Additional Packages:**
    ```bash
    sudo pip install spotipy
    sudo pip install adafruit-circuitpython-neopixel
    sudo pip3 install pyttsx3
    ```

6. **Setup Python Script for Control:**
    ```bash
    mkdir westinghouse
    cd westinghouse/
    nano monitor_input.py
    # Follow instructions in "monitor_input.py" file
    chmod +x monitor_input.py
    ```

7. **Configure Spotify API Credentials:**
    ```bash
    export SPOTIPY_CLIENT_ID='xxxxxxxxxxxxxxxxxxxxxxxx'
    export SPOTIPY_CLIENT_SECRET='xxxxxxxxxxxxxxxxxxxx'
    export SPOTIPY_REDIRECT_URI='http://localhost:8080/callback'
    ```

8. **Setup Python Script as a Service:**
    ```bash
    sudo nano /etc/systemd/system/monitor_input.py.service
    # Follow instructions in "monitor_input.py.service" file
    sudo systemctl enable monitor_input.py
    sudo systemctl daemon-reload
    sudo systemctl start monitor_input.py
    systemctl | grep running
    ```

9. **Automatic Reboot Setup:**
    ```bash
    sudo crontab -e
    # Add this line for nightly reboot
    0 2 * * * /sbin/shutdown -r now
    ```

## Additional Notes
- Wiring diagram will be added soon.
- TinkerCAD files allow for printing the complete clock and even creating molds for a new lens.
- The system is set to "Overlay" mode and reboots nightly for stability.
