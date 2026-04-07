FROM ghcr.io/zeroclaw-labs/zeroclaw:latest

WORKDIR /app

# Install Python and pip
RUN apt-get update && apt-get install -y python3 python3-pip

# Install required Python packages
RUN pip3 install fastapi uvicorn slack_sdk

COPY app.py .

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
