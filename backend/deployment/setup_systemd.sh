#!/bin/bash
# Setup systemd timer for daily ingestion

set -e

echo "Setting up Dr. Chaffee daily ingestion systemd timer..."

# Get the absolute path to the backend directory
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Backend directory: $BACKEND_DIR"

# Update paths in service file
SERVICE_FILE="$BACKEND_DIR/deployment/drchaffee-ingest.service"
sed -i "s|/path/to/ask-dr-chaffee/backend|$BACKEND_DIR|g" "$SERVICE_FILE"

# Copy service and timer files to systemd
sudo cp "$BACKEND_DIR/deployment/drchaffee-ingest.service" /etc/systemd/system/
sudo cp "$BACKEND_DIR/deployment/drchaffee-ingest.timer" /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timer
sudo systemctl enable drchaffee-ingest.timer
sudo systemctl start drchaffee-ingest.timer

echo ""
echo "✅ Systemd timer installed successfully!"
echo ""
echo "📊 Status:"
sudo systemctl status drchaffee-ingest.timer --no-pager
echo ""
echo "📅 Next run:"
sudo systemctl list-timers drchaffee-ingest.timer --no-pager
echo ""
echo "📝 Useful commands:"
echo "  View logs:        sudo journalctl -u drchaffee-ingest -f"
echo "  Run now:          sudo systemctl start drchaffee-ingest"
echo "  Check status:     sudo systemctl status drchaffee-ingest"
echo "  Disable timer:    sudo systemctl disable drchaffee-ingest.timer"
echo ""
