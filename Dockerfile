FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including WeasyPrint requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash may \
    && mkdir -p /app/data/uploads \
    && chown -R may:may /app

USER may

# Set environment variables
ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5050/health')" || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "2", "--threads", "4", "run:app"]
