import os
import random
import time
import threading
from datetime import datetime
import pytz
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
WATERCOOLER = os.environ.get("WATERCOOLER_CHANNEL_ID")

YOUR_USER_ID = "U0A6W461UFN"
LOCAL_TZ = pytz.timezone("Africa/Harare")

QUESTIONS = [
    "What's a small thing that made you smile recently?",
    "What's a skill you'd love to learn and why?",
]

user_answers = {}
message_sent_today = False  # Track if already sent today

@app.command("/send-questions")
def handle_question(ack, command, client):
    ack()
    question = random.choice(QUESTIONS)
    user_answers[YOUR_USER_ID] = {"question": question, "name": command["user_name"]}
    client.chat_postMessage(channel=YOUR_USER_ID, text=f"💭 {question}\n\n_Reply with your answer!_")
    client.chat_postEphemeral(channel=command["channel_id"], user=command["user_id"], text="✅ Sent!")

@app.event("message")
def handle_answer(message, say):
    user_id = message.get("user")
    if message.get("subtype") == "bot_message" or user_id is None:
        return
    if user_id in user_answers:
        answer = message.get("text", "").strip()
        question = user_answers[user_id]["question"]
        user_name = user_answers[user_id]["name"]
        try:
            app.client.chat_postMessage(
                channel=WATERCOOLER,
                text=f"🎉 *{user_name}* answered:\n\n> *Q:* {question}\n> *A:* {answer}"
            )
            app.client.chat_postMessage(channel=user_id, text="✅ Thanks! Your answer has been shared!")
            del user_answers[user_id]
        except Exception as e:
            print(f"Error: {e}")

# ============================================
# SCHEDULER - SENDS ONE MESSAGE AT 1:00 PM
# ============================================

def run_scheduler():
    global message_sent_today
    print(f"⏰ Scheduler started - will send ONE test message at 1:00 PM your time")
    
    while True:
        now = datetime.now(LOCAL_TZ)
        
        # Send at 1:00 PM (only once per day)
        if now.hour == 13 and now.minute == 0 and not message_sent_today:
            print(f"🔴 1:00 PM reached! Sending ONE message...")
            question = random.choice(QUESTIONS)
            try:
                app.client.chat_postMessage(
                    channel=YOUR_USER_ID,
                    text=f"🧪 **TEST at 1:00 PM**\n\n💭 {question}\n\n_Reply with your answer!_"
                )
                message_sent_today = True
                print(f"✅ ONE message sent at {now}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        time.sleep(1)

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("⏰ BOT WILL SEND ONE TEST MESSAGE AT 1:00 PM")
    print("   Your timezone: Africa/Harare")
    print("   ONE message only (no duplicates)")
    print("=" * 50)
    
    # Start scheduler
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # Start Slack app
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()