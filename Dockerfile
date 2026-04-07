FROM python:3.11

WORKDIR /app

# Install system dependencies
# 'jq' is likely the missing command causing exit code 127
RUN apt-get update && apt-get install -y \
    curl \
    git \
    unzip \
    sudo \
    jq \
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
