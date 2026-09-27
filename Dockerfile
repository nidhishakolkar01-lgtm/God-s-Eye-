# ======================================================================
# PROJECT TRINETRA-C2 // PRODUCTION CLOUD DOCKERFILE
# AI Border Surveillance Video Analytics (SIH PS 26187 // MHA CIBMS)
# Base: Debian-based Python 3.10 Slim with CPU-Optimized Inference
# ======================================================================

FROM python:3.10-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp|fflags;nobuffer|max_delay;0"

# Install essential system dependencies for OpenCV, PyTorch, and video decoders
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set container working directory
WORKDIR /app

# Upgrade pip and pre-install lightweight CPU PyTorch & Torchvision wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy and install application dependencies
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Create necessary runtime directories
RUN mkdir -p /app/evidence /app/static /app/known_faces /app/models /app/sample_footage

# Copy application code and model artifacts
COPY core/ /app/core/
COPY static/ /app/static/
COPY models/ /app/models/
COPY sample_footage/ /app/sample_footage/
COPY known_faces/ /app/known_faces/
COPY vehicle_watchlist.json /app/
COPY satellites_tle.json /app/
COPY yolov8n.pt /app/
COPY server.py /app/
COPY entrypoint.sh /app/

# Ensure entrypoint script has executable permissions
RUN chmod +x /app/entrypoint.sh

# Expose default HTTP C2 port
EXPOSE 8080

# Health check to verify telemetry endpoint is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/api/telemetry || exit 1

# Launch using entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
