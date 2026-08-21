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
USED_QUESTIONS_FILE = "used_questions.json"

# --- Web Server & Webhook Trigger for Render ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is alive and running!", 200

@flask_app.route('/trigger-send', methods=['GET', 'POST'])
def trigger_send():
    """Endpoint to manually or via cron-job force a message check."""
    try:
        send_messages()
        return "Message check executed successfully!", 200
    except Exception as e:
        return f"Error executing send_messages: {e}", 500

# ============================================
# CONTENT LISTS
# ============================================

MOTIVATIONAL_BOOSTS = [
    "You are a star ⭐!",
    "💡 Thanks for driving innovation and bringing great ideas to the table.",
    "✨ Taking a quick pause to celebrate your continuous impact on our mission!",
    "⭐ Your focus and problem-solving keep moving us forward—thank you!"
]

QUESTIONS = [
    "What’s a recent customer success story or project milestone that made you proud?",
    "If you had to explain financial inclusion to a 10-year-old, what analogy would you use?",
    "What's one aspect of digital financial tools that you think more people should understand?",
    "What is your absolute favorite shortcut or routine that keeps your remote work day smooth?",
    "What's the most rewarding challenge you've tackled since joining DreamStart Labs?",
    "How do you stay connected with our mission during your busy day-to-day tasks?",
    "What is one piece of advice you’d give to someone joining a fully remote, global team?",
    "Which of our company values (Inclusion, Innovation, Impact) resonated with you most recently?",
    "What is the best professional advice you’ve ever received that sticks with you?",
    "What is a common myth or misconception about your specific role or field that you wish people knew?",
    "What’s a problem you solved recently—big or small—that you felt really proud of figuring out?",
    "What’s the most unusual or funny work habit you’ve developed since working remotely?",
    "If you had to delete every app on your phone except for three, which three are keeping their spot?",
    "Are you a 'type out a full paragraph' person or a 'send five short messages in a row' person?",
    "What’s a keyboard shortcut or tech trick you learned that legitimately changed your daily workflow?",
    "If your current project or work style had a video game soundtrack, what kind of music would be playing?",
    "If you could have any superpower for 24 hours to help your productivity, what would it be?",
    "If you were forced to enter a reality TV competition, which one do you think you’d actually have a chance of winning?",
    "If a movie was made about your career journey so far, what genre would it be and who plays you?",
    "If you could instantly teleport to any location for just your 1-hour lunch break today, where are you going?",
    "If you could safely time travel, would you go to the past or the future?",
    "If you were forced to eat only one meal for the rest of your life, what would it be?",
    "What’s your favorite way to completely 'unplug' and recharge after a busy day?",
    "What’s the most interesting place you’ve ever visited or lived in?",
    "If you could teach a 10-minute masterclass on any non-work topic, what would it be?",
    "What’s the best book, podcast, or documentary you’ve consumed recently that stayed with you?"
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
    used_questions = load_json(USED_QUESTIONS_FILE)
    members = get_all_team_members()
    
    server_today_str = datetime.now().date().isoformat()
    
    available_questions = [q for q in QUESTIONS if q not in used_questions]
    
    if not available_questions:
        print("🔄 All questions in the pool have been used! Resetting vault...")
        used_questions = {}
        available_questions = QUESTIONS
        save_json(USED_QUESTIONS_FILE, used_questions)

    random.seed(server_today_str)
    todays_question = random.choice(available_questions)
    random.seed(None)

    for user in members:
        try:
            user_tz = pytz.timezone(user["tz"])
            now_local = datetime.now(user_tz)
            user_today_str = now_local.date().isoformat()

            random.seed(server_today_str)
            todays_motivation = random.choice(MOTIVATIONAL_BOOSTS)
            random.seed(None)

            if user["id"] not in tracker:
                tracker[user["id"]] = {"last_date": "", "question": False, "reminder": False}
            
            if tracker[user["id"]]["last_date"] != user_today_str:
                tracker[user["id"]].update({
                    "last_date": user_today_str, 
                    "question": False, 
                    "reminder": False
                })

            # --- QUESTION WINDOW: Monday/Friday 11:00 AM to 11:30 AM ---
            if now_local.weekday() in [0, 4] and now_local.hour == 11 and now_local.minute < 30:
                if not tracker[user["id"]]["question"]:
                    pending[user["id"]] = {"question": todays_question, "name": user["name"]}
                    
                    combined_text = f"{todays_motivation}\n\n💭 *Today's Question:*\n{todays_question}"
                    app.client.chat_postMessage(channel=user["id"], text=combined_text)
                    
                    tracker[user["id"]]["question"] = True
                    used_questions[todays_question] = user_today_str
                    
                    save_json(TRACKER_FILE, tracker)
                    save_json(PENDING_FILE, pending)
                    save_json(USED_QUESTIONS_FILE, used_questions)
                    
                    print(f"✅ SENT UNIFIED QUESTION TO: {user['name']} ({user['id']}) at {now_local.strftime('%I:%M %p')}")

            # --- REMINDER WINDOW: Monday/Friday 3:00 PM to 3:30 PM ---
            if now_local.weekday() in [0, 4] and now_local.hour == 15 and now_local.minute < 30:
                if user["id"] in pending and not tracker[user["id"]].get("reminder", False):
                    
                    reminder_text = "🔔 *Quick Check-in:* Don't forget to share your answer to today's question! Your colleagues are already chatting in the #watercooler. Just reply directly to this message to join in."
                    app.client.chat_postMessage(channel=user["id"], text=reminder_text)
                    
                    tracker[user["id"]]["reminder"] = True
                    save_json(TRACKER_FILE, tracker)
                    
                    print(f"🔔 SENT REMINDER TO: {user['name']} ({user['id']}) at {now_local.strftime('%I:%M %p')}")

        except Exception as e: 
            print(f"⚠️ Scheduling Loop Exception for {user.get('name', 'Unknown')}: {e}")

# ============================================
# INCOMING SLACK HANDLERS
# ============================================

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

# ============================================
# THREAD RUNNERS
# ============================================

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

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