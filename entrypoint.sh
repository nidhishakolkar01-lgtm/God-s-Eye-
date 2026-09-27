#!/bin/bash
set -e

# ======================================================================
# PROJECT TRINETRA-C2 // CLOUD CONTAINER ENTRYPOINT SCRIPT
# AI Border Surveillance Video Analytics (SIH PS 26187 // MHA CIBMS)
# ======================================================================

# Ensure runtime directories exist with write permissions
mkdir -p evidence static known_faces

# Initialize empty alert_config.json if not present
if [ ! -f alert_config.json ]; then
    echo '{"telegram_enabled": false, "webhook_enabled": false, "cooldown_seconds": 10.0, "total_alerts_sent": 0}' > alert_config.json
fi

# Default PORT fallback if not provided by Cloud Run / Render / Railway
export PORT="${PORT:-8080}"
export PYTHONUNBUFFERED=1
export YOLO_CONFIG_DIR=/tmp/Ultralytics
mkdir -p /tmp/Ultralytics
export OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp|fflags;nobuffer|max_delay;0"

echo "======================================================================"
echo " PROJECT TRINETRA-C2 // AUTONOMOUS TACTICAL C2 CLOUD INSTANCE"
echo " Sponsoring Authority: Ministry of Home Affairs (MHA) | PS 26187"
echo " Active Listening Address: http://0.0.0.0:${PORT}"
echo "======================================================================"

# Execute server process
exec python server.py
