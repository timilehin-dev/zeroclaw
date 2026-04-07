FROM ghcr.io/zeroclaw-labs/zeroclaw:latest

WORKDIR /app

# Install Python tools
RUN pip install fastapi uvicorn slack_sdk

COPY app.py .
COPY requirements.txt .

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
