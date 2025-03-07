# Use the official Python 3.11 image
FROM python:3.11

# Expose the application port
EXPOSE 5002

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install dependencies and Google Chrome
RUN apt update && apt install -y \
    wget \
    xvfb \
    x11-utils \
    x11vnc \
    fluxbox \
    fonts-liberation \
    libasound2 \
    libnspr4 \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    lsb-release \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome manually
RUN wget -qO - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list && \
    apt update && apt install -y google-chrome-stable

# Set working directory
WORKDIR /app
COPY . /app

# Install Python requirements
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Create a non-root user and set permissions
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Set DISPLAY environment variable for Xvfb
ENV DISPLAY=:99

# Start Xvfb and then run Gunicorn
CMD Xvfb :99 -screen 0 1920x1080x24 & gunicorn --bind 0.0.0.0:5002 app:app
