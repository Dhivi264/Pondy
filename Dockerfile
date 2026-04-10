FROM python:3.10-slim

# Install system dependencies required for OpenCV, PyAV, and SQLite
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    libsm6 \
    libxext6 \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend codebase from the backend directory
COPY backend/ .

# Expose Hugging Face default port
EXPOSE 7860

# Start Uvicorn production server
CMD ["python", "run.py"]
