# Production Dockerfile for FastAPI Backend (v1.2.0-stable)
FROM python:3.11-slim

WORKDIR /workspace

ENV PYTHONPATH=/workspace:/workspace/backend
ENV PYTHONUNBUFFERED=1

# Install system dependencies needed for python libraries (like shapefile, psycopg, gdal, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    curl \
    fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /workspace

EXPOSE 8000

# Use native Uvicorn ASGI server matching local environment spec (start_omnisite_local.bat)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "75"]
