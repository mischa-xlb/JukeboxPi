#!/bin/bash
# Installs and enables the JukeboxPi systemd services (run on the Pi with sudo).
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo cp "$SCRIPT_DIR/jukebox.service" "$SCRIPT_DIR/jukebox-web.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jukebox.service jukebox-web.service

echo
echo "Installed. Useful commands:"
echo "  systemctl status jukebox jukebox-web"
echo "  journalctl -u jukebox -f"
echo "  sudo systemctl restart jukebox"
