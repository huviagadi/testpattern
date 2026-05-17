#!/usr/bin/env python3
"""
Test Pattern Generator for Pi Test Signal Generator
Writes directly to fb0 (HDMI + composite)
Listens for commands via Unix socket from touch UI
Supports 3D rotating artist name overlay
"""

import os
import sys
import socket
import threading
import struct
import mmap
import time
import math

# Constants
FB_DEVICE = "/dev/fb0"
SOCKET_PATH = "/tmp/pattern_gen.sock"
ARTISTS_FILE = "/home/admin/artists.txt"

DEFAULT_ARTISTS = [
    "YOUR_NAME",
    "ARTIST_2",
    "VJ_CREW",
    "VISUALS",
]

# 5x7 pixel font for 3D text
FONT_5X7 = {
    'A': [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    'B': [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
    'C': [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
    'D': [0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E],
    'E': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
    'F': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    'G': [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0E],
    'H': [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    'I': [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E],
    'J': [0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C],
    'K': [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
    'L': [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    'M': [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
    'N': [0x11, 0x11, 0x19, 0x15, 0x13, 0x11, 0x11],
    'O': [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    'P': [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    'Q': [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D],
    'R': [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    'S': [0x0E, 0x11, 0x10, 0x0E, 0x01, 0x11, 0x0E],
    'T': [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    'U': [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    'V': [0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04],
    'W': [0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11],
    'X': [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    'Y': [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
    'Z': [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    '0': [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
    '1': [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    '2': [0x0E, 0x11, 0x01, 0x0E, 0x10, 0x10, 0x1F],
    '3': [0x0E, 0x11, 0x01, 0x06, 0x01, 0x11, 0x0E],
    '4': [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    '5': [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    '6': [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    '7': [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    '8': [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    '9': [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    ' ': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
    '_': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F],
    '-': [0x00, 0x00, 0x00, 0x0E, 0x00, 0x00, 0x00],
}

def get_fb_info(fb_path):
    fb_name = os.path.basename(fb_path)
    size_path = f"/sys/class/graphics/{fb_name}/virtual_size"
    bpp_path = f"/sys/class/graphics/{fb_name}/bits_per_pixel"
    with open(size_path) as f:
        w, h = map(int, f.read().strip().split(','))
    with open(bpp_path) as f:
        bpp = int(f.read().strip())
    return w, h, bpp

def rgb_to_rgb565(r, g, b):
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)

def rgb565_bytes(r, g, b):
    val = rgb_to_rgb565(r, g, b)
    return struct.pack('<H', val)

SMPTE_COLORS = [
    (191, 191, 191), (191, 191, 0), (0, 191, 191), (0, 191, 0),
    (191, 0, 191), (191, 0, 0), (0, 0, 191),
]

PM5544_COLORS = [
    (255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
    (255, 0, 255), (255, 0, 0), (0, 0, 255),
]


class PatternGenerator:
    def __init__(self):
        self.running = True
        self.current_pattern = "smpte"
        self.pattern_changed = threading.Event()
        self.animation_frame = 0
        self.pattern_on = True

        # Artist overlay
        self.artists = self.load_artists()
        self.artist_idx = 0
        self.artist_overlay = False
        self.text_cache = None  # Cached rendered text (list of (x, y) pixel positions)
        self.text_cache_artist = None  # Which artist is cached

        # Disable console on fb0
        try:
            os.system("echo 0 > /sys/class/vtconsole/vtcon1/bind 2>/dev/null")
        except:
            pass

        # Get framebuffer info
        self.width, self.height, self.bpp = get_fb_info(FB_DEVICE)
        self.stride = self.width * (self.bpp // 8)
        self.fb_size = self.stride * self.height

        print(f"Framebuffer: {self.width}x{self.height} @ {self.bpp}bpp", flush=True)

        # Open and mmap framebuffer
        self.fb_fd = os.open(FB_DEVICE, os.O_RDWR)
        self.fb = mmap.mmap(self.fb_fd, self.fb_size, mmap.MAP_SHARED, mmap.PROT_WRITE | mmap.PROT_READ)

        # Create buffers for drawing
        self.buffer = bytearray(self.fb_size)
        self.pattern_cache = bytearray(self.fb_size)  # Cached pattern
        self.pattern_dirty = True  # Need to redraw pattern

        # Pattern registry
        self.patterns = {
            "smpte": self.draw_smpte,
            "grid": self.draw_grid,
            "oldtv": self.draw_oldtv,
            "pm5544": self.draw_pm5544,
            "bars": self.draw_luma_bars,
            "vignette": self.draw_vignette,
            "off": lambda: self.fill_screen(0, 0, 0),
        }

        print(f"Artists: {self.artists}", flush=True)

    def load_artists(self):
        try:
            with open(ARTISTS_FILE, 'r') as f:
                artists = [line.strip() for line in f if line.strip()]
                return artists if artists else DEFAULT_ARTISTS[:]
        except:
            return DEFAULT_ARTISTS[:]

    def set_pixel(self, x, y, r, g, b):
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = y * self.stride + x * 2
            val = rgb_to_rgb565(r, g, b)
            self.buffer[offset] = val & 0xFF
            self.buffer[offset + 1] = (val >> 8) & 0xFF

    def fill_rect(self, x, y, w, h, r, g, b):
        pixel = rgb565_bytes(r, g, b)
        for py in range(y, min(y + h, self.height)):
            offset = py * self.stride + x * 2
            for px in range(w):
                if x + px < self.width:
                    self.buffer[offset + px * 2] = pixel[0]
                    self.buffer[offset + px * 2 + 1] = pixel[1]

    def fill_screen(self, r, g, b):
        pixel = rgb565_bytes(r, g, b)
        for i in range(0, self.fb_size, 2):
            self.buffer[i] = pixel[0]
            self.buffer[i + 1] = pixel[1]

    def flip(self):
        self.fb.seek(0)
        self.fb.write(self.buffer)

    def draw_smpte(self):
        bar_width = self.width // 7
        top_height = int(self.height * 0.67)
        mid_height = int(self.height * 0.08)

        for i, color in enumerate(SMPTE_COLORS):
            x = i * bar_width
            w = bar_width if i < 6 else self.width - x
            self.fill_rect(x, 0, w, top_height, *color)

        mid_y = top_height
        reverse_colors = [(0, 0, 191), (19, 19, 19), (191, 0, 191), (19, 19, 19),
                          (0, 191, 191), (19, 19, 19), (191, 191, 191)]
        for i, color in enumerate(reverse_colors):
            x = i * bar_width
            w = bar_width if i < 6 else self.width - x
            self.fill_rect(x, mid_y, w, mid_height, *color)

        bottom_y = mid_y + mid_height
        bottom_height = self.height - bottom_y
        pluge_width = self.width // 4
        pluge_colors = [(0, 0, 0), (16, 16, 16), (32, 32, 32)]
        pluge_bar = pluge_width // 3
        for i, color in enumerate(pluge_colors):
            self.fill_rect(i * pluge_bar, bottom_y, pluge_bar, bottom_height, *color)

        self.fill_rect(pluge_width, bottom_y, pluge_width, bottom_height, 255, 255, 255)

        ramp_start = pluge_width * 2
        ramp_width = self.width - ramp_start
        for x in range(ramp_width):
            gray = int((x / ramp_width) * 255)
            for y in range(bottom_y, self.height):
                self.set_pixel(ramp_start + x, y, gray, gray, gray)

    def draw_grid(self):
        self.fill_screen(0, 0, 0)
        spacing = 40

        for x in range(0, self.width, spacing):
            color = (255, 255, 255) if x % (spacing * 4) == 0 else (128, 128, 128)
            for y in range(self.height):
                self.set_pixel(x, y, *color)

        for y in range(0, self.height, spacing):
            color = (255, 255, 255) if y % (spacing * 4) == 0 else (128, 128, 128)
            for x in range(self.width):
                self.set_pixel(x, y, *color)

        cx, cy = self.width // 2, self.height // 2
        for i in range(-20, 21):
            self.set_pixel(cx + i, cy, 255, 0, 0)
            self.set_pixel(cx, cy + i, 255, 0, 0)

        marker = 30
        for corner_x, corner_y in [(0, 0), (self.width - marker, 0),
                                    (0, self.height - marker),
                                    (self.width - marker, self.height - marker)]:
            self.fill_rect(corner_x, corner_y, marker, marker, 255, 255, 255)

    def draw_oldtv(self):
        self.fill_screen(0, 0, 0)
        cx, cy = self.width // 2, self.height // 2
        radius = min(cx, cy) - 20

        # Circle
        for angle in range(360):
            rad = math.radians(angle)
            px = int(cx + radius * math.cos(rad))
            py = int(cy + radius * math.sin(rad))
            for t in range(-1, 2):
                self.set_pixel(px + t, py, 255, 255, 255)
                self.set_pixel(px, py + t, 255, 255, 255)

        # Crosshairs
        for i in range(-radius, radius + 1):
            self.set_pixel(cx + i, cy, 255, 255, 255)
            self.set_pixel(cx, cy + i, 255, 255, 255)

        # Resolution wedges at top/bottom
        for y in range(30):
            bars = 3 + y // 4
            bar_w = max(1, self.width // (bars * 2))
            for x in range(self.width):
                if (x // bar_w) % 2 == 0:
                    self.set_pixel(x, y, 255, 255, 255)
                    self.set_pixel(x, self.height - 1 - y, 255, 255, 255)

    def draw_pm5544(self):
        self.fill_screen(0, 0, 0)
        bar_w = self.width // 7
        bar_h = self.height // 4

        for i, color in enumerate(PM5544_COLORS):
            x = i * bar_w
            w = bar_w if i < 6 else self.width - x
            self.fill_rect(x, 0, w, bar_h, *color)

        cx, cy = self.width // 2, self.height // 2
        radius = min(self.width, self.height) // 3

        for y in range(cy - radius, cy + radius):
            for x in range(cx - radius, cx + radius):
                if (x - cx)**2 + (y - cy)**2 <= radius**2:
                    self.set_pixel(x, y, 64, 64, 64)

        for angle in range(360):
            rad = math.radians(angle)
            px = int(cx + radius * math.cos(rad))
            py = int(cy + radius * math.sin(rad))
            self.set_pixel(px, py, 255, 255, 255)

        for i in range(-15, 16):
            self.set_pixel(cx + i, cy, 255, 255, 255)
            self.set_pixel(cx, cy + i, 255, 255, 255)

        bottom_y = self.height - bar_h
        freqs = [6, 10, 16, 24, 32, 48]
        section_w = self.width // len(freqs)
        for i, freq in enumerate(freqs):
            bar_w = max(1, section_w // freq)
            for x in range(section_w):
                px = i * section_w + x
                if (x // bar_w) % 2 == 0:
                    for y in range(bottom_y, self.height):
                        self.set_pixel(px, y, 255, 255, 255)

    def draw_luma_bars(self):
        self.fill_screen(0, 0, 0)
        num_bars = 8
        bar_h = self.height // num_bars

        for bar in range(num_bars):
            y_start = bar * bar_h
            for x in range(self.width):
                if bar % 2 == 0:
                    gray = int((x / self.width) * 255)
                else:
                    gray = int((1 - x / self.width) * 255)
                for y in range(y_start, min(y_start + bar_h, self.height)):
                    self.set_pixel(x, y, gray, gray, gray)

    def draw_vignette(self):
        cx, cy = self.width // 2, self.height // 2
        max_dist = math.sqrt(cx**2 + cy**2)

        for y in range(self.height):
            for x in range(self.width):
                dist = math.sqrt((x - cx)**2 + (y - cy)**2)
                gray = int(255 * (1 - dist / max_dist))
                gray = max(0, min(255, gray))
                self.set_pixel(x, y, gray, gray, gray)

    def cache_text(self, text):
        """Pre-render text to a list of pixel offsets for fast drawing"""
        if not text:
            self.text_cache = []
            return

        text = text.upper()
        scale = 5
        char_w = 6 * scale

        pixels = []
        cx = 0
        for char in text:
            font = FONT_5X7.get(char, FONT_5X7.get(' '))
            if font:
                for row in range(7):
                    for col in range(5):
                        if font[row] & (1 << (4 - col)):
                            for sy in range(scale):
                                for sx in range(scale):
                                    px = cx + col * scale + sx
                                    py = row * scale + sy
                                    pixels.append((px, py))
            cx += char_w

        self.text_cache = pixels
        self.text_cache_artist = text
        self.text_width = cx
        self.text_height = 7 * scale

    def draw_3d_text(self, text):
        """Draw 3D rotating text overlay using cached pixels"""
        if not text:
            return

        text = text.upper()

        # Rebuild cache if artist changed
        if self.text_cache is None or self.text_cache_artist != text:
            self.cache_text(text)

        if not self.text_cache:
            return

        # Rotation angle based on frame
        angle = (self.animation_frame * 12) % 360
        rad = math.radians(angle)

        # 3D rotation: squeeze horizontally as it "rotates"
        squeeze = abs(math.cos(rad))
        if squeeze < 0.1:
            squeeze = 0.1

        # Center on screen
        squeezed_w = int(self.text_width * squeeze)
        base_x = (self.width - squeezed_w) // 2
        base_y = (self.height - self.text_height) // 2

        # Draw shadow first
        shadow_offset = 4
        shadow_color = rgb_to_rgb565(60, 60, 60)
        for px, py in self.text_cache:
            sx = base_x + int(px * squeeze) + shadow_offset
            sy = base_y + py + shadow_offset
            if 0 <= sx < self.width and 0 <= sy < self.height:
                offset = sy * self.stride + sx * 2
                self.buffer[offset] = shadow_color & 0xFF
                self.buffer[offset + 1] = (shadow_color >> 8) & 0xFF

        # Draw main text
        text_color = rgb_to_rgb565(255, 255, 255)
        for px, py in self.text_cache:
            sx = base_x + int(px * squeeze)
            sy = base_y + py
            if 0 <= sx < self.width and 0 <= sy < self.height:
                offset = sy * self.stride + sx * 2
                self.buffer[offset] = text_color & 0xFF
                self.buffer[offset + 1] = (text_color >> 8) & 0xFF

    def set_pattern(self, pattern_name):
        if pattern_name in self.patterns:
            self.current_pattern = pattern_name
            self.pattern_on = True
            self.pattern_dirty = True
            self.pattern_changed.set()
            print(f"Pattern: {pattern_name}", flush=True)
            return True
        return False

    def toggle_pattern(self):
        self.pattern_on = not self.pattern_on
        self.pattern_dirty = True
        self.pattern_changed.set()
        print(f"Pattern {'ON' if self.pattern_on else 'OFF'}", flush=True)
        return self.pattern_on

    def toggle_overlay(self):
        self.artist_overlay = not self.artist_overlay
        print(f"Overlay {'ON' if self.artist_overlay else 'OFF'}: {self.get_artist()}", flush=True)
        return self.artist_overlay

    def next_artist(self):
        if len(self.artists) > 0:
            self.artist_idx = (self.artist_idx + 1) % len(self.artists)
        self.text_cache = None  # Invalidate cache
        return self.get_artist()

    def prev_artist(self):
        if len(self.artists) > 0:
            self.artist_idx = (self.artist_idx - 1) % len(self.artists)
        self.text_cache = None  # Invalidate cache
        return self.get_artist()

    def get_artist(self):
        if len(self.artists) > 0 and 0 <= self.artist_idx < len(self.artists):
            return self.artists[self.artist_idx]
        return "NO ARTIST"

    def render_frame(self):
        """Render current frame with pattern and optional overlay"""
        # Only redraw pattern if changed
        if self.pattern_dirty:
            if self.pattern_on:
                self.patterns[self.current_pattern]()
            else:
                self.fill_screen(0, 0, 0)
            # Cache the pattern
            self.pattern_cache[:] = self.buffer[:]
            self.pattern_dirty = False
        else:
            # Restore from cache
            self.buffer[:] = self.pattern_cache[:]

        if self.artist_overlay:
            self.draw_3d_text(self.get_artist())

        self.flip()

    def socket_listener(self):
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o666)
        server.listen(1)
        server.settimeout(0.1)

        print(f"Listening: {SOCKET_PATH}", flush=True)

        while self.running:
            try:
                conn, _ = server.accept()
                data = conn.recv(256).decode().strip()

                if data == "quit":
                    self.running = False
                    response = "OK"
                elif data == "list":
                    response = ",".join(self.patterns.keys())
                elif data.startswith("set:"):
                    pattern = data[4:]
                    response = "OK" if self.set_pattern(pattern) else "ERR"
                elif data == "current":
                    response = self.current_pattern
                elif data == "toggle":
                    response = "ON" if self.toggle_pattern() else "OFF"
                elif data == "overlay":
                    response = "ON" if self.toggle_overlay() else "OFF"
                elif data == "next_artist":
                    response = self.next_artist()
                elif data == "prev_artist":
                    response = self.prev_artist()
                elif data == "artist":
                    response = self.get_artist()
                elif data == "artists":
                    response = "|".join(self.artists)
                elif data == "overlay_status":
                    response = "ON" if self.artist_overlay else "OFF"
                elif data == "pattern_status":
                    response = "ON" if self.pattern_on else "OFF"
                else:
                    response = "ERR"

                conn.send(response.encode())
                conn.close()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Socket error: {e}", flush=True)

        server.close()
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

    def run(self):
        listener = threading.Thread(target=self.socket_listener, daemon=True)
        listener.start()

        self.render_frame()

        while self.running:
            if self.artist_overlay:
                self.animation_frame += 1
                self.render_frame()
                time.sleep(0.033)  # ~30fps for smooth rotation
            elif self.pattern_changed.is_set():
                self.pattern_changed.clear()
                self.render_frame()
            else:
                time.sleep(0.1)

        self.fb.close()
        os.close(self.fb_fd)
        print("Stopped", flush=True)


def send_command(cmd):
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        sock.send(cmd.encode())
        response = sock.recv(256).decode()
        sock.close()
        return response
    except Exception as e:
        return f"ERR: {e}"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1] if len(sys.argv) == 2 else f"{sys.argv[1]}:{sys.argv[2]}"
        print(send_command(cmd))
    else:
        gen = PatternGenerator()
        gen.run()
