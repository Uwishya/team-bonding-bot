import os
import random
import schedule
import time
import threading
import json
from datetime import datetime, timezone, timedelta
import pytz
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
WATERCOOLER = os.environ.get("WATERCOOLER_CHANNEL_ID")

# File to track sent messages
TRACKER_FILE = "sent_tracker.json"

def load_tracker():
    try:
        with open(TRACKER_FILE, "r") as f:
            return json.load(f)
    except:
        return {"morning_date": None, "questions_date": None}

def save_tracker(tracker):
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f)

# ============================================
# 53 FUN QUESTIONS
# ============================================

QUESTIONS = [
    "If you could have dinner with any person (dead or alive), who would it be and why?",
    "What's the best piece of advice you've ever received?",
    "What's a small thing that made you smile recently?",
    "What's a skill you'd love to learn and why?",
    "What's your favorite way to unwind after work?",
    "What's a book or movie that changed your perspective?",
    "If you could travel anywhere tomorrow, where would you go?",
    "What's something you're grateful for today?",
    "What's a childhood memory that makes you happy?",
    "Who is someone that has inspired you recently?",
    "What's a hobby you've always wanted to try?",
    "What's the best meal you've had recently?",
    "What's something that made you laugh this week?",
    "If you could have any superpower, what would it be?",
    "What's a goal you're working toward right now?",
    "What's a quote that motivates you?",
    "What's something you'd tell your younger self?",
    "What's a tradition from your culture that you love?",
    "What's the best concert or event you've attended?",
    "What's something you're looking forward to?",
    "What's a fear you've overcome?",
    "What's something that makes you feel proud?",
    "What's a place that feels like home to you?",
    "What's something you've learned recently?",
    "What's a random act of kindness you've experienced?",
    "What's your favorite season and why?",
    "What's something that surprised you this week?",
    "What's a song that always puts you in a good mood?",
    "What's something you'd like to be remembered for?",
    "What's a challenge you've overcome at work?",
    "What's something that makes your team great?",
    "What's a project you enjoyed working on?",
    "What's something you appreciate about a colleague?",
    "What's a work habit that helps you stay productive?",
    "What's something you've learned from a teammate?",
    "What's a way you've grown professionally this year?",
    "What's something that motivates you at work?",
    "What's a skill you've developed recently?",
    "What's something you're curious about?",
    "What's a podcast or article you'd recommend?",
    "What's something that made you feel accomplished?",
    "What's a way you've helped someone recently?",
    "What's something that made you feel inspired at work?",
    "What's a small win you've had recently?",
    "What's something you'd like to learn from a colleague?",
    "What's a way you've supported your team?",
    "What's something that makes you feel energized?",
    "What's a feedback you've received that helped you?",
    "What's something you're excited about for the future?",
    "What's your favorite thing about your job?",
    "What's something that made you feel proud this month?",
    "What's a new food you tried and loved?",
    "What's something you're really good at?",
    "What's something you want to improve?",
]

# ============================================
# 31 MORNING MESSAGES
# ============================================

MORNING_MESSAGES = [
    "🌞 Good morning! Hope you have a fantastic day ahead!",
    "☀️ Rise and shine! You've got this!",
    "🌅 Good morning! Small steps lead to big results.",
    "💪 Morning! Remember why you started.",
    "🌟 Good morning! Today is full of possibilities.",
    "🌈 Good morning! Your energy makes a difference.",
    "🍃 Good morning! Take a deep breath and go get it.",
    "✨ Good morning! Be the reason someone smiles today.",
    "🌸 Good morning! You are capable of amazing things.",
    "🦋 Good morning! Every day is a fresh start.",
    "⭐ Good morning! Make today your masterpiece.",
    "🌻 Good morning! Your attitude determines your direction.",
    "💫 Good morning! Believe in yourself and all that you are.",
    "🍀 Good morning! Luck is when preparation meets opportunity.",
    "🎯 Good morning! Focus on what matters today.",
    "💡 Good morning! You have ideas that can change things.",
    "🤝 Good morning! Your teamwork makes a difference.",
    "🏆 Good morning! Every small win adds up.",
    "📈 Good morning! Growth happens outside your comfort zone.",
    "🧠 Good morning! Your mind is your greatest asset.",
    "❤️ Good morning! Lead with kindness today.",
    "🎨 Good morning! You are the author of your story.",
    "🚀 Good morning! Aim high and take the first step.",
    "🏔️ Good morning! The view is better after the climb.",
    "🌊 Good morning! Go with the flow but know your direction.",
    "🔥 Good morning! Bring your passion to work today.",
    "💎 Good morning! Your unique perspective is valuable.",
    "🕊️ Good morning! Peace starts with you.",
    "🎵 Good morning! Find your rhythm and dance through the day.",
    "📚 Good morning! Every day is a chance to learn something new.",
    "🤗 Good morning! Your presence makes this team better.",
]

user_answers = {}

# YOUR INFO - USING YOUR SLACK USER ID DIRECTLY
YOUR_USER_ID = "U0A6W461UFN"
YOUR_NAME = "Uwishya"
YOUR_TIMEZONE = "Africa/Harare"

def schedule_message_for_user(user_id, user_tz, message, target_hour, target_minute=0):
    try:
        user_timezone = pytz.timezone(user_tz)
        now_local = datetime.now(user_timezone)
        target_time = now_local.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if target_time < now_local:
            target_time += timedelta(days=1)
        utc_timestamp = int(target_time.astimezone(timezone.utc).timestamp())
        app.client.chat_scheduleMessage(channel=user_id, text=message, post_at=utc_timestamp)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def send_morning_greetings():
    """TEST MODE: Send morning greeting ONLY TO YOU"""
    tracker = load_tracker()
    today = datetime.now().date().isoformat()
    today_weekday = datetime.now().weekday()
    
    # NO WEEKENDS
    if today_weekday in [5, 6]:
        print(f"Weekend. No morning greetings.")
        return 0
    
    # CHECK IF ALREADY SENT TODAY
    if tracker.get("morning_date") == today:
        print(f"Morning already sent today ({today}). Skipping.")
        return 0
    
    print(f"Sending morning greeting to YOU ({YOUR_NAME})...")
    message = random.choice(MORNING_MESSAGES)
    
    if schedule_message_for_user(YOUR_USER_ID, YOUR_TIMEZONE, message, 9, 0):
        print(f"✅ Morning greeting scheduled for YOU at 9:00 AM")
    else:
        print(f"❌ Failed to schedule morning greeting")
    
    # MARK AS SENT
    tracker["morning_date"] = today
    save_tracker(tracker)
    print(f"Morning greeting sent to 1 person (TEST MODE - only you)")
    return 1

def send_questions_to_all():
    """TEST MODE: Send fun question ONLY TO YOU at 11:40 AM"""
    tracker = load_tracker()
    today = datetime.now().date().isoformat()
    today_weekday = datetime.now().weekday()
    
    # ONLY MON/WED/FRI
    if today_weekday not in [0, 2, 4]:
        print(f"Not Mon/Wed/Fri. No questions.")
        return 0
    
    # CHECK IF ALREADY SENT TODAY
    if tracker.get("questions_date") == today:
        print(f"Questions already sent today ({today}). Skipping.")
        return 0
    
    print(f"Sending fun question to YOU ({YOUR_NAME}) at 11:25 AM...")
    
    question = random.choice(QUESTIONS)
    
    user_answers[YOUR_USER_ID] = {
        "question": question,
        "name": YOUR_NAME
    }
    
    message = f"💭 *Fun question of the day:*\n\n{question}\n\n_Reply with your answer!_"
    
    if schedule_message_for_user(YOUR_USER_ID, YOUR_TIMEZONE, message, 11, 25):
        print(f"✅ Question scheduled for YOU at 11:25 AM")
    else:
        print(f"❌ Failed to schedule question")
    
    # MARK AS SENT
    tracker["questions_date"] = today
    save_tracker(tracker)
    print(f"Question sent to 1 person (TEST MODE - only you)")
    return 1

@app.event("message")
def handle_answer(message, say):
    user_id = message.get("user")
    if message.get("subtype") == "bot_message" or user_id == None:
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
                text=f"Thanks! Your answer has been shared!"
            )
            del user_answers[user_id]
            print(f"Answer posted for {user_name}")
        except Exception as e:
            print(f"Error: {e}")

def run_scheduler():
    print("Scheduler started")
    print("   Morning greetings: Mon-Fri at 9:00 AM (TEST MODE - only you)")
    print("   Fun questions: Mon/Wed/Fri at 11:25 AM (TEST MODE - only you)")
    
    while True:
        now = datetime.now()
        
        # Morning greetings at 9:00 AM
        if now.hour == 9 and now.minute == 0:
            send_morning_greetings()
            time.sleep(60)
        
        # Fun questions at 11:40 AM
        if now.hour == 11 and now.minute == 40:
            send_questions_to_all()
            time.sleep(60)
        
        time.sleep(30)

@app.command("/send-morning")
def test_morning(ack, command, client):
    ack()
    count = send_morning_greetings()
    client.chat_postEphemeral(
        channel=command["channel_id"],
        user=command["user_id"],
        text=f"Morning greeting sent to {count} people (TEST MODE - only you)!"
    )

@app.command("/send-questions")
def test_questions(ack, command, client):
    ack()
    count = send_questions_to_all()
    client.chat_postEphemeral(
        channel=command["channel_id"],
        user=command["user_id"],
        text=f"Questions sent to {count} people (TEST MODE - only you)!"
    )

if __name__ == "__main__":
    print("🚀 Team Bonding Bot is running!")
    print("   Morning greetings: Mon-Fri at 9:00 AM (TEST MODE - ONLY YOU)")
    print("   Fun questions: Mon/Wed/Fri at 11:40 AM (TEST MODE - ONLY YOU)")
    print(f"   Your User ID: {YOUR_USER_ID}")
    print("   No weekends | No duplicates | File-based tracking")
    
    # Run once on startup
    send_morning_greetings()
    
    today_weekday = datetime.now().weekday()
    if today_weekday in [0, 2, 4]:
        send_questions_to_all()
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()