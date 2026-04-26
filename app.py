import os
import random
import time
import threading
import json
from datetime import datetime, timedelta, timezone
import pytz
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
WATERCOOLER = os.environ.get("WATERCOOLER_CHANNEL_ID")

LOCAL_TZ = pytz.timezone("Africa/Harare")

# File to track sent messages (persists across restarts)
TRACKER_FILE = "sent_tracker.json"

def load_tracker():
    try:
        with open(TRACKER_FILE, "r") as f:
            return json.load(f)
    except:
        return {"morning_date": None, "question_date": None}

def save_tracker(tracker):
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f)

# ============================================
# MORNING MESSAGES (15+)
# ============================================

MORNING_MESSAGES = [
    "🌞 Good morning! Hope you have a fantastic day!",
    "☀️ Rise and shine! You've got this!",
    "🌅 Small steps lead to big results. Good morning!",
    "💪 Morning! Remember why you started.",
    "🌟 Good morning! Today is full of possibilities.",
    "🌈 Good morning! Your energy makes a difference.",
    "🍃 Good morning! Take a deep breath and go get it.",
    "✨ Good morning! Be the reason someone smiles today.",
    "🌸 Good morning! You are capable of amazing things.",
    "🦋 Good morning! Every day is a fresh start.",
    "⭐ Good morning! Make today your masterpiece.",
    "🌻 Good morning! Your attitude determines your direction.",
    "💫 Good morning! Believe in yourself.",
    "🍀 Good morning! Luck is when preparation meets opportunity.",
    "🎯 Good morning! Focus on what matters today.",
]

# ============================================
# FUN QUESTIONS (25+)
# ============================================

QUESTIONS = [
    "What's a small thing that made you smile recently?",
    "What's a skill you'd love to learn and why?",
    "What's the best advice you've ever received?",
    "What's a book or movie that changed your perspective?",
    "What's your favorite way to unwind after work?",
    "If you could have dinner with anyone (dead or alive), who would it be?",
    "What's something you're grateful for today?",
    "What's a childhood memory that makes you happy?",
    "What's a goal you're working toward right now?",
    "What's a quote that motivates you?",
    "What's something you'd tell your younger self?",
    "What's a tradition from your culture that you love?",
    "What's something you're looking forward to?",
    "What's a fear you've overcome?",
    "What's something that makes you feel proud?",
    "What's something you've learned recently?",
    "What's your favorite season and why?",
    "What's a song that always puts you in a good mood?",
    "What's a random act of kindness you've experienced?",
    "What's something that surprised you this week?",
    "What's a hobby you've always wanted to try?",
    "What's the best meal you've had recently?",
    "What's something that made you laugh this week?",
    "If you could have any superpower, what would it be?",
    "What's something you're excited about for the future?",
]

user_answers = {}

# ============================================
# GET ALL TEAM MEMBERS WITH @dreamstartlabs.com
# ============================================

def get_all_team_members():
    """Get all users with @dreamstartlabs.com email"""
    try:
        users = app.client.users_list()["members"]
        team_members = []
        for user in users:
            if user["is_bot"] or user["deleted"]:
                continue
            try:
                user_info = app.client.users_info(user=user["id"])
                email = user_info["user"]["profile"].get("email", "")
                if email.endswith("@dreamstartlabs.com"):
                    team_members.append({
                        "id": user["id"],
                        "name": user["name"],
                        "email": email,
                        "tz": user.get("tz", "Africa/Kigali")
                    })
            except:
                pass
        print(f"📊 Found {len(team_members)} team members")
        return team_members
    except Exception as e:
        print(f"Error: {e}")
        return []

# ============================================
# SCHEDULE MESSAGE AT USER'S LOCAL TIME
# ============================================

def schedule_message_at_local_time(user_id, user_tz, message, target_hour, target_minute):
    """Schedule a message at the user's local time"""
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
        print(f"Error scheduling for {user_id}: {e}")
        return False

# ============================================
# MORNING GREETINGS (MON-FRI, 9 AM)
# ============================================

def send_morning_to_all():
    tracker = load_tracker()
    now = datetime.now(LOCAL_TZ)
    today = now.date().isoformat()
    weekday = now.weekday()
    
    # NO WEEKENDS
    if weekday in [5, 6]:
        print(f"Saturday/Sunday - No morning messages")
        return
    
    # Already sent today?
    if tracker.get("morning_date") == today:
        print(f"Morning already sent today. Skipping.")
        return
    
    team_members = get_all_team_members()
    message = random.choice(MORNING_MESSAGES)
    count = 0
    
    for user in team_members:
        if schedule_message_at_local_time(user["id"], user["tz"], message, 9, 0):
            count += 1
            print(f"✅ Morning scheduled for {user['name']}")
    
    tracker["morning_date"] = today
    save_tracker(tracker)
    print(f"✅ Morning greetings sent to {count} people")

# ============================================
# FUN QUESTIONS (MON/WED/FRI, 11 AM)
# ============================================

def send_questions_to_all():
    tracker = load_tracker()
    now = datetime.now(LOCAL_TZ)
    today = now.date().isoformat()
    weekday = now.weekday()
    
    # ONLY MON/WED/FRI
    if weekday not in [0, 2, 4]:
        print(f"Not Mon/Wed/Fri - No questions")
        return
    
    # Already sent today?
    if tracker.get("question_date") == today:
        print(f"Questions already sent today. Skipping.")
        return
    
    team_members = get_all_team_members()
    question = random.choice(QUESTIONS)
    count = 0
    
    for user in team_members:
        # Store question to capture answer later
        user_answers[user["id"]] = {
            "question": question,
            "name": user["name"]
        }
        
        message = f"💭 *Fun question of the day:*\n\n{question}\n\n_Reply with your answer!_"
        
        if schedule_message_at_local_time(user["id"], user["tz"], message, 11, 0):
            count += 1
            print(f"✅ Question scheduled for {user['name']}")
    
    tracker["question_date"] = today
    save_tracker(tracker)
    print(f"✅ Questions sent to {count} people")

# ============================================
# HANDLE USER REPLIES
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
                text=f"✅ Thanks! Your answer has been shared in #watercooler!"
            )
            del user_answers[user_id]
            print(f"Answer posted for {user_name}")
        except Exception as e:
            print(f"Error: {e}")

# ============================================
# SCHEDULER
# ============================================

def run_scheduler():
    print("⏰ Scheduler started")
    print("   Morning: Mon-Fri at 9 AM (each user's local time)")
    print("   Question: Mon/Wed/Fri at 11 AM (each user's local time)")
    print("   Target: @dreamstartlabs.com users only")
    print("   ONE message per day | NO duplicates | NO weekends")
    
    while True:
        now = datetime.now(LOCAL_TZ)
        
        # Morning at 9:00 AM
        if now.hour == 9 and now.minute == 0:
            send_morning_to_all()
            time.sleep(60)
        
        # Questions at 11:00 AM
        if now.hour == 11 and now.minute == 0:
            send_questions_to_all()
            time.sleep(60)
        
        time.sleep(10)

# ============================================
# SLASH COMMANDS FOR MANUAL TESTING
# ============================================

@app.command("/send-morning")
def test_morning(ack, command, client):
    ack()
    send_morning_to_all()
    client.chat_postEphemeral(
        channel=command["channel_id"],
        user=command["user_id"],
        text=f"✅ Morning greetings scheduled for everyone!"
    )

@app.command("/send-questions")
def test_questions(ack, command, client):
    ack()
    send_questions_to_all()
    client.chat_postEphemeral(
        channel=command["channel_id"],
        user=command["user_id"],
        text=f"✅ Questions scheduled for everyone!"
    )

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 TEAM BONDING BOT - FINAL VERSION")
    print("   Morning: Mon-Fri at 9 AM (local time)")
    print("   Question: Mon/Wed/Fri at 11 AM (local time)")
    print("   15+ morning messages | 25+ questions")
    print("   Target: @dreamstartlabs.com users only")
    print("   ONE message per day | NO duplicates | NO weekends")
    print("=" * 60)
    
    # Start scheduler
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # Start Slack app
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()