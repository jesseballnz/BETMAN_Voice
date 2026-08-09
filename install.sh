#!/bin/bash
set -e

echo "=== BETMAN_Voice Installer ==="

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "macOS detected"
  BREW=$(which brew || echo "/opt/homebrew/bin/brew")
  $BREW install python@3.11 redis || true
else
  echo "Linux detected - install python3.11 + redis manually"
fi

# Create venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "VoiceBox installed. Run with:"
echo "  ./scripts/run.sh"
echo ""
echo "Then visit http://localhost:8000"