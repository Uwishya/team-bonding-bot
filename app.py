import os
import random
import time
import threading
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

# Initialize Slack client
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
client = WebClient(token=SLACK_BOT_TOKEN)

# YOUR INFO - USING YOUR SLACK USER ID
YOUR_USER_ID = "U0A6W461UFN"
YOUR_TIMEZONE = "Africa/Harare"

# Questions
QUESTIONS = [
    "If you could have dinner with any person (dead or alive), who would it be and why?",
    "What's a small thing that made you smile recently?",
    "What's a skill you'd love to learn and why?",
    "What's your favorite way to unwind after work?",
]

# Morning messages
MORNING_MESSAGES = [
    "🌞 Good morning! Hope you have a fantastic day ahead!",
    "☀️ Rise and shine! You've got this!",
    "🌅 Good morning! Small steps lead to big results.",
]

# Track if already sent today
last_morning_date = None
last_question_date = None

def send_message_to_user(user_id, message):
    """Send a message directly to a user"""
    try:
        result = client.chat_postMessage(channel=user_id, text=message)
        print(f"✅ Message sent to {user_id}")
        return True
    except SlackApiError as e:
        print(f"❌ Error sending to {user_id}: {e.response['error']}")
        return False

def send_morning_greeting():
    global last_morning_date
    today = datetime.now().date()
    
    if last_morning_date == today:
        print("Morning already sent today. Skipping.")
        return
    
    # Check if weekend (Saturday=5, Sunday=6)
    if datetime.now().weekday() in [5, 6]:
        print("Weekend. No morning greeting.")
        return
    
    message = random.choice(MORNING_MESSAGES)
    if send_message_to_user(YOUR_USER_ID, message):
        last_morning_date = today
        print(f"✅ Morning greeting sent to you at {datetime.now()}")

def send_fun_question():
    global last_question_date
    today = datetime.now().date()
    
    if last_question_date == today:
        print("Question already sent today. Skipping.")
        return
    
    # Only Monday (0), Wednesday (2), Friday (4)
    if datetime.now().weekday() not in [0, 2, 4]:
        print("Not a question day (Mon/Wed/Fri). Skipping.")
        return
    
    question = random.choice(QUESTIONS)
    message = f"💭 *Fun question of the day:*\n\n{question}\n\n_Reply with your answer!_"
    
    if send_message_to_user(YOUR_USER_ID, message):
        last_question_date = today
        print(f"✅ Question sent to you at {datetime.now()}")

def run_scheduler():
    print("Scheduler started. Will check every 30 seconds...")
    while True:
        now = datetime.now()
        
        # Morning greeting at 9:00 AM
        if now.hour == 9 and now.minute == 0:
            send_morning_greeting()
            time.sleep(60)  # Avoid multiple triggers
        
        # Fun question at 11:50 AM
        if now.hour == 11 and now.minute == 50:
            send_fun_question()
            time.sleep(60)
        
        time.sleep(30)

if __name__ == "__main__":
    print("🚀 Team Bonding Bot - TEST MODE (Only You)")
    print(f"   Your User ID: {YOUR_USER_ID}")
    print("   Morning greeting: Mon-Fri at 9:00 AM")
    print("   Fun question: Mon/Wed/Fri at 11:50 AM")
    
    # Start the scheduler
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Keep the bot running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Bot stopped.")