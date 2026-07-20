# Production Dockerfile for FastAPI Backend (v1.2.0-stable)
FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies needed for python libraries (like shapefile, psycopg, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /workspace

EXPOSE 8000

# Use Gunicorn with Uvicorn workers for production reliability and concurrency
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
