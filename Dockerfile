# Use the official Ubuntu image as the base image
FROM python:3-slim-bookworm

# Set environment variables to avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV DOCKERMODE=true

# Install necessary packages for Xvfb and pyvirtualdisplay
RUN apt-get update && \
    apt-get install -y \
    pipx \
    chromium \
    wget \
    gnupg \
    ca-certificates \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    x11-apps \
    fonts-liberation \
    libappindicator3-1 \
    libu2f-udev \
    libvulkan1 \
    libdrm2 \
    xdg-utils \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set up a working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose the port for remote debugging
EXPOSE 9222

# Expose the port for the FastAPI server
EXPOSE 8000

# Default command
CMD ["python", "server.py"]
