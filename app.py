import os
import subprocess
from fastapi import FastAPI, Request
from slack_sdk import WebClient

app = FastAPI()

# Initialize Slack Client
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

        # Clean text (remove the bot mention prefix)
        clean_text = user_text.split(" ", 1)[-1] if " " in user_text else user_text

        try:
            # UPDATED COMMAND: Use 'agent' with '-m' for single message mode
            result = subprocess.run(
                ["zeroclaw", "agent", "-m", clean_text],
                capture_output=True,
                text=True,
                env=os.environ  # Passes OLLAMA_BASE_URL and API_KEY
            )

            if result.returncode != 0:
                print(f"ZeroClaw Error: {result.stderr}")
                reply = f"Error: {result.stderr.strip()}"
            else:
                reply = result.stdout.strip() or "No response."
                
        except Exception as e:
            print(f"Exception: {str(e)}")
            reply = "Failed to execute ZeroClaw."

        # Post reply to Slack
        slack.chat_postMessage(
            channel=channel,
            text=reply
        )

    return {"ok": True}
