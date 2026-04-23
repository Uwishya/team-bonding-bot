import os
import random
import schedule
import time
import threading
from datetime import datetime, timezone, timedelta
import pytz
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Load tokens from .env file
load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
WATERCOOLER = os.environ.get("WATERCOOLER_CHANNEL_ID")

# Track sent messages (prevent duplicates)
sent_morning = set()
sent_questions = set()

# ============================================
# 50+ FUN QUESTIONS
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
# 30+ MORNING MESSAGES
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

# ============================================
# STORE USER ANSWERS
# ============================================

user_answers = {}

# ============================================
# GET TARGET USERS (ONLY @dreamstartlabs.com)
# ============================================

def get_target_users():
    try:
        users = app.client.users_list()["members"]
        target_users = []
        
        for user in users:
            if user["is_bot"] or user["deleted"]:
                continue
            
            try:
                user_info = app.client.users_info(user=user["id"])
                email = user_info["user"]["profile"].get("email", "")
                tz = user.get("tz", "Africa/Kigali")
                
                if email.endswith("@dreamstartlabs.com"):
                    target_users.append({
                        "id": user["id"],
                        "name": user["name"],
                        "email": email,
                        "tz": tz
                    })
                    print(f"✅ INCLUDED: {user['name']} ({email}) - Timezone: {tz}")
            except:
                pass
        
        print(f"📊 Total team members: {len(target_users)}")
        return target_users
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

# ============================================
# SCHEDULE MESSAGE AT LOCAL TIME
# ============================================

def schedule_message_for_user(user_id, user_tz, message, target_hour, target_minute=0):
    try:
        user_timezone = pytz.timezone(user_tz)
        now_local = datetime.now(user_timezone)
        
        target_time = now_local.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        
        if target_time < now_local:
            target_time += timedelta(days=1)
        
        utc_timestamp = int(target_time.astimezone(timezone.utc).timestamp())
        
        app.client.chat_scheduleMessage(
            channel=user_id,
            text=message,
            post_at=utc_timestamp
        )
        return True
    except Exception as e:
        print(f"❌ Error scheduling for {user_id}: {e}")
        return False

# ============================================
# MORNING GREETINGS (EVERY DAY)
# ============================================

def send_morning_greetings():
    try:
        target_users = get_target_users()
        message = random.choice(MORNING_MESSAGES)
        today = datetime.now().date()
        count = 0
        
        for user in target_users:
            user_id = user["id"]
            
            if f"{user_id}_{today}" in sent_morning:
                continue
            
            if schedule_message_for_user(user["id"], user["tz"], message, 9, 0):
                sent_morning.add(f"{user_id}_{today}")
                count += 1
                print(f"✅ Scheduled morning greeting for {user['name']}")
        
        print(f"✅ Scheduled morning greetings for {count} people")
        return count
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

# ============================================
# FUN QUESTIONS (ONLY MON, WED, FRI)
# ============================================

def send_questions_to_all():
    """Send fun questions ONLY on Monday, Wednesday, Friday"""
    try:
        # Check if today is Monday (0), Wednesday (2), or Friday (4)
        today_weekday = datetime.now().weekday()
        if today_weekday not in [0, 2, 4]:
            print(f"📅 Today is day {today_weekday}. No fun questions today (only Mon=0, Wed=2, Fri=4)")
            return 0
        
        target_users = get_target_users()
        question = random.choice(QUESTIONS)
        today = datetime.now().date()
        count = 0
        
        for user in target_users:
            user_id = user["id"]
            user_name = user["name"]
            user_tz = user["tz"]
            
            if f"{user_id}_{today}" in sent_questions:
                continue
            
            user_answers[user_id] = {
                "question": question,
                "name": user_name
            }
            
            message = f"💭 *Fun question of the day:*\n\n{question}\n\n_Reply with your answer and I'll share it with the team!_"
            
            if schedule_message_for_user(user_id, user_tz, message, 11, 0):
                sent_questions.add(f"{user_id}_{today}")
                count += 1
                print(f"✅ Scheduled fun question for {user_name}")
        
        print(f"✅ Scheduled questions for {count} people")
        return count
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

# ============================================
# HANDLE USER REPLIES
# ============================================

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
                text=f"✅ Thanks! Your answer has been shared in the watercooler channel!"
            )
            
            del user_answers[user_id]
            print(f"✅ Answer posted for {user_name}")
        except Exception as e:
            print(f"❌ Error posting answer: {e}")

# ============================================
# SCHEDULER
# ============================================

def run_scheduler():
    def clear_trackers():
        global sent_morning, sent_questions
        sent_morning.clear()
        sent_questions.clear()
        print("🔄 Daily trackers cleared")
    
    schedule.every().day.at("00:01").do(clear_trackers)
    schedule.every().day.at("00:02").do(send_morning_greetings)
    schedule.every().monday.at("00:03").do(send_questions_to_all)
    schedule.every().wednesday.at("00:03").do(send_questions_to_all)
    schedule.every().friday.at("00:03").do(send_questions_to_all)
    
    print("⏰ Scheduler started!")
    print("   Morning greetings: Daily at each user's local 9 AM")
    print("   Fun questions: Monday, Wednesday, Friday at each user's local 11 AM")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# ============================================
# SLASH COMMANDS
# ============================================

@app.command("/send-morning")
def test_morning(ack, command, client):
    ack()
    count = send_morning_greetings()
    client.chat_postEphemeral(
        channel=command["channel_id"],
        user=command["user_id"],
        text=f"✅ Morning greetings scheduled for {count} people!"
    )

@app.command("/send-questions")
def test_questions(ack, command, client):
    ack()
    count = send_questions_to_all()
    client.chat_postEphemeral(
        channel=command["channel_id"],
        user=command["user_id"],
        text=f"✅ Fun questions scheduled for {count} people!"
    )

# ============================================
# RUN THE BOT
# ============================================

if __name__ == "__main__":
    print("🚀 Team Bonding Bot is running!")
    print("   Morning greetings: Daily at each user's local 9 AM")
    print("   Fun questions: Monday, Wednesday, Friday at each user's local 11 AM")
    print("   Target: @dreamstartlabs.com users only")
    print(f"   Watercooler channel: {WATERCOOLER}")
    
    print("\n📅 Scheduling today's messages...")
    send_morning_greetings()
    
    # Only send questions on Mon, Wed, Fri
    today = datetime.now().weekday()
    if today in [0, 2, 4]:
        send_questions_to_all()
    else:
        print(f"📅 Today is day {today}. No fun questions today (only Mon=0, Wed=2, Fri=4)")
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()