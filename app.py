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
from flask import Flask

# ============================================
# INITIALIZATION
# ============================================
load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
WATERCOOLER = os.environ.get("WATERCOOLER_CHANNEL_ID")

TRACKER_FILE = "sent_tracker.json"
PENDING_FILE = "pending_answers.json"

# --- Dummy Web Server for Render's Free Tier ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is alive and running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
# ============================================

# ============================================
# CONTENT LISTS
# ============================================

MOTIVATIONAL_BOOSTS = [
    "🚀 Let's start the week strong and focus on driving real impact!",
    "💡 Innovation thrives on collaboration. Let's make today count!",
    "🌟 Small steps every day lead to massive results for our clients.",
    "💪 Success is built by teams who support each other. You've got this!",
    "✨ Fresh week, fresh opportunities to build something incredible.",
    "🌍 Every piece of code and every conversation helps empower someone somewhere.",
    "🎯 Stay focused, stay curious, and let's win together today!",
    "⚡ Energy and persistence conquer all things. Let's crush it!",
    "🤝 Stronger together, working smarter every single day.",
    "🙌 Finish the week strong! Your hard work makes a huge difference."
]

QUESTIONS = [
    "What’s a recent customer success story or feature milestone that made you proud?",
    "If you had to explain financial inclusion to a 10-year-old, what analogy would you use?",
    "What's one thing about digital financial inclusion that you think more people should know?",
    "What is your absolute favorite shortcut or tool that keeps your remote work day smooth?",
    "If our remote team had a signature theme song for our sync meetings, what should it be?",
    "What's the most rewarding challenge you've tackled since joining DreamStart Labs?",
    "How do you stay connected with our mission when working deeply on technical tasks?",
    "What is one piece of advice you’d give to someone joining a fully remote software team?",
    "Which of our company values (Inclusion, Innovation, Impact) resonated with you most this week?",
    "If you could shadow anyone on the team for a single day to see what they do, who would it be?",
    "If you could have any superpower for 24 hours, what would it be?",
    "What’s the most 'useless' talent you have?",
    "What is the best professional advice you’ve ever received?",
    "If you were forced to eat only one meal for life, what would it be?",
    "What’s your favorite way to 'unplug' after a long day?",
    "What’s the most interesting place you’ve ever visited or lived in?",
    "If you could time travel, would you go to the past or the future?",
    "Are you a 'total silence' or 'background music' person when writing code or documentation?",
    "What is your go-to comfort food on a rainy afternoon?",
    "What’s your favorite thing about your home office or desk setup right now?",
    "What is one thing you think everyone should try at least once in their life?",
    "What’s the most spontaneous thing you’ve ever done?",
    "If you could instantly speak any language fluently, which one would it be?",
    "Do you prefer a crisp morning sunrise or a quiet evening sunset?",
    "What’s the best concert or live performance you’ve ever attended?",
    "What’s a popular trend you are secretly glad is over?",
    "What’s your favorite way to spend a Saturday morning?",
    "What is the best thing that happened to you this week, big or small?",
    "What’s your 'walk-up' song if you were a professional athlete entering a stadium?",
    "What is the strangest food combination you genuinely enjoy?",
    "If you could open a small brick-and-mortar business tomorrow, what would it be?",
    "What’s a movie or book you can quote almost entirely from memory?",
    "What is one thing you are really good at, but absolutely hate doing?"
]

# ============================================
# PERSISTENCE HELPERS
# ============================================

def load_json(filename):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
    except: pass
    return {}

def save_json(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f)
    except Exception as e: print(f"❌ Storage Error: {e}")

# ============================================
# CORE LOGIC
# ============================================

def get_all_team_members():
    try:
        result = app.client.users_list()
        team_members = []
        for user in result["members"]:
            if user["is_bot"] or user["deleted"]: continue
            email = user.get("profile", {}).get("email", "")
            if email.endswith("@dreamstartlabs.com"):
                team_members.append({
                    "id": user["id"],
                    "name": user["real_name"] or user["name"],
                    "tz": user.get("tz", "Africa/Harare")
                })
        return team_members
    except Exception as e:
        print(f"❌ API Error: {e}")
        return []

def send_messages():
    tracker = load_json(TRACKER_FILE)
    pending = load_json(PENDING_FILE)
    members = get_all_team_members()

    for user in members:
        try:
            user_tz = pytz.timezone(user["tz"])
            now_local = datetime.now(user_tz)
            today_str = now_local.date().isoformat()
            
            random.seed(today_str)
            todays_motivation = random.choice(MOTIVATIONAL_BOOSTS)
            todays_question = random.choice(QUESTIONS)
            random.seed(None)

            if user["id"] not in tracker:
                tracker[user["id"]] = {"last_date": "", "question": False, "reminder": False}
            
            if tracker[user["id"]]["last_date"] != today_str:
                tracker[user["id"]].update({
                    "last_date": today_str, 
                    "question": False, 
                    "reminder": False
                })

            # --- BULLETPROOF QUESTION TRIGGER (Anytime after 11:00 AM local time) ---
            if now_local.weekday() in [0, 4] and now_local.hour >= 11:
                if not tracker[user["id"]]["question"]:
                    pending[user["id"]] = {"question": todays_question, "name": user["name"]}
                    
                    combined_text = f"{todays_motivation}\n\n💭 *Today's Question:*\n{todays_question}"
                    app.client.chat_postMessage(channel=user["id"], text=combined_text)
                    
                    tracker[user["id"]]["question"] = True
                    save_json(TRACKER_FILE, tracker)
                    save_json(PENDING_FILE, pending)

            # --- BULLETPROOF REMINDER TRIGGER (Anytime after 3:00 PM / 15h local time) ---
            if now_local.weekday() in [0, 4] and now_local.hour >= 15:
                if user["id"] in pending and not tracker[user["id"]].get("reminder", False):
                    
                    reminder_text = "🔔 *Quick Check-in:* Don't forget to share your answer to today's question! Your colleagues are already chatting in the #watercooler. Just reply directly to this message to join in."
                    app.client.chat_postMessage(channel=user["id"], text=reminder_text)
                    
                    tracker[user["id"]]["reminder"] = True
                    save_json(TRACKER_FILE, tracker)

        except Exception as e: print(f"⚠️ Scheduling Loop Exception: {e}")

@app.event("message")
def handle_answer(message, say):
    user_id = message.get("user")
    if message.get("channel_type") != "im" or message.get("subtype") == "bot_message": return
    
    pending = load_json(PENDING_FILE)
    if user_id in pending:
        answer = message.get("text", "").strip()
        question = pending[user_id]["question"]
        user_name = pending[user_id]["name"]
        
        app.client.chat_postMessage(
            channel=WATERCOOLER, 
            text=f"🎉 *{user_name}* shared an answer:\n\n> *Q:* {question}\n> *A:* {answer}"
        )
        say("✅ Your answer has been shared in the watercooler! Thanks for participating.")
        del pending[user_id]
        save_json(PENDING_FILE, pending)

def run_scheduler():
    schedule.every(2).minutes.do(send_messages)
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    print("🚀 Launching Web Server and Scheduling Loops...")
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()