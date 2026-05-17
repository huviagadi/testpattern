# Pi Test Pattern Generator

Test signal generator for Raspberry Pi with composite/HDMI output and SPI touchscreen control.

Outputs classic test patterns (SMPTE, PM5544, color bars, etc.) with an optional 2D rotating artist name overlay for luma keying in video synthesis setups.

## Hardware

- Raspberry Pi 3B+ (or similar)
- PiScreen 3.5" SPI touchscreen (480x320, ILI9486 + ADS7846 touch)
- Composite video output or HDMI, both outputs active for easy testing of displays

## Patterns

- **SMPTE** — Standard SMPTE color bars
- **Grid** — Alignment grid
- **OldTV** — Classic TV test card style
- **PM5544** — Philips PM5544 pattern
- **Bars** — Simple color bars
- **Vignette** — Vignette gradient

## Features

- Touch UI on SPI screen to select patterns
- Artist name overlay (3D rotating text) on composite/HDMI output
- Toggle patterns and overlay on/off via touch
- Auto-starts on boot via systemd

## Installation

### 1. Flash SD Card

1. Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Insert your SD card (8GB+ recommended)
3. Open Raspberry Pi Imager and select:
   - **Device:** Raspberry Pi 3
   - **OS:** Raspberry Pi OS Lite (64-bit) — under "Raspberry Pi OS (other)"
   - **Storage:** Your SD card
4. Click the gear icon (⚙) or "Edit Settings" to configure:
   - **Hostname:** `testpattern`
   - **Username:** `admin`
   - **Password:** `admin`
   - **WiFi:** Your network SSID and password
   - **Enable SSH:** Yes (use password authentication)
   - **Locale:** Your timezone
5. Click "Write" and wait for it to complete

### 2. Add Display Config

Before ejecting the SD card, open the `bootfs` volume and edit `config.txt` (on macOS/Linux) or access it after first boot via SSH at `/boot/firmware/config.txt`.

Add these lines to the end of the file:

```
dtoverlay=vc4-kms-v3d,composite=1
gpu_mem=256
max_framebuffers=2
enable_tvout=1
sdtv_mode=0
sdtv_aspect=1
dtoverlay=disable-bt
dtoverlay=piscreen,speed=16000000,rotate=270
dtparam=spi=on
```

### 3. Run Setup Script

From your Mac/Linux machine:

```bash
./setup_pi.sh admin@testpattern.local
```

This copies the Python files and installs systemd services.

### 4. Reboot

```bash
ssh admin@testpattern.local 'sudo reboot'
```

The pattern generator and touch UI will start automatically.

## Usage

- **Tap a pattern button** to activate it
- **Tap the active pattern** to toggle it off
- **Tap < or >** to cycle through artist names
- **Tap the artist display area** to toggle the overlay on/off

The artist overlay appears on composite/HDMI output as white text on black — useful for luma keying.

## Files

```
testpattern/
├── README.md
├── pattern_gen.py      # Main pattern generator (runs on fb0)
├── touch_ui.py         # Touch UI (runs on fb1/SPI screen)
├── artists.txt         # List of artist names for overlay
├── setup_pi.sh         # Deployment script
└── config/
    ├── config.txt.additions   # Boot config for Pi
    ├── pattern_gen.service    # systemd service
    └── touch_ui.service       # systemd service
```

## Customization

### Artist Names

Edit `artists.txt` on the Pi (`/home/admin/artists.txt`) to set your own artist names for the overlay. One name per line:

```
YOUR_NAME
CREW_NAME
ANOTHER_ARTIST
```

After editing, restart the service:
```bash
sudo systemctl restart pattern_gen.service
```

### Adding Patterns

Edit `pattern_gen.py` to add new test patterns. Each pattern is a function that draws to the framebuffer. See existing patterns like `draw_smpte()` for examples.
I may add an example of drawing an image to the framebuffer, so real-life test card examples could be added as static images.

### Display Settings

Edit `config/config.txt.additions` before deploying to change:
- `sdtv_mode` — 0=NTSC, 2=PAL
- `sdtv_aspect` — 1=4:3, 3=16:9
- `rotate` — SPI screen rotation (0, 90, 180, 270)

## License

MIT
