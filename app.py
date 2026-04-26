import os
import time
import threading
import json
from datetime import datetime
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Diagnostic tracker file
TRACKER_FILE = "diagnostic_log.json"

def log_event(event):
    """Log every event to a file"""
    try:
        with open(TRACKER_FILE, "r") as f:
            log = json.load(f)
        log["events"].append({
            "timestamp": datetime.now().isoformat(),
            "event": event
        })
        with open(TRACKER_FILE, "w") as f:
            json.dump(log, f, indent=2)
    except:
        log = {"events": [{"timestamp": datetime.now().isoformat(), "event": event}]}
        with open(TRACKER_FILE, "w") as f:
            json.dump(log, f, indent=2)
    
    print(f"📝 LOGGED: {event} at {datetime.now()}")

# ============================================
# DIAGNOSTIC SCHEDULER - LOGS EVERYTHING
# ============================================

def run_diagnostic():
    print("🔍 DIAGNOSTIC MODE - LOGGING EVERYTHING")
    print("   This will show what the bot is actually doing")
    
    last_minute = -1
    
    while True:
        now = datetime.now()
        current_minute = now.hour * 60 + now.minute
        weekday = now.weekday()
        
        # Log once per minute
        if current_minute != last_minute:
            last_minute = current_minute
            log_event(f"CHECK: {now.strftime('%H:%M')} - Weekday: {weekday}")
            print(f"🔍 CHECK at {now.strftime('%H:%M')} - Weekday: {weekday}")
        
        # Check morning condition
        if now.hour == 9 and now.minute == 0:
            log_event("MORNING CONDITION MET - 9:00 AM")
            print("⚠️ MORNING CONDITION MET - would send message")
        
        # Check question condition
        if now.hour == 16 and now.minute == 0:
            log_event("QUESTION CONDITION MET - 4:00 PM")
            print("⚠️ QUESTION CONDITION MET - would send message")
        
        time.sleep(1)

@app.command("/diagnostic")
def diagnostic(ack, command, client):
    ack()
    try:
        with open(TRACKER_FILE, "r") as f:
            log = json.load(f)
        summary = f"Total events logged: {len(log['events'])}\n\nLast 5 events:\n"
        for event in log['events'][-5:]:
            summary += f"- {event['timestamp']}: {event['event']}\n"
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text=f"```{summary}```"
        )
    except:
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text="No diagnostic data yet. Wait a few minutes."
        )

if __name__ == "__main__":
    print("=" * 50)
    print("🔍 DIAGNOSTIC MODE - RUNNING")
    print("   Logging every condition check to diagnostic_log.json")
    print("   Use /diagnostic command to see logs")
    print("=" * 50)
    
    # Start diagnostic
    threading.Thread(target=run_diagnostic, daemon=True).start()
    
    # Start Slack app
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()