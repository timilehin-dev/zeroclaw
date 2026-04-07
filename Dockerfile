FROM python:3.11-slim

WORKDIR /app

# Install system tools (Added 'unzip' and 'git' to fix exit code 127)
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install ZeroClaw
RUN curl -sSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/main/install.sh | bash

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app
COPY app.py .

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
