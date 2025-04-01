FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    gcc \
    libsndfile1 \
    libportaudio2 \
    portaudio19-dev \
    ffmpeg \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

RUN pip install --no-cache-dir setuptools wheel

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories and set permissions before copying application code
RUN mkdir -p /app/data /home/app/.cache/huggingface/transformers \
    && chmod 777 /app/data \
    && addgroup --system --gid 1001 app \
    && adduser --system --uid 1001 --gid 1001 --home /home/app app \
    && chown -R app:app /app /home/app

# Copy application code
COPY --chown=app:app . .

# Set environment variables for model caching
ENV HOME=/home/app
ENV HF_HOME=/home/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/home/app/.cache/huggingface/transformers

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"] 