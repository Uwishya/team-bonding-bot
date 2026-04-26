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

MORNING_MESSAGES = [
    "🌞 Good morning! Hope you have a fantastic day!",
    "☀️ Rise and shine! You've got this!",
]

QUESTIONS = [
    "What's a small thing that made you smile recently?",
    "What's a skill you'd love to learn and why?",
]

# Tracking
last_morning_date = None
last_question_date = None
last_morning_minute = None
last_question_minute = None

user_answers = {}

# ============================================
# COMMAND HANDLERS
# ============================================

@app.command("/send-morning")
def handle_morning(ack, command, client):
    ack()
    msg = random.choice(MORNING_MESSAGES)
    client.chat_postMessage(channel=YOUR_USER_ID, text=msg)
    client.chat_postEphemeral(channel=command["channel_id"], user=command["user_id"], text="✅ Sent!")

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
# TEST SCHEDULER - SENDS AT 12:00 PM
# ============================================

def check_and_send():
    global last_morning_date, last_question_date, last_morning_minute, last_question_minute
    
    now = datetime.now()
    today = now.date()
    weekday = now.weekday()
    current_minute = now.hour * 60 + now.minute
    
    # TEST: Send at 12:00 PM (NOON) - Sunday is fine for testing
    if now.hour == 12:
        if last_question_minute != current_minute:
            last_question_minute = current_minute
            print(f"🔴 TEST TRIGGER at {now.strftime('%H:%M:%S')}")
            
            question = random.choice(QUESTIONS)
            user_answers[YOUR_USER_ID] = {"question": question, "name": "TestUser"}
            app.client.chat_postMessage(
                channel=YOUR_USER_ID, 
                text=f"🧪 **TEST MESSAGE** at {now.strftime('%H:%M:%S')}\n\n💭 {question}\n\n_Reply with your answer!_"
            )
            print(f"✅ Test message sent")

def run_scheduler():
    print("🕐 TEST SCHEDULER - Will send at 12:00 PM")
    print("   Checking every second...")
    while True:
        try:
            check_and_send()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(1)

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("🧪 TEST MODE")
    print("   Bot will send a test message at 12:00 PM")
    print("   Commands still work: /send-morning , /send-questions")
    print("=" * 50)
    
    # Start scheduler
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # Start Slack app
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()