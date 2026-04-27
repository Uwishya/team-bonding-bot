import os
import random
import time
import threading
import json
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import schedule

# ============================================
# INITIALIZATION
# ============================================
load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
WATERCOOLER = os.environ.get("WATERCOOLER_CHANNEL_ID")

# Files for persistence - will stay safe on Railway Volume
TRACKER_FILE = "sent_tracker.json"
PENDING_FILE = "pending_answers.json"

cached_members = []
last_fetch_time = None

# ============================================
# STORAGE HELPERS
# ============================================

def load_json(filename):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except:
        pass
    return {}

def save_json(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"❌ Storage Error: {e}")

# ============================================
# MESSAGES
# ============================================

MORNING_MESSAGES = [
    "🌞 Good morning! Hope you have a fantastic day!",
    "☀️ Rise and shine! You've got this!",
    "✨ New day, new opportunities. Let’s make it amazing!",
    "💪 Good morning team! Time to crush it today!",
    "🚀 Let’s start the day strong and finish stronger!",
]

QUESTIONS = [
    "What's a small thing that made you smile recently?",
    "What's a skill you'd love to learn and why?",
    "What's the best advice you've ever received?",
    "What's your favorite meal of all time?",
    "If you could travel anywhere right now, where would you go?",
    "What's one thing you're proud of this week?",
    "What's your hidden talent?",
]

# ============================================
# CORE LOGIC
# ============================================

def get_all_team_members():
    global cached_members, last_fetch_time
    if last_fetch_time and datetime.now() < last_fetch_time + timedelta(minutes=60):
        return cached_members

    try:
        print("🔄 Syncing team list...")
        result = app.client.users_list()
        team_members = []
        for user in result["members"]:
            if user["is_bot"] or user["deleted"]:
                continue
            
            email = user.get("profile", {}).get("email", "")
            if email.endswith("@dreamstartlabs.com"):
                team_members.append({
                    "id": user["id"],
                    "name": user["real_name"] or user["name"],
                    "tz": user.get("tz", "Africa/Harare")
                })
        
        cached_members = team_members
        last_fetch_time = datetime.now()
        print(f"📊 Sync complete: {len(team_members)} members.")
        return team_members
    except Exception as e:
        print(f"❌ API Error: {e}")
        return cached_members 

def send_messages():
    tracker = load_json(TRACKER_FILE)
    pending = load_json(PENDING_FILE)
    members = get_all_team_members()

    for user in members:
        try:
            user_tz = pytz.timezone(user["tz"])
            now_local = datetime.now(user_tz)
            today = now_local.date().isoformat()
            
            # Auto-Clean: If the stored date isn't today, clear that user's record
            if user["id"] in tracker:
                user_record = tracker[user["id"]]
                if user_record.get("date") != today:
                    tracker[user["id"]] = {"date": today, "morning": False, "question": False}

            # Initialize new user in tracker
            if user["id"] not in tracker:
                tracker[user["id"]] = {"date": today, "morning": False, "question": False}

            # --- MORNING (9:00 - 9:05) ---
            if now_local.weekday() < 5 and now_local.hour == 9 and now_local.minute < 5:
                if not tracker[user["id"]]["morning"]:
                    app.client.chat_postMessage(channel=user["id"], text=random.choice(MORNING_MESSAGES))
                    tracker[user["id"]]["morning"] = True
                    save_json(TRACKER_FILE, tracker)
                    print(f"🌞 Morning sent to {user['name']}")
                    time.sleep(1.5)

            # --- QUESTION (Mon, Wed, Fri | 11:00 - 11:05) ---
            if now_local.weekday() in [0, 2, 4] and now_local.hour == 11 and now_local.minute < 5:
                if not tracker[user["id"]]["question"]:
                    question = random.choice(QUESTIONS)
                    pending[user["id"]] = {"question": question, "name": user["name"]}
                    
                    app.client.chat_postMessage(
                        channel=user["id"], 
                        text=f"💭 *Fun question of the day:*\n\n{question}\n\n_Reply to this DM!_"
                    )
                    
                    tracker[user["id"]]["question"] = True
                    save_json(TRACKER_FILE, tracker)
                    save_json(PENDING_FILE, pending)
                    print(f"💭 Question sent to {user['name']}")
                    time.sleep(1.5)

        except Exception as e:
            print(f"⚠️ User Error ({user['name']}): {e}")

# ============================================
# EVENT HANDLER
# ============================================

@app.event("message")
def handle_answer(message, say):
    user_id = message.get("user")
    if message.get("channel_type") != "im" or message.get("subtype") == "bot_message":
        return

    pending = load_json(PENDING_FILE)

    if user_id in pending:
        answer = message.get("text", "").strip()
        question = pending[user_id]["question"]
        user_name = pending[user_id]["name"]

        try:
            app.client.chat_postMessage(
                channel=WATERCOOLER,
                text=f"🎉 *{user_name}* shared an answer:\n\n> *Q:* {question}\n> *A:* {answer}"
            )
            say("✅ Shared in the watercooler!")
            del pending[user_id]
            save_json(PENDING_FILE, pending)
        except Exception as e:
            print(f"❌ Post Error: {e}")

# ============================================
# RUN
# ============================================

def run_scheduler():
    schedule.every(2).minutes.do(send_messages)
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    print("🚀 Bot initializing...")
    threading.Thread(target=run_scheduler, daemon=True).start()
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()