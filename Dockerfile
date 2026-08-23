FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV headless and general build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run expects the app to listen on the port specified in the PORT env var.
# Default Cloud Run port is 8080.
ENV PORT=8080

# Start FastAPI via Uvicorn
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
