FROM python:3.11-slim

WORKDIR /app

# Install system dependencies that might be needed by libraries like sentence-transformers
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies spec
COPY pyproject.toml .

# Copy backend source code
COPY . .

# Install python dependencies
RUN pip install --no-cache-dir .

# Expose backend port
EXPOSE 8000

# Command to run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
