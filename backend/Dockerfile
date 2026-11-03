# ── Backend Dockerfile ─────────────────────────────────────────────────────────
# Multi-stage build for a lean production image

FROM python:3.11-slim AS base

# System dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download YOLOv8 nano weights
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Copy application code
COPY . .

# Create output directories
RUN mkdir -p uploads outputs/annotated outputs/heatmaps

EXPOSE 8000

# Run with uvicorn (single worker for GPU; use gunicorn + uvicorn workers for CPU fleet)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
