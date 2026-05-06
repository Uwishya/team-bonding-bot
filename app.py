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

# Files stored locally (Temporary memory without Volume)
TRACKER_FILE = "sent_tracker.json"
PENDING_FILE = "pending_answers.json"

# ============================================
# CONTENT LISTS (50+ Greetings & 50+ Questions)
# ============================================

MORNING_MESSAGES = [
    "🌞 Good morning! Hope you have a fantastic day!", "☀️ Rise and shine! You've got this!",
    "✨ New day, new opportunities. Let’s make it amazing!", "💪 Good morning team! Time to crush it today!",
    "🚀 Let’s start the day strong and finish stronger!", "🌅 Small steps lead to big results.",
    "🌻 Sending you positive vibes!", "🔥 Ready to do great things today?",
    "🌈 Make today awesome!", "☕ Morning! Hope your coffee is strong!",
    "🌟 You are capable of amazing things!", "🍀 Wishing you a productive day!",
    "🙌 High fives all around—it's a brand new day!", "🌊 Ride the wave of productivity.",
    "⚡ Sparkle and shine, it's work time!", "🎯 Stay focused and awesome today!",
    "🦋 Spread some positivity.", "💎 You're a gem!",
    "🎈 Hope your day is bright!", "🧠 Think big, work hard, and stay kind.",
    "🦁 Channel your inner lion!", "🧗 Keep climbing toward those goals.",
    "🎶 May your day have a productive rhythm!", "🏙️ Let's build something great!",
    "🛠️ Time to make magic happen!", "🍃 Take a deep breath and have a calm morning.",
    "🕯️ Light up the world with your ideas!", "🚲 Keep moving forward.",
    "🎨 Create something you're proud of.", "🔋 Fully charged and ready to go!",
    "🧘 Wishing you a focused morning.", "🍍 Stay sweet and keep your head high!",
    "🤝 Teamwork makes the dream work!", "🏔️ No mountain is too high.",
    "🍿 Hope your day is a blockbuster!", "🧩 You're a vital piece of this team.",
    "🛸 To infinity and beyond!", "⚓ Stay grounded and keep sailing.",
    "🧪 Experiment, learn, and grow!", "📣 You're doing a great job!",
    "🍦 Hope your day is a treat!", "🏡 Enjoy your workflow today.",
    "🔑 You hold the key to a successful day!", "🎁 Every day is a gift!",
    "🏁 Start your engines!", "🌍 Let's make a positive impact!",
    "🌠 Wishing for your best day yet!", "🌤️ The sun is up and so are we.",
    "🥳 Happy morning! Let's celebrate the day!"
]

QUESTIONS = [
    "If you could have any superpower for 24 hours, what would it be?",
    "What’s the most 'useless' talent you have?",
    "What is the best professional advice you’ve ever received?",
    "If you were forced to eat only one meal for life, what would it be?",
    "What’s your favorite way to 'unplug'?",
    "If you could instantly become an expert in one subject, what would it be?",
    "What was your first-ever job, and what did you learn?",
    "What’s the most interesting place you’ve ever visited?",
    "If you could time travel, would you go to the past or the future?",
    "What's a book, movie, or song that changed your thinking?",
    "Are you a 'total silence' or 'background music' person?",
    "What is your go-to comfort food on a rainy day?",
    "What’s the best piece of career advice you’ve ever ignored?",
    "If you could have dinner with any historical figure, who would it be?",
    "What’s your favorite thing about your home office setup?",
    "What is one thing everyone should try at least once?",
    "What’s the most spontaneous thing you’ve ever done?",
    "If you could live in any fictional world, which one would it be?",
    "What’s the best gift you’ve ever received?",
    "What is your 'guilty pleasure' movie or TV show?",
    "If you could trade places with any animal, which one would it be?",
    "What’s a hobby you’ve always wanted to start?",
    "What’s your favorite local spot?",
    "If you had to change your first name, what would it be?",
    "Was there a teacher who had a major impact on you?",
    "What was your favorite subject in school?",
    "What’s the most used emoji on your phone right now?",
    "If you could win an Olympic medal for any sport, what would it be?",
    "What’s your favorite childhood memory?",
    "What is the most underrated movie?",
    "If you could only use three apps, which ones would stay?",
    "What’s your secret for staying productive?",
    "If you won the lottery, what’s the first 'unnecessary' thing you’d buy?",
    "What’s your favorite board game?",
    "What’s one thing you’re looking forward to this month?",
    "If you could speak any language fluently, which one would it be?",
    "What’s the most impressive thing you can cook?",
    "Do you prefer sunrise or sunset?",
    "What’s the best concert you’ve ever attended?",
    "If you could be any age again for one week, what age would it be?",
    "What’s a trend you’re glad is over?",
    "What’s your favorite way to spend a Saturday morning?",
    "What is the best thing that happened to you this week?",
    "If you could be a character in any sitcom, who would it be?",
    "What’s your 'walk-up' song if you were a pro athlete?",
    "What is the strangest food combination you enjoy?",
    "What’s the one thing you can’t travel without?",
    "If you could open a business tomorrow, what would it be?",
    "What’s your favorite holiday and why?",
    "What’s a movie you can quote almost entirely?",
    "If you could meet your future self, what one question would you ask?",
    "What is the most beautiful place you have ever seen?",
    "What is one thing you are really good at, but hate doing?",
    "What was the first album you ever bought?"
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
            
            # Global Seed Logic
            random.seed(today_str)
            todays_greeting = random.choice(MORNING_MESSAGES)
            todays_question = random.choice(QUESTIONS)
            random.seed(None)

            if user["id"] not in tracker:
                tracker[user["id"]] = {"last_date": "", "morning": False, "question": False}
            
            if tracker[user["id"]]["last_date"] != today_str:
                tracker[user["id"]].update({"last_date": today_str, "morning": False, "question": False})

            # Morning Greeting (9:00 AM)
            if now_local.weekday() < 5 and now_local.hour == 9 and now_local.minute < 5:
                if not tracker[user["id"]]["morning"]:
                    app.client.chat_postMessage(channel=user["id"], text=todays_greeting)
                    tracker[user["id"]]["morning"] = True
                    save_json(TRACKER_FILE, tracker)

            # Question (11:00 AM - Mon, Wed, Fri)
            if now_local.weekday() in [0, 2, 4] and now_local.hour == 11 and now_local.minute < 5:
                if not tracker[user["id"]]["question"]:
                    pending[user["id"]] = {"question": todays_question, "name": user["name"]}
                    app.client.chat_postMessage(channel=user["id"], text=f"💭 *Today's Question:*\n\n{todays_question}")
                    tracker[user["id"]]["question"] = True
                    save_json(TRACKER_FILE, tracker)
                    save_json(PENDING_FILE, pending)

            # --- THE REMAINDER (3:00 PM - Mon, Wed, Fri) ---
            if now_local.weekday() in [0, 2, 4] and now_local.hour == 15 and now_local.minute < 5:
                if user["id"] in pending:
                    app.client.chat_postMessage(
                        channel=user["id"], 
                        text="🔔 *Friendly Nudge:* Don't forget to share your answer! Others are already chatting in the #watercooler. Just reply here to join."
                    )

        except Exception as e: print(f"⚠️ Error: {e}")

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
    threading.Thread(target=run_scheduler, daemon=True).start()
    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()