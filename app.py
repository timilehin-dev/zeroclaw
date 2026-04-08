import os
import subprocess
import re
from fastapi import FastAPI, Request
from slack_sdk import WebClient

app = FastAPI()

slack = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

def clean_zeroclaw_output(text):
    # Remove ANSI color codes
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    text = ansi_escape.sub('', text)
    
    # Remove system log lines
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        if " INFO " in line or " WARN " in line or " ERROR " in line:
            continue
        if "Config loaded" in line or "Memory initialized" in line:
            continue
        clean_lines.append(line)
    
    return "\n".join(clean_lines).strip()

def format_for_slack(text):
    # Convert Markdown to Slack's "mrkdwn" format
    
    # 1. Headers (# Header) -> Bold (*Header*)
    text = re.sub(r'^#+\s*(.*)', r'*\1*', text, flags=re.MULTILINE)
    
    # 2. Bold (**text**) -> Slack Bold (*text*)
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    
    # 3. Italic (*text*) -> Slack Italic (_text_)
    # We look for single asterisks surrounded by spaces or start/end of line to avoid messing up bold text
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'_\1_', text)
    
    return text

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

            # Combine and clean
            raw_output = result.stdout.strip() + "\n" + result.stderr.strip()
            clean_reply = clean_zeroclaw_output(raw_output)
            
            # Format for Slack
            formatted_reply = format_for_slack(clean_reply)

            if not formatted_reply:
                formatted_reply = "No response."
                
        except Exception as e:
            print(f"Exception: {str(e)}")
            formatted_reply = "Failed to execute ZeroClaw."

        slack.chat_postMessage(
            channel=channel,
            text=formatted_reply
        )

    return {"ok": True}
