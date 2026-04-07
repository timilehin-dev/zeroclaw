from fastapi import FastAPI, Request
import subprocess
import os
from slack_sdk import WebClient

app = FastAPI()

slack = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

@app.get("/")
def home():
    return {"status": "running"}

@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.json()

    # Slack verification step
    if body.get("type") == "url_verification":
        return {"challenge": body["challenge"]}

    event = body.get("event", {})

    if event.get("type") == "app_mention":
        user_text = event.get("text", "")
        channel = event.get("channel")

        # Call ZeroClaw
        result = subprocess.run(
            ["zeroclaw", "run", user_text],
            capture_output=True,
            text=True
        )

        reply = result.stdout.strip() or "No response."

        slack.chat_postMessage(
            channel=channel,
            text=reply
        )

    return {"ok": True}
