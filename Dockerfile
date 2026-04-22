# Dockerfile for SSS Secure Shielding Service Backend
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies (required for some ML packages)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download necessary language model for Presidio Analyzer
RUN python -m spacy download en_core_web_lg

# Copy application files
COPY . .

# Expose the Flask port
EXPOSE 5000

# Command to run the backend service
CMD ["python", "flaskBackend.py"]
