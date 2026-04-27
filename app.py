import os
import random
import time
import threading
import json
from datetime import datetime
import pytz
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import schedule

# ============================================
# LOAD ENVIRONMENT VARIABLES
# ============================================

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
WATERCOOLER = os.environ.get("WATERCOOLER_CHANNEL_ID")

# Files to persist data (Use Railway Volumes to keep these across restarts)
TRACKER_FILE = "sent_tracker.json"
PENDING_FILE = "pending_answers.json"

# ============================================
# STORAGE HELPERS
# ============================================

def load_json(filename):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
    return {}

def save_json(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

# ============================================
# MESSAGES
# ============================================

MORNING_MESSAGES = [
    "🌞 Good morning! Hope you have a fantastic day!",
    "☀️ Rise and shine! You've got this!",
    "✨ New day, new opportunities. Let’s make it amazing!",
    "💪 Good morning team! Time to crush it today!",
    "🚀 Let’s start the day strong and finish stronger!",
    "😊 Wishing you a productive and joyful day ahead!",
    "🔥 Ready to do great things today? Let’s go!",
]

QUESTIONS = [
    "What's a small thing that made you smile recently?",
    "What's a skill you'd love to learn and why?",
    "What's the best advice you've ever received?",
    "What's your favorite meal of all time?",
    "If you could travel anywhere right now, where would you go?",
    "What's one thing you're proud of this week?",
    "Coffee or tea — and why?",
    "What's your dream job as a kid?",
    "What's one app you can't live without?",
    "What's your favorite weekend activity?",
]

# ============================================
# LOGIC & RATE LIMITING
# ============================================

def get_all_team_members():
    """Fetches all users once to avoid rate limits."""
    try:
        result = app.client.users_list()
        team_members = []
        for user in result["members"]:
            if user["is_bot"] or user["deleted"] or user["is_app_user"]:
                continue
            
            profile = user.get("profile", {})
            email = profile.get("email", "")
            
            if email.endswith("@dreamstartlabs.com"):
                team_members.append({
                    "id": user["id"],
                    "name": user["real_name"] or user["name"],
                    "tz": user.get("tz", "Africa/Harare")
                })
        print(f"📊 Total team members found: {len(team_members)}")
        return team_members
    except Exception as e:
        print(f"❌ Error fetching users: {e}")
        return []

def send_morning_to_all():
    tracker = load_json(TRACKER_FILE)
    team_members = get_all_team_members()

    for user in team_members:
        try:
            user_tz = pytz.timezone(user["tz"])
            now_local = datetime.now(user_tz)
            today = now_local.date().isoformat()

            if now_local.weekday() >= 5: continue 

            if tracker.get(user["id"], {}).get("morning") == today:
                continue

            if now_local.hour == 9 and now_local.minute < 10:
                message = random.choice(MORNING_MESSAGES)
                app.client.chat_postMessage(channel=user["id"], text=message)
                
                if user["id"] not in tracker: tracker[user["id"]] = {}
                tracker[user["id"]]["morning"] = today
                save_json(TRACKER_FILE, tracker) # Save immediately per user
                
                print(f"🌞 Morning sent to {user['name']}")
                time.sleep(1.2) # PACE: Slack Tier 2 is ~20-50/min. 1.2s is safe.

        except Exception as e:
            print(f"Error in morning loop for {user['name']}: {e}")

def send_questions_to_all():
    tracker = load_json(TRACKER_FILE)
    pending = load_json(PENDING_FILE)
    team_members = get_all_team_members()

    for user in team_members:
        try:
            user_tz = pytz.timezone(user["tz"])
            now_local = datetime.now(user_tz)
            today = now_local.date().isoformat()

            # Mon, Wed, Fri only
            if now_local.weekday() not in [0, 2, 4]: continue

            if tracker.get(user["id"], {}).get("question") == today:
                continue

            if now_local.hour == 11 and now_local.minute < 10:
                question = random.choice(QUESTIONS)
                pending[user["id"]] = {"question": question, "name": user["name"]}
                
                message = f"💭 *Fun question of the day:*\n\n{question}\n\n_Reply directly to this DM to share your answer!_"
                app.client.chat_postMessage(channel=user["id"], text=message)

                if user["id"] not in tracker: tracker[user["id"]] = {}
                tracker[user["id"]]["question"] = today
                
                # Save state as we go
                save_json(TRACKER_FILE, tracker)
                save_json(PENDING_FILE, pending)
                
                print(f"💭 Question sent to {user['name']}")
                time.sleep(1.2) # PACE: Avoid "ratelimited" error

        except Exception as e:
            print(f"Error in question loop for {user['name']}: {e}")

# ============================================
# SLACK EVENTS (REPLIES)
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
            say("✅ Thanks! Your answer is now in the watercooler.")
            
            del pending[user_id]
            save_json(PENDING_FILE, pending)
        except Exception as e:
            print(f"Error posting answer: {e}")

# ============================================
# SCHEDULER & RUNTIME
# ============================================

def run_scheduler():
    # Every 5 mins, check if we are in the 9am or 11am windows
    schedule.every(5).minutes.do(send_morning_to_all)
    schedule.every(5).minutes.do(send_questions_to_all)
    
    print("⏰ Scheduler is active.")
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    print("🚀 Team Bonding Bot starting...")
    
    # Run scheduler in background
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # Start Slack App
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()