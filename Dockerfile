# Dockerfile
FROM python:3.11-slim

# Keep Python fast & quiet
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

# Runtime dep for numpy/pandas wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for better Docker layer caching
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source
COPY . /app

# Optional healthcheck (simple TCP connect to $PORT)
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python - <<'PY' || exit 1
import os, socket
s = socket.socket()
s.settimeout(2)
s.connect(("127.0.0.1", int(os.environ.get("PORT","8080"))))
s.close()
PY

# Start the app (Render sets $PORT)
CMD gunicorn -b 0.0.0.0:${PORT:-8080} wsgi:app
