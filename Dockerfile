# Use Python 3.12 (stable, avoids pandas build errors)
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for pandas, numpy, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libatlas-base-dev \
    libblas-dev \
    liblapack-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY . .

# Expose port for Render
EXPOSE 5000

# Run the app with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
