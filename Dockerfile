FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install ZeroClaw v0.6.8
RUN curl -L -o zeroclaw.tar.gz "https://github.com/zeroclaw-labs/zeroclaw/releases/download/v0.6.8/zeroclaw-x86_64-unknown-linux-gnu.tar.gz" \
    && tar -xzf zeroclaw.tar.gz \
    && mv zeroclaw /usr/local/bin/zeroclaw \
    && rm zeroclaw.tar.gz \
    && chmod +x /usr/local/bin/zeroclaw

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
