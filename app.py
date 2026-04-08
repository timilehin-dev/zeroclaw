import os
import subprocess
import re
from fastapi import FastAPI, Request
from slack_sdk import WebClient

app = FastAPI()

slack = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

def clean_zeroclaw_output(text):
    # 1. Remove ANSI color codes (the [32m, [0m stuff)
    # This regex finds escape sequences and removes them
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    text = ansi_escape.sub('', text)
    
    # 2. Remove lines that look like system logs
    # Logs usually contain " INFO ", " WARN ", or start with a timestamp
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        if " INFO " in line or " WARN " in line or " ERROR " in line:
            continue
        # Also skip lines that are purely config/initialization logs
        if "Config loaded" in line or "Memory initialized" in line:
            continue
        clean_lines.append(line)
    
    return "\n".join(clean_lines).strip()

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

        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        # Using a good Gemma model available on OpenRouter
        model_name = "openrouter/free" 

        try:
            run_env = os.environ.copy()
            run_env["OPENROUTER_API_KEY"] = api_key

            result = subprocess.run(
                [
                    "zeroclaw", "agent", 
                    "-p", "openrouter", 
                    "--model", model_name, 
                    "-m", clean_text
                ],
                capture_output=True,
                text=True,
                env=run_env
            )

            # Combine stdout and stderr, then clean
            raw_output = result.stdout.strip() + "\n" + result.stderr.strip()
            reply = clean_zeroclaw_output(raw_output)

            if not reply:
                reply = "No response."
                
        except Exception as e:
            print(f"Exception: {str(e)}")
            reply = "Failed to execute ZeroClaw."

        slack.chat_postMessage(
            channel=channel,
            text=reply
        )

    return {"ok": True}
