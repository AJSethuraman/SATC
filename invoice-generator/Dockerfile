# Invoicer — single-image build with all native dependencies baked in.
# WeasyPrint needs Pango/Cairo/GDK-PixBuf at runtime; installing them here
# means users never have to touch system packages themselves.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Native libraries required by WeasyPrint, plus fonts for PDF rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better layer caching. The deploy
# requirements add the PostgreSQL driver on top of the base requirements.
COPY requirements.txt requirements-deploy.txt ./
RUN pip install --no-cache-dir -r requirements-deploy.txt

COPY . .

# Runtime data location for transient generated PDFs.
RUN mkdir -p /app/data /app/invoices

EXPOSE 5000

# Bind to $PORT when the host provides one (Render, etc.), else 5000.
# 2 workers / 4 threads with a long timeout to accommodate PDF rendering.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --threads 4 --timeout 120 app:app"]
