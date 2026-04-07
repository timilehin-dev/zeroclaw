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

        # 1. Get Config
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "").rstrip("/")
        ollama_key = os.environ.get("OLLAMA_API_KEY", "")
        # The model you want to use
        model_name = "gemma4:31b-cloud" 

        # 2. Construct Provider String
        provider_str = f"custom:{ollama_url}/v1"

        try:
            # 3. Prepare Environment
            # "custom" provider looks for "CUSTOM_API_KEY"
            run_env = os.environ.copy()
            run_env["CUSTOM_API_KEY"] = ollama_key

            # 4. Run ZeroClaw with explicit Model and Provider
            result = subprocess.run(
                [
                    "zeroclaw", "agent", 
                    "-p", provider_str, 
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
