import os
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# ============================================
# DIAGNOSTIC MODE - PRINTS EVERY CHECK
# ============================================

def run_diagnostic():
    print("=" * 60)
    print("🔍 DIAGNOSTIC MODE STARTED")
    print("   This will log every time check to Railway console")
    print("   Watch the logs to see what the bot is doing")
    print("=" * 60)
    
    last_logged_minute = -1
    condition_trigger_count = 0
    
    while True:
        now = datetime.now()
        current_minute = now.hour * 60 + now.minute
        weekday = now.weekday()
        weekday_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][weekday]
        
        # Log once per minute
        if current_minute != last_logged_minute:
            last_logged_minute = current_minute
            print(f"\n⏰ {now.strftime('%H:%M:%S')} - {weekday_name} (day {weekday})")
        
        # Check morning condition (9:00 AM)
        if now.hour == 9 and now.minute == 0 and now.second == 0:
            condition_trigger_count += 1
            print(f"🔴🔴🔴 MORNING CONDITION TRIGGERED #{condition_trigger_count} at {now.strftime('%H:%M:%S')} 🔴🔴🔴")
            print(f"   Weekday: {weekday_name} - Should send? {'NO (weekend)' if weekday in [5,6] else 'YES'}")
        
        # Check question condition (4:00 PM)
        if now.hour == 16 and now.minute == 0 and now.second == 0:
            condition_trigger_count += 1
            print(f"🔵🔵🔵 QUESTION CONDITION TRIGGERED #{condition_trigger_count} at {now.strftime('%H:%M:%S')} 🔵🔵🔵")
            print(f"   Weekday: {weekday_name} - Should send? {'NO (not Mon/Wed/Fri)' if weekday not in [0,2,4] else 'YES'}")
        
        time.sleep(0.5)

# ============================================
# SIMPLE SCHEDULED MESSAGES - WITH BLOCKING
# ============================================

# Track if already sent (in memory - will reset on restart)
last_morning_date = None
last_question_date = None

def send_morning_if_needed():
    global last_morning_date
    now = datetime.now()
    today = now.date()
    weekday = now.weekday()
    
    # BLOCK WEEKENDS
    if weekday in [5, 6]:
        print(f"🚫 Saturday/Sunday - BLOCKING morning message")
        return
    
    # Already sent today?
    if last_morning_date == today:
        print(f"🚫 Morning already sent today ({today}) - BLOCKING")
        return
    
    # Send the message
    print(f"✅✅✅ SENDING MORNING GREETING at {now} ✅✅✅")
    try:
        app.client.chat_postMessage(
            channel="U0A6W461UFN",
            text="🌞 Good morning! Test message."
        )
        last_morning_date = today
        print(f"✅ Morning message SENT successfully")
    except Exception as e:
        print(f"❌ Error sending morning: {e}")

def send_question_if_needed():
    global last_question_date
    now = datetime.now()
    today = now.date()
    weekday = now.weekday()
    
    # ONLY MON/WED/FRI
    if weekday not in [0, 2, 4]:
        print(f"🚫 Not Mon/Wed/Fri ({weekday}) - BLOCKING question")
        return
    
    # Already sent today?
    if last_question_date == today:
        print(f"🚫 Question already sent today ({today}) - BLOCKING")
        return
    
    # Send the question
    print(f"✅✅✅ SENDING FUN QUESTION at {now} ✅✅✅")
    try:
        app.client.chat_postMessage(
            channel="U0A6W461UFN",
            text="💭 Fun question: What's the best advice you've ever received?"
        )
        last_question_date = today
        print(f"✅ Question SENT successfully")
    except Exception as e:
        print(f"❌ Error sending question: {e}")

def run_scheduler():
    print("🕐 Main scheduler started - checking every second")
    while True:
        now = datetime.now()
        
        # Check at exactly 9:00:00 AM
        if now.hour == 9 and now.minute == 0 and now.second == 0:
            send_morning_if_needed()
            time.sleep(1)  # Prevent multiple triggers in same second
        
        # Check at exactly 4:00:00 PM
        if now.hour == 16 and now.minute == 0 and now.second == 0:
            send_question_if_needed()
            time.sleep(1)
        
        time.sleep(0.5)

# ============================================
# SLASH COMMAND FOR MANUAL TESTING
# ============================================

@app.command("/test-morning")
def test_morning(ack, command, client):
    ack()
    try:
        client.chat_postMessage(channel="U0A6W461UFN", text="🌞 Test morning message")
        client.chat_postEphemeral(channel=command["channel_id"], user=command["user_id"], text="✅ Sent!")
    except Exception as e:
        client.chat_postEphemeral(channel=command["channel_id"], user=command["user_id"], text=f"❌ Error: {e}")

@app.command("/test-question")
def test_question(ack, command, client):
    ack()
    try:
        client.chat_postMessage(channel="U0A6W461UFN", text="💭 Test question: What's your favorite movie?")
        client.chat_postEphemeral(channel=command["channel_id"], user=command["user_id"], text="✅ Sent!")
    except Exception as e:
        client.chat_postEphemeral(channel=command["channel_id"], user=command["user_id"], text=f"❌ Error: {e}")

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 DIAGNOSTIC + WORKING BOT")
    print("   Watching for 9:00 AM and 4:00 PM triggers")
    print("   Commands: /test-morning , /test-question")
    print("=" * 60)
    
    # Start diagnostic scheduler
    threading.Thread(target=run_scheduler, daemon=True).start()
    threading.Thread(target=run_diagnostic, daemon=True).start()
    
    # Start Slack app
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()