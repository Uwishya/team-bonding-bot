import os
import random
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
WATERCOOLER = os.environ.get("WATERCOOLER_CHANNEL_ID")

YOUR_USER_ID = "U0A6W461UFN"

# ============================================
# COMMAND HANDLERS - MUST ACKNOWLEDGE FIRST
# ============================================

@app.command("/send-morning")
def handle_morning(ack, command, client):
    ack()  # REQUIRED - tells Slack the command was received
    try:
        client.chat_postMessage(channel=YOUR_USER_ID, text="🌞 Good morning test")
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text="✅ Morning message sent!"
        )
    except Exception as e:
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text=f"❌ Error: {e}"
        )

@app.command("/send-questions")
def handle_question(ack, command, client):
    ack()  # REQUIRED - tells Slack the command was received
    try:
        client.chat_postMessage(channel=YOUR_USER_ID, text="💭 Test question: What's your favorite thing about work?")
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text="✅ Question sent!"
        )
    except Exception as e:
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text=f"❌ Error: {e}"
        )

# ============================================
# KEEP BOT ALIVE
# ============================================

if __name__ == "__main__":
    print("Bot is running...")
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()