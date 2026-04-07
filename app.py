import os
import subprocess
from fastapi import FastAPI, Request
from slack_sdk import WebClient

app = FastAPI()

# Initialize Slack Client
# Ensure SLACK_BOT_TOKEN is set in Northflank Environment Variables
slack = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

@app.get("/")
def home():
    return {"status": "running"}

@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.json()

    # Slack verification handshake
    if body.get("type") == "url_verification":
        return {"challenge": body["challenge"]}

    event = body.get("event", {})

    if event.get("type") == "app_mention":
        user_text = event.get("text", "")
        channel = event.get("channel")

        # Prepare the command
        # We use shell=True to ensure the 'zeroclaw' command is found in PATH
        # We pass the current environment so OLLAMA keys are accessible to the tool
        try:
            result = subprocess.run(
                f'zeroclaw run "{user_text}"',
                shell=True,
                capture_output=True,
                text=True,
                env=os.environ
            )
            
            # Log errors if any
            if result.returncode != 0:
                print(f"ZeroClaw Error: {result.stderr}")
                reply = f"Error running ZeroClaw: {result.stderr}"
            else:
                reply = result.stdout.strip() or "No response generated."
                
        except Exception as e:
            reply = f"Failed to execute command: {str(e)}"

        # Post reply to Slack
        slack.chat_postMessage(
            channel=channel,
            text=reply
        )

    return {"ok": True}
