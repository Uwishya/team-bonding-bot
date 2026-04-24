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

# YOUR INFO - USING YOUR SLACK USER ID
YOUR_USER_ID = "U0A6W461UFN"
YOUR_TIMEZONE = "Africa/Harare"

# Questions
QUESTIONS = [
    "If you could have dinner with any person (dead or alive), who would it be and why?",
    "What's a small thing that made you smile recently?",
    "What's a skill you'd love to learn and why?",
    "What's your favorite way to unwind after work?",
    "What's a book or movie that changed your perspective?",
]

# Morning messages
MORNING_MESSAGES = [
    "🌞 Good morning! Hope you have a fantastic day ahead!",
    "☀️ Rise and shine! You've got this!",
    "🌅 Good morning! Small steps lead to big results.",
    "💪 Morning! Remember why you started.",
]

# Track if already sent today
last_morning_date = None
last_question_date = None

# Store answers
user_answers = {}

def send_message_to_user(user_id, message):
    """Send a message directly to a user"""
    try:
        app.client.chat_postMessage(channel=user_id, text=message)
        print(f"✅ Message sent to {user_id}")
        return True
    except Exception as e:
        print(f"❌ Error sending to {user_id}: {e}")
        return False

# ============================================
# SLASH COMMANDS - MUST ACKNOWLEDGE IMMEDIATELY
# ============================================

@app.command("/send-morning")
def handle_morning(ack, command, client):
    ack()  # MUST CALL THIS FIRST
    try:
        message = random.choice(MORNING_MESSAGES)
        client.chat_postMessage(channel=YOUR_USER_ID, text=message)
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text=f"✅ Morning greeting sent to you!"
        )
    except Exception as e:
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text=f"❌ Error: {e}"
        )

@app.command("/send-questions")
def handle_question(ack, command, client):
    ack()  # MUST CALL THIS FIRST
    try:
        question = random.choice(QUESTIONS)
        user_answers[YOUR_USER_ID] = {
            "question": question,
            "name": command["user_name"]
        }
        message = f"💭 *Fun question of the day:*\n\n{question}\n\n_Reply with your answer!_"
        client.chat_postMessage(channel=YOUR_USER_ID, text=message)
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text=f"✅ Fun question sent to you!"
        )
    except Exception as e:
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text=f"❌ Error: {e}"
        )

# ============================================
# HANDLE REPLIES
# ============================================

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
            app.client.chat_postMessage(
                channel=user_id,
                text=f"✅ Thanks! Your answer has been shared!"
            )
            del user_answers[user_id]
            print(f"Answer posted for {user_name}")
        except Exception as e:
            print(f"Error: {e}")

# ============================================
# SCHEDULER FOR AUTOMATIC MESSAGES
# ============================================

def send_morning_greeting():
    global last_morning_date
    today = datetime.now().date()
    
    if last_morning_date == today:
        print("Morning already sent today. Skipping.")
        return
    
    if datetime.now().weekday() in [5, 6]:
        print("Weekend. No morning greeting.")
        return
    
    message = random.choice(MORNING_MESSAGES)
    if send_message_to_user(YOUR_USER_ID, message):
        last_morning_date = today
        print(f"✅ Morning greeting sent at {datetime.now()}")

def send_fun_question():
    global last_question_date
    today = datetime.now().date()
    
    if last_question_date == today:
        print("Question already sent today. Skipping.")
        return
    
    if datetime.now().weekday() not in [0, 2, 4]:
        print("Not a question day. Skipping.")
        return
    
    question = random.choice(QUESTIONS)
    user_answers[YOUR_USER_ID] = {
        "question": question,
        "name": "You"
    }
    message = f"💭 *Fun question of the day:*\n\n{question}\n\n_Reply with your answer!_"
    
    if send_message_to_user(YOUR_USER_ID, message):
        last_question_date = today
        print(f"✅ Question sent at {datetime.now()}")

def run_scheduler():
    print("Scheduler started...")
    while True:
        now = datetime.now()
        
        if now.hour == 9 and now.minute == 0:
            send_morning_greeting()
            time.sleep(60)
        
        if now.hour == 11 and now.minute == 25:
            send_fun_question()
            time.sleep(60)
        
        time.sleep(30)

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("🚀 Team Bonding Bot is running!")
    print(f"   Your User ID: {YOUR_USER_ID}")
    print("   Commands: /send-morning , /send-questions")
    
    # Start scheduler
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Start Slack app
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()