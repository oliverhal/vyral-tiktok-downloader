FROM python:3.11-slim

# Install ffmpeg (yt-dlp uses it for merging audio/video streams)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
        rm -rf /var/lib/apt/lists/*

        WORKDIR /app

        # Install Python dependencies
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        # Cache bust v3
        # Copy application code
        COPY . .

        # Create download directory
        RUN mkdir -p /tmp/vyral_downloads

        EXPOSE 8000

        # Start with gunicorn (production server)
        # - timeout 600s to handle large batches
        # - 1 worker with 4 threads (single worker needed for in-memory job store)
        CMD ["gunicorn", "app:app", \
             "--bind", "0.0.0.0:8000", \
                  "--timeout", "600", \
                       "--workers", "1", \
                            "--threads", "4"]
