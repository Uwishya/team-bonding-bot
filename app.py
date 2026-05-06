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
# 50+ MORNING GREETINGS & QUESTIONS
# ============================================

MORNING_MESSAGES = [
    "🌞 Good morning! Hope you have a fantastic day!",
    "☀️ Rise and shine! You've got this!",
    "✨ New day, new opportunities. Let’s make it amazing!",
    "💪 Good morning team! Time to crush it today!",
    "🚀 Let’s start the day strong and finish stronger!",
    "🌅 Small steps lead to big results. Good morning!",
    "🌻 Sending you positive vibes this morning!",
    "🔥 Ready to do great things today? Let’s go!",
    "🌈 Make today so awesome that yesterday gets jealous!",
    "☕ Morning! I hope your coffee is strong and your Monday is short!",
    "🌟 You are capable of amazing things. Have a great morning!",
    "🍀 Wishing you a day full of productivity and big wins!",
    "🙌 High fives all around—it's a brand new day!",
    "🌊 Ride the wave of productivity today. Good morning!",
    "⚡ Sparkle and shine, it's work time!",
    "🎯 Stay focused and stay awesome today!",
    "🦋 Spread some positivity today. Good morning!",
    "💎 You're a gem! Have a brilliant day ahead!",
    "🎈 Hope your day is as bright as your smile!",
    "🧠 Think big, work hard, and stay kind today.",
    "🦁 Channel your inner lion and conquer the day!",
    "🧗 Keep climbing toward those goals. Good morning!",
    "🥗 Fuel up and feel great today!",
    "🎶 May your day have a productive rhythm!",
    "🏙️ Let's build something great today!",
    "🛠️ Time to get to work and make magic happen!",
    "🍃 Take a deep breath and have a calm, productive morning.",
    "🕯️ Light up the world with your ideas today!",
    "🚲 Keep moving forward. Good morning!",
    "🗺️ Every day is a new adventure. Enjoy this one!",
    "🎨 Create something you're proud of today.",
    "🔋 Fully charged and ready to go? Let's do this!",
    "🧘 Wishing you a mindful and focused morning.",
    "🍍 Stay sweet and keep your head high today!",
    "🤝 Teamwork makes the dream work. Good morning!",
    "🏔️ No mountain is too high today. Let's go!",
    "🍿 Hope your day is a blockbuster success!",
    "🧩 You're a vital piece of this team. Have a great day!",
    "🛸 To infinity and beyond! Have a stellar morning!",
    "⚓ Stay grounded and keep sailing forward.",
    "🧪 Experiment, learn, and grow today!",
    "📣 Just a reminder: You're doing a great job!",
    "🍦 Hope your day is a treat!",
    "🏡 Make yourself at home in your workflow today.",
    "🔑 You hold the key to a successful day!",
    "🎁 Every day is a gift—make the most of this one!",
    "🏁 Start your engines... it's time to shine!",
    "🌍 Let's make a positive impact today!",
    "🌠 Wishing upon a star for your best day yet!",
    "🌤️ The sun is up and so are we. Let's get it!",
    "🥳 Happy morning! Let's make it a celebratory day!"
]

QUESTIONS = [
    "If you could have any superpower for 24 hours, what would it be?",
    "What’s the most 'useless' talent you have that you’re actually proud of?",
    "What is the best professional advice you’ve ever received?",
    "If you were forced to eat only one meal for the rest of your life, what would it be?",
    "What’s your favorite way to 'unplug' after a long day of work?",
    "If you could instantly become an expert in one subject, what would it be?",
    "What was your first-ever job, and what did you learn from it?",
    "What’s the most interesting place you’ve ever visited?",
    "If you could time travel, would you go to the past or the future?",
    "What's a book, movie, or song that changed the way you think?",
    "Are you a 'work in total silence' or a 'music in the background' person?",
    "What is your go-to comfort food on a rainy day?",
    "What’s the best piece of career advice you’ve ever ignored?",
    "If you could have dinner with any historical figure, who would it be?",
    "What’s your favorite thing about your current home office setup?",
    "What is one thing you’ve done that you think everyone should try at least once?",
    "What’s the most spontaneous thing you’ve ever done?",
    "If you could live in any fictional world (book/movie), which one would it be?",
    "What’s the best gift you’ve ever received?",
    "What is your 'guilty pleasure' movie or TV show?",
    "If you could trade places with any animal for a day, which one would it be?",
    "What’s a hobby you’ve always wanted to start but haven’t yet?",
    "What’s your favorite local spot that more people should know about?",
    "If you had to change your first name, what would you pick?",
    "Was there a teacher who had a major impact on your life?",
    "What was your favorite subject in school?",
    "What’s the most used emoji on your phone right now?",
    "If you could win an Olympic medal for any sport (real or fake), what would it be?",
    "What’s your favorite childhood memory?",
    "What is the most underrated movie in your opinion?",
    "If you could only use three apps on your phone, which ones would stay?",
    "What’s your secret for staying productive during a busy week?",
    "If you won the lottery tomorrow, what’s the first 'unnecessary' thing you’d buy?",
    "What’s your favorite board game or card game?",
    "What’s one thing you’re looking forward to this month?",
    "If you could speak any language fluently, which one would you choose?",
    "What’s the most impressive thing you can cook?",
    "Do you prefer sunrise or sunset?",
    "What’s the best concert or live event you’ve ever attended?",
    "If you could be any age again for one week, what age would you choose?",
    "What’s a trend you’re glad is over?",
    "What’s your favorite way to spend a Saturday morning?",
    "What is the best thing that happened to you this week so far?",
    "If you could be a character in any sitcom, who would you be?",
    "What’s your 'walk-up' song if you were a professional athlete?",
    "What is the strangest food combination you actually enjoy?",
    "What’s the one thing you can’t travel without?",
    "If you could open a business tomorrow, what kind of business would it be?",
    "What’s your favorite holiday and why?",
    "What’s a movie you can quote almost entirely?",
    "If you could meet your future self, what one question would you ask?",
    "What is the most beautiful place you have ever seen in person?",
    "What is one thing you are really good at, but you hate doing?",
    "What was the first CD, tape, or record you ever bought?"
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
            today_str = now_local.date().isoformat()
            
            # --- THE "DATE LOCK" SECRET ---
            # We use the current date string as a seed. 
            # This ensures that for this SPECIFIC day, random.choice 
            # always picks the same item no matter when or where it's called.
            random.seed(today_str)
            todays_greeting = random.choice(MORNING_MESSAGES)
            todays_question = random.choice(QUESTIONS)
            # -------------------------------

            if user["id"] not in tracker or tracker[user["id"]].get("date") != today_str:
                tracker[user["id"]] = {"date": today_str, "morning": False, "question": False}

            # --- MORNING (9:00 - 9:05) ---
            if now_local.weekday() < 5 and now_local.hour == 9 and now_local.minute < 5:
                if not tracker[user["id"]]["morning"]:
                    app.client.chat_postMessage(channel=user["id"], text=todays_greeting)
                    tracker[user["id"]]["morning"] = True
                    save_json(TRACKER_FILE, tracker)
                    print(f"🌞 Morning sent to {user['name']}")
                    time.sleep(1.5)

            # --- QUESTION (Mon, Wed, Fri | 11:00 - 11:05) ---
            if now_local.weekday() in [0, 2, 4] and now_local.hour == 11 and now_local.minute < 5:
                if not tracker[user["id"]]["question"]:
                    pending[user["id"]] = {"question": todays_question, "name": user["name"]}
                    
                    app.client.chat_postMessage(
                        channel=user["id"], 
                        text=f"💭 *Today's Team Question:*\n\n{todays_question}\n\n_Reply to this DM to share your answer!_"
                    )
                    
                    tracker[user["id"]]["question"] = True
                    save_json(TRACKER_FILE, tracker)
                    save_json(PENDING_FILE, pending)
                    print(f"💭 Question sent to {user['name']}")
                    time.sleep(1.5)

        except Exception as e:
            print(f"⚠️ User Error ({user['name']}): {e}")
        finally:
            # Reset the random seed so other parts of the app (like random greeting) 
            # don't get stuck if you use random elsewhere later.
            random.seed(None)

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
            say("✅ Your answer has been shared in the watercooler!")
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
    print("🚀 Bot starting with Global Timezone Sync...")
    threading.Thread(target=run_scheduler, daemon=True).start()
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()