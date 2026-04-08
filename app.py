import os
import subprocess
import re
from fastapi import FastAPI, Request
from slack_sdk import WebClient

app = FastAPI()

slack = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

# --- Helper Functions ---

def clean_zeroclaw_output(text):
    # Remove ANSI color codes
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    text = ansi_escape.sub('', text)
    
    # Remove system log lines
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        if " INFO " in line or " WARN " in line or " ERROR " in line: continue
        if "Config loaded" in line or "Memory initialized" in line: continue
        clean_lines.append(line)
    return "\n".join(clean_lines).strip()

def format_for_slack(text):
    # Convert Markdown headers (# Header) to Slack Bold (*Header*)
    text = re.sub(r'^#+\s*(.*)', r'*\1*', text, flags=re.MULTILINE)
    # Convert Markdown Bold (**text**) to Slack Bold (*text*)
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    # Convert Markdown Italic (*text*) to Slack Italic (_text_)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'_\1_', text)
    return text

def run_agent(prompt, provider_config):
    """
    Runs ZeroClaw with a specific provider configuration.
    Returns: (success_boolean, output_string)
    """
    # Prepare environment for this specific provider
    run_env = os.environ.copy()
    
    # Set the API Key for this provider
    # ZeroClaw 'custom' provider looks for CUSTOM_API_KEY
    run_env["CUSTOM_API_KEY"] = provider_config["key"]
    
    # Construct the provider string
    # e.g., "custom:https://aihubmix.com/v1"
    provider_str = f"custom:{provider_config['base_url']}"

    try:
        result = subprocess.run(
            [
                "zeroclaw", "agent",
                "-p", provider_str,
                "--model", provider_config["model"],
                "-m", prompt
            ],
            capture_output=True,
            text=True,
            env=run_env,
            timeout=120 # 2 minute timeout
        )

        raw_output = result.stdout.strip() + "\n" + result.stderr.strip()
        clean_output = clean_zeroclaw_output(raw_output)

        # Check for Rate Limits or specific API errors in the output
        # ZeroClaw usually returns these in the stderr or stdout combined
        if "rate limit" in clean_output.lower() or "429" in clean_output:
            return False, f"Rate limit hit for {provider_config['name']}."
        
        if result.returncode != 0 and not clean_output:
             return False, "Unknown error occurred."

        return True, clean_output

    except subprocess.TimeoutExpired:
        return False, "Request timed out."
    except Exception as e:
        return False, str(e)

# --- Main App ---

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

        # --- Define Providers (Priority Order) ---
        providers = [
            {
                "name": "AIHubMix (Mimo)",
                "base_url": "https://aihubmix.com/v1",
                "model": "mimo-v2-flash-free", # Or your specific model
                "key": os.environ.get("AIHUBMIX_API_KEY", "")
            },
            {
                "name": "OpenRouter (Gemma)",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "google/gemma-2-9b-it",
                "key": os.environ.get("OPENROUTER_API_KEY", "")
            }
        ]

        final_reply = "All providers failed to respond."

        # --- Try each provider ---
        for provider in providers:
            if not provider["key"]:
                # Skip if API key is missing in env vars
                continue

            print(f"Trying provider: {provider['name']}...")
            success, output = run_agent(clean_text, provider)

            if success:
                final_reply = format_for_slack(output)
                break # Success! Stop trying other providers.
            else:
                print(f"Failed on {provider['name']}: {output}")
                # If it failed, the loop continues to the next provider
        
        slack.chat_postMessage(channel=channel, text=final_reply)

    return {"ok": True}
