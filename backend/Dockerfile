FROM python:3.12-slim

WORKDIR /app

# Copy dependency manifest
COPY requirements.txt .
# Install dependencies
RUN pip install -r requirements.txt
# Copy application code
COPY . .