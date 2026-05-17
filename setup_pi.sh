#!/bin/bash
# Setup script for testpattern Pi after fresh flash
# Run from Mac: ./setup_pi.sh <pi-ip-or-hostname>

PI_HOST="${1:-admin@testpattern.local}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up testpattern Pi at $PI_HOST"
echo "Password is 'admin'"
echo ""

# Copy Python files
echo "=== Copying Python files ==="
scp "$SCRIPT_DIR/pattern_gen.py" "$PI_HOST:/home/admin/"
scp "$SCRIPT_DIR/touch_ui.py" "$PI_HOST:/home/admin/"
scp "$SCRIPT_DIR/artists.txt" "$PI_HOST:/home/admin/"

# Copy and install systemd services
echo "=== Installing systemd services ==="
scp "$SCRIPT_DIR/config/pattern_gen.service" "$PI_HOST:/tmp/"
scp "$SCRIPT_DIR/config/touch_ui.service" "$PI_HOST:/tmp/"
ssh "$PI_HOST" "sudo mv /tmp/pattern_gen.service /etc/systemd/system/ && sudo mv /tmp/touch_ui.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable pattern_gen.service touch_ui.service"

# Remind about config.txt
echo ""
echo "=== MANUAL STEP REQUIRED ==="
echo "Add the following to /boot/firmware/config.txt on the Pi:"
echo ""
cat "$SCRIPT_DIR/config/config.txt.additions"
echo ""
echo "Run: ssh $PI_HOST 'sudo nano /boot/firmware/config.txt'"
echo "Then reboot: ssh $PI_HOST 'sudo reboot'"
echo ""
echo "Done!"
