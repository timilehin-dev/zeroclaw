import os
import subprocess
from fastapi import FastAPI, Request
from slack_sdk import WebClient

app = FastAPI()

slack = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

@app.get("/")
def home():
    return {"status": "running"}

@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.json()

    if body.get("type") == "url_verification":
        return {"challenge": body["challenge"]}

    event = body.get("event", {})

    if event.get("type") == "app_mention":
        user_text = event.get("text", "")
        channel = event.get("channel")

        clean_text = user_text.split(" ", 1)[-1] if " " in user_text else user_text

        # 1. Get the Key
        # We use OPENROUTER_API_KEY
        api_key = os.environ.get("OPENROUTER_API_KEY", "")

        # 2. Define the model
        # OpenRouter model names usually look like: google/gemma-2-9b-it
        # You can pick any model from openrouter.ai/models
        model_name = "openrouter/free" 

        try:
            # 3. Prepare Environment
            run_env = os.environ.copy()
            run_env["OPENROUTER_API_KEY"] = api_key

            # 4. Run ZeroClaw with OpenRouter provider
            result = subprocess.run(
                [
                    "zeroclaw", "agent", 
                    "-p", "openrouter",      # Use openrouter provider
                    "--model", model_name, 
                    "-m", clean_text
                ],
                capture_output=True,
                text=True,
                env=run_env
            )

            if result.returncode != 0:
                print(f"ZeroClaw Error: {result.stderr}")
                reply = f"Error: {result.stderr.strip()}"
            else:
                reply = result.stdout.strip() or "No response."
                
        except Exception as e:
            print(f"Exception: {str(e)}")
            reply = "Failed to execute ZeroClaw."

        slack.chat_postMessage(
            channel=channel,
            text=reply
        )

    return {"ok": True}
