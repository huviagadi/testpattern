#!/usr/bin/env python3
"""
Touch UI for Pi Test Signal Generator
8 pattern buttons + artist display with prev/next
"""

import os
import struct
import socket
import time
import glob

FB_DEVICE = "/dev/fb1"
SOCKET_PATH = "/tmp/pattern_gen.sock"

def find_touch_device():
    """Find ADS7846 touchscreen event device dynamically"""
    try:
        with open('/proc/bus/input/devices', 'r') as f:
            content = f.read()

        # Split into device blocks
        blocks = content.split('\n\n')
        for block in blocks:
            if 'ADS7846' in block:
                # Find the event handler
                for line in block.split('\n'):
                    if line.startswith('H: Handlers='):
                        handlers = line.split('=')[1].split()
                        for h in handlers:
                            if h.startswith('event'):
                                return f'/dev/input/{h}'
    except:
        pass

    # Fallback: try common event devices
    for i in range(5):
        path = f'/dev/input/event{i}'
        if os.path.exists(path):
            return path
    return '/dev/input/event0'

TOUCH_DEVICE = find_touch_device()

# 6 patterns + 2 nav buttons
PATTERNS = [
    ("SMPTE", "smpte"),
    ("Grid", "grid"),
    ("OldTV", "oldtv"),
    ("PM5544", "pm5544"),
    ("Bars", "bars"),
    ("Vign", "vignette"),
]

W, H = 480, 320

def rgb565(r, g, b):
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)

# Simple 5x7 font
FONT = {
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
    ':': [0x00, 0x04, 0x04, 0x00, 0x04, 0x04, 0x00],
    '<': [0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02],
    '>': [0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08],
    'a': [0x00, 0x00, 0x0E, 0x01, 0x0F, 0x11, 0x0F],
    'b': [0x10, 0x10, 0x1E, 0x11, 0x11, 0x11, 0x1E],
    'c': [0x00, 0x00, 0x0E, 0x10, 0x10, 0x11, 0x0E],
    'd': [0x01, 0x01, 0x0F, 0x11, 0x11, 0x11, 0x0F],
    'e': [0x00, 0x00, 0x0E, 0x11, 0x1F, 0x10, 0x0E],
    'g': [0x00, 0x00, 0x0F, 0x11, 0x0F, 0x01, 0x0E],
    'h': [0x10, 0x10, 0x16, 0x19, 0x11, 0x11, 0x11],
    'i': [0x04, 0x00, 0x0C, 0x04, 0x04, 0x04, 0x0E],
    'l': [0x0C, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E],
    'm': [0x00, 0x00, 0x1A, 0x15, 0x15, 0x11, 0x11],
    'n': [0x00, 0x00, 0x16, 0x19, 0x11, 0x11, 0x11],
    'o': [0x00, 0x00, 0x0E, 0x11, 0x11, 0x11, 0x0E],
    'p': [0x00, 0x00, 0x1E, 0x11, 0x1E, 0x10, 0x10],
    'r': [0x00, 0x00, 0x16, 0x19, 0x10, 0x10, 0x10],
    's': [0x00, 0x00, 0x0F, 0x10, 0x0E, 0x01, 0x1E],
    't': [0x04, 0x04, 0x1F, 0x04, 0x04, 0x05, 0x02],
    'u': [0x00, 0x00, 0x11, 0x11, 0x11, 0x13, 0x0D],
    'v': [0x00, 0x00, 0x11, 0x11, 0x11, 0x0A, 0x04],
    'y': [0x00, 0x00, 0x11, 0x11, 0x0F, 0x01, 0x0E],
}

def send_cmd(cmd):
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)
        sock.send(cmd.encode())
        r = sock.recv(256).decode()
        sock.close()
        return r
    except:
        return ""

def draw_text(buf, x, y, text, color, scale=2):
    cx = x
    for char in text:
        font = FONT.get(char)
        if font:
            for row in range(7):
                for col in range(5):
                    if font[row] & (1 << (4 - col)):
                        for sy in range(scale):
                            for sx in range(scale):
                                px = cx + col * scale + sx
                                py = y + row * scale + sy
                                if 0 <= px < W and 0 <= py < H:
                                    idx = (py * W + px) * 2
                                    buf[idx] = color & 0xFF
                                    buf[idx + 1] = (color >> 8) & 0xFF
        cx += 6 * scale

def draw_ui(current_pattern, pattern_on, artist, overlay_on):
    bg = rgb565(20, 20, 25)
    btn_off = rgb565(50, 50, 60)
    btn_on = rgb565(80, 120, 200)
    btn_nav = rgb565(60, 80, 60)
    text_color = rgb565(255, 255, 255)
    border = rgb565(80, 80, 90)
    artist_bg = rgb565(30, 30, 40)
    overlay_color = rgb565(100, 200, 100) if overlay_on else rgb565(200, 100, 100)

    buf = bytearray(W * H * 2)

    # Fill background
    for i in range(0, len(buf), 2):
        buf[i] = bg & 0xFF
        buf[i + 1] = (bg >> 8) & 0xFF

    # Button grid: 4 cols x 2 rows for patterns + nav
    btn_w, btn_h = 110, 50
    margin = 8
    start_x, start_y = 10, 10

    # Draw 6 pattern buttons
    for i, (label, cmd) in enumerate(PATTERNS):
        col = i % 4
        row = i // 4
        x = start_x + col * (btn_w + margin)
        y = start_y + row * (btn_h + margin)

        # Button is active if it matches current pattern AND pattern is on
        is_active = (cmd == current_pattern and pattern_on)
        color = btn_on if is_active else btn_off

        # Fill button
        for py in range(y, min(y + btn_h, H)):
            for px in range(x, min(x + btn_w, W)):
                idx = (py * W + px) * 2
                buf[idx] = color & 0xFF
                buf[idx + 1] = (color >> 8) & 0xFF

        # Border
        for py in range(y, min(y + btn_h, H)):
            for t in range(2):
                if x + t < W:
                    idx = (py * W + x + t) * 2
                    buf[idx] = border & 0xFF
                    buf[idx + 1] = (border >> 8) & 0xFF
                if x + btn_w - 1 - t < W:
                    idx = (py * W + x + btn_w - 1 - t) * 2
                    buf[idx] = border & 0xFF
                    buf[idx + 1] = (border >> 8) & 0xFF
        for px in range(x, min(x + btn_w, W)):
            for t in range(2):
                if y + t < H:
                    idx = ((y + t) * W + px) * 2
                    buf[idx] = border & 0xFF
                    buf[idx + 1] = (border >> 8) & 0xFF
                if y + btn_h - 1 - t < H:
                    idx = ((y + btn_h - 1 - t) * W + px) * 2
                    buf[idx] = border & 0xFF
                    buf[idx + 1] = (border >> 8) & 0xFF

        # Text centered
        text_w = len(label) * 12
        text_x = x + (btn_w - text_w) // 2
        text_y = y + (btn_h - 14) // 2
        draw_text(buf, text_x, text_y, label, text_color)

    # Nav buttons (< and >) - row 1, cols 2-3
    nav_buttons = [("<", "prev"), (">", "next")]
    for i, (label, action) in enumerate(nav_buttons):
        col = 2 + i
        row = 1
        x = start_x + col * (btn_w + margin)
        y = start_y + row * (btn_h + margin)

        # Fill button
        for py in range(y, min(y + btn_h, H)):
            for px in range(x, min(x + btn_w, W)):
                idx = (py * W + px) * 2
                buf[idx] = btn_nav & 0xFF
                buf[idx + 1] = (btn_nav >> 8) & 0xFF

        # Border
        for py in range(y, min(y + btn_h, H)):
            for t in range(2):
                if x + t < W:
                    idx = (py * W + x + t) * 2
                    buf[idx] = border & 0xFF
                    buf[idx + 1] = (border >> 8) & 0xFF
                if x + btn_w - 1 - t < W:
                    idx = (py * W + x + btn_w - 1 - t) * 2
                    buf[idx] = border & 0xFF
                    buf[idx + 1] = (border >> 8) & 0xFF
        for px in range(x, min(x + btn_w, W)):
            for t in range(2):
                if y + t < H:
                    idx = ((y + t) * W + px) * 2
                    buf[idx] = border & 0xFF
                    buf[idx + 1] = (border >> 8) & 0xFF
                if y + btn_h - 1 - t < H:
                    idx = ((y + btn_h - 1 - t) * W + px) * 2
                    buf[idx] = border & 0xFF
                    buf[idx + 1] = (border >> 8) & 0xFF

        # Arrow text
        text_x = x + (btn_w - 12) // 2
        text_y = y + (btn_h - 14) // 2
        draw_text(buf, text_x, text_y, label, text_color)

    # Artist display area
    artist_y = start_y + 2 * (btn_h + margin) + 10
    artist_h = H - artist_y - 10

    # Fill artist area
    for py in range(artist_y, min(artist_y + artist_h, H)):
        for px in range(start_x, W - start_x):
            idx = (py * W + px) * 2
            buf[idx] = artist_bg & 0xFF
            buf[idx + 1] = (artist_bg >> 8) & 0xFF

    # Border for artist area
    for py in range(artist_y, min(artist_y + artist_h, H)):
        for t in range(2):
            idx = (py * W + start_x + t) * 2
            buf[idx] = overlay_color & 0xFF
            buf[idx + 1] = (overlay_color >> 8) & 0xFF
            idx = (py * W + W - start_x - 1 - t) * 2
            buf[idx] = overlay_color & 0xFF
            buf[idx + 1] = (overlay_color >> 8) & 0xFF
    for px in range(start_x, W - start_x):
        for t in range(2):
            idx = ((artist_y + t) * W + px) * 2
            buf[idx] = overlay_color & 0xFF
            buf[idx + 1] = (overlay_color >> 8) & 0xFF
            idx = ((artist_y + artist_h - 1 - t) * W + px) * 2
            buf[idx] = overlay_color & 0xFF
            buf[idx + 1] = (overlay_color >> 8) & 0xFF

    # "CURRENT ARTIST" label
    label = "CURRENT ARTIST"
    label_x = (W - len(label) * 12) // 2
    draw_text(buf, label_x, artist_y + 15, label, overlay_color)

    # Artist name (larger, centered)
    name_scale = 3
    name_w = len(artist) * 6 * name_scale
    name_x = (W - name_w) // 2
    name_y = artist_y + 50
    draw_text(buf, name_x, name_y, artist.upper(), text_color, name_scale)

    # Overlay status hint
    status = "TAP TO TOGGLE OVERLAY"
    status_x = (W - len(status) * 10) // 2
    draw_text(buf, status_x, artist_y + artist_h - 30, status, overlay_color, 1)

    return buf

def raw_to_screen(raw_x, raw_y):
    """Convert raw touch to screen coordinates - calibrated for rotate=270"""
    norm_x = raw_x / 4095.0
    norm_y = raw_y / 4095.0
    # Correct mapping for this screen orientation
    sx = int(norm_x * W)
    sy = int((1.0 - norm_y) * H)
    return max(0, min(W - 1, sx)), max(0, min(H - 1, sy))

def screen_to_action(sx, sy, current_pattern, pattern_on):
    """Determine action from screen coordinates"""
    btn_w, btn_h = 110, 50
    margin = 8
    start_x, start_y = 10, 10

    # Check pattern buttons (6 buttons, 4 cols x 2 rows but only 6 used)
    for i, (label, cmd) in enumerate(PATTERNS):
        col = i % 4
        row = i // 4
        x = start_x + col * (btn_w + margin)
        y = start_y + row * (btn_h + margin)

        if x <= sx < x + btn_w and y <= sy < y + btn_h:
            # If tapping active pattern, toggle off
            if cmd == current_pattern and pattern_on:
                return ("toggle", None)
            else:
                return ("pattern", cmd)

    # Check nav buttons (row 1, cols 2-3)
    for i, action in enumerate(["prev", "next"]):
        col = 2 + i
        row = 1
        x = start_x + col * (btn_w + margin)
        y = start_y + row * (btn_h + margin)

        if x <= sx < x + btn_w and y <= sy < y + btn_h:
            return ("artist", action)

    # Check artist area (tap to toggle overlay)
    artist_y = start_y + 2 * (btn_h + margin) + 10
    if sy >= artist_y and start_x <= sx < W - start_x:
        return ("overlay", None)

    return (None, None)

def main():
    fb = open(FB_DEVICE, 'r+b', buffering=0)

    # Get initial state
    current_pattern = send_cmd("current") or "smpte"
    pattern_on = send_cmd("pattern_status") == "ON"
    artist = send_cmd("artist") or "ARTIST"
    overlay_on = send_cmd("overlay_status") == "ON"

    buf = draw_ui(current_pattern, pattern_on, artist, overlay_on)
    fb.seek(0)
    fb.write(buf)
    print(f"Touch: {TOUCH_DEVICE}", flush=True)
    print(f"Ready: {current_pattern}, Artist: {artist}", flush=True)

    touch_fd = open(TOUCH_DEVICE, 'rb')
    raw_x, raw_y = 0, 0
    last_press = 0

    while True:
        data = touch_fd.read(16)
        if len(data) < 16:
            continue

        _, _, ev_type, ev_code, ev_value = struct.unpack('llHHi', data)

        if ev_type == 3:  # EV_ABS
            if ev_code == 0:
                raw_x = ev_value
            elif ev_code == 1:
                raw_y = ev_value
        elif ev_type == 1 and ev_code == 330 and ev_value == 0:  # BTN_TOUCH up
            now = time.time()
            if now - last_press > 0.3 and raw_x > 100 and raw_y > 100:
                sx, sy = raw_to_screen(raw_x, raw_y)
                action, value = screen_to_action(sx, sy, current_pattern, pattern_on)

                if action == "pattern":
                    send_cmd(f"set:{value}")
                    current_pattern = value
                    pattern_on = True
                    print(f"Pattern: {value}", flush=True)
                elif action == "toggle":
                    result = send_cmd("toggle")
                    pattern_on = (result == "ON")
                    print(f"Pattern {'ON' if pattern_on else 'OFF'}", flush=True)
                elif action == "artist":
                    if value == "prev":
                        artist = send_cmd("prev_artist")
                    else:
                        artist = send_cmd("next_artist")
                    print(f"Artist: {artist}", flush=True)
                elif action == "overlay":
                    result = send_cmd("overlay")
                    overlay_on = (result == "ON")
                    print(f"Overlay {'ON' if overlay_on else 'OFF'}", flush=True)

                if action:
                    buf = draw_ui(current_pattern, pattern_on, artist, overlay_on)
                    fb.seek(0)
                    fb.write(buf)

                last_press = now

if __name__ == "__main__":
    main()
