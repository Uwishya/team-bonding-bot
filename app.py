import os
import re
import json
import random
import logging
import threading
import hmac
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from supabase import create_client, Client


# ============================================================
# 1. PRODUCTION CONFIGURATION
# ============================================================

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SCHEDULER_SECRET = os.getenv("SCHEDULER_SECRET")
WATERCOOLER_CHANNEL_ID = os.getenv("WATERCOOLER_CHANNEL_ID")
SHOUTOUT_ANCHOR_DATE = os.getenv("SHOUTOUT_ANCHOR_DATE", "2026-11-06")
TIMEZONE = ZoneInfo("Africa/Kigali")

REQUIRED_VARIABLES = {
    "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
    "SLACK_APP_TOKEN": SLACK_APP_TOKEN,
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY,
    "SCHEDULER_SECRET": SCHEDULER_SECRET,
    "WATERCOOLER_CHANNEL_ID": WATERCOOLER_CHANNEL_ID,
}
missing = [key for key, value in REQUIRED_VARIABLES.items() if not value]
if missing:
    raise ValueError("Missing environment variables: " + ", ".join(missing))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("watercooler")
app = App(token=SLACK_BOT_TOKEN)
flask_app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
STATE_LOCK = threading.RLock()


# ============================================================
# 2. CONTENT BANKS (preserved from the tested version)
# ============================================================

MONDAY_QUESTIONS = [
    "What's a recent customer success story or project milestone that made you proud?",
    "If you had to explain financial inclusion to a 10-year-old, what analogy would you use?",
    "What's one aspect of digital financial tools that you think more people should understand?",
    "What is one routine or tool that makes your remote workday smoother?",
    "What's the most rewarding challenge you've tackled recently?",
    "How do you stay connected to our mission during your busy day-to-day tasks?",
    "What advice would you give someone joining a fully remote, global team?",
    "Which company value — Inclusion, Innovation or Impact — has resonated with you recently, and why?",
    "What is the best professional advice you've ever received?",
    "What's a common misconception about your role that you wish colleagues understood?",
    "What's a problem you solved recently that made you proud?",
    "What is one thing we could improve in how we collaborate across teams?",
    "What helps you stay motivated when work becomes demanding?",
    "What is one skill you would like to develop this year?",
    "What information or support would help you do your job more effectively?",
    "What is something another team or colleague does that makes your work easier?",
    "What is one process you think we could simplify?",
    "What is one lesson you've learned from working with our partners or customers?",
    "What is one thing you think our team should celebrate more often?",
    "If you could change one thing about our team's way of working, what would it be?",
]

FRIDAY_QUESTIONS = [
    "What's the most unusual or funny work habit you've developed while working remotely?",
    "If you had to delete every app on your phone except three, which three would survive?",
    "Are you a person who sends one long message or five short messages in a row?",
    "If your work style had a video game soundtrack, what kind of music would be playing?",
    "If you could have any superpower for 24 hours, what would it be?",
    "If you had to compete in a reality TV show, which one would you choose?",
    "If a movie were made about your life, what genre would it be?",
    "If you could teleport anywhere for your lunch break, where would you go?",
    "If you could safely time travel, would you visit the past or the future?",
    "If you had to eat one meal for the rest of your life, what would it be?",
    "What's your favourite way to unplug and recharge after a busy day?",
    "What's the most interesting place you've ever visited?",
    "If you could teach a 10-minute masterclass on a non-work topic, what would it be?",
    "What's the best book, podcast or documentary you've enjoyed recently?",
    "What song can instantly improve your mood?",
    "If you could wake up tomorrow with a new talent, what would you choose?",
    "What's one thing you've always wanted to try but haven't yet?",
    "If you could spend a month anywhere in the world, where would you go?",
    "What's the funniest thing that has happened to you recently?",
    "Would you rather have unlimited free travel or unlimited free food?",
    "If you could meet any famous person, living or historical, who would it be?",
    "What's a childhood memory that still makes you smile?",
    "If you opened a business tomorrow, what kind of business would it be?",
    "What's one small thing that can turn a bad day into a good one?",
    "If you could instantly become an expert at anything, what would you choose?",
]

MONDAY_POLLS = [
    {"question": "What helps you do your best work?", "options": ["Clear priorities", "Good teamwork", "Flexibility", "Regular feedback"]},
    {"question": "Which area would most improve our teamwork?", "options": ["Communication", "Planning", "Knowledge sharing", "Collaboration"]},
    {"question": "How do you prefer to receive feedback?", "options": ["One-on-one conversations", "Written feedback", "Team discussions", "A combination"]},
    {"question": "What motivates you most at work?", "options": ["Making an impact", "Learning and growth", "Recognition", "Achieving goals"]},
    {"question": "What helps you stay focused?", "options": ["A clear to-do list", "Quiet working time", "Short breaks", "Team accountability"]},
    {"question": "Which type of team interaction do you value most?", "options": ["Team meetings", "One-on-one check-ins", "Informal conversations", "Written updates"]},
    {"question": "What would help you grow professionally?", "options": ["Mentorship", "Training opportunities", "New responsibilities", "Constructive feedback"]},
    {"question": "How do you prefer to start your workweek?", "options": ["Planning my priorities", "Reviewing ongoing tasks", "Connecting with colleagues", "Starting with the most urgent task"]},
    {"question": "What is most important for successful remote teamwork?", "options": ["Trust", "Communication", "Accountability", "Flexibility"]},
    {"question": "Which area deserves more knowledge sharing?", "options": ["Products and technology", "Customer and partner insights", "Operations and processes", "Team experiences"]},
    {"question": "What makes a meeting valuable?", "options": ["Clear agenda", "Useful decisions", "Everyone participating", "Short and focused discussion"]},
    {"question": "When facing a challenge, what do you usually do first?", "options": ["Research the solution", "Ask a colleague", "Try different approaches", "Break it into smaller tasks"]},
    {"question": "Which recognition means the most to you?", "options": ["A personal thank-you", "Public appreciation", "Career opportunities", "Positive feedback"]},
    {"question": "What would make cross-team collaboration easier?", "options": ["Clear ownership", "Better information sharing", "More coordination", "Shared goals"]},
    {"question": "What do you value most in a team culture?", "options": ["Respect and trust", "Learning and growth", "Open communication", "Support and recognition"]},
]

FRIDAY_POLLS = [
    {"question": "Which would you choose for a perfect weekend?", "options": ["Travelling", "Relaxing at home", "Going out with friends", "Trying something new"]},
    {"question": "Which superpower would you choose?", "options": ["Teleportation", "Time travel", "Reading minds", "Invisibility"]},
    {"question": "What's your ideal Friday evening?", "options": ["Movie night", "Dinner with friends", "Music and relaxation", "Going somewhere new"]},
    {"question": "Which holiday would you prefer?", "options": ["Beach vacation", "Mountain adventure", "City exploration", "Safari experience"]},
    {"question": "If you could only listen to one music genre, what would it be?", "options": ["R&B", "Afrobeats", "Hip-hop", "Gospel"]},
    {"question": "Which would you rather have?", "options": ["Free flights for life", "Free meals for life", "A dream house", "Unlimited shopping"]},
    {"question": "What is your preferred way to travel?", "options": ["Road trip", "Flying", "Train journey", "Boat or cruise"]},
    {"question": "Which fictional world would you visit?", "options": ["Harry Potter", "Marvel Universe", "Disney World", "Jurassic Park"]},
    {"question": "Which would you choose for a day off?", "options": ["Sleeping in", "Exploring somewhere", "Spending time with family", "Going on an adventure"]},
    {"question": "Which food could you eat repeatedly without getting bored?", "options": ["Pizza", "Rice dishes", "Grilled food", "Pasta"]},
    {"question": "Which describes you best at a party?", "options": ["The dancer", "The conversationalist", "The observer", "The person who leaves early"]},
    {"question": "Would you rather speak every language or play every instrument?", "options": ["Speak every language", "Play every instrument"]},
    {"question": "Which pet would you prefer?", "options": ["Dog", "Cat", "Bird", "No pets"]},
    {"question": "What would you choose for a spontaneous adventure?", "options": ["A road trip", "A surprise flight", "A hiking trip", "A food tour"]},
    {"question": "Which would you rather give up for a month?", "options": ["Social media", "Coffee or tea", "Watching TV", "Online shopping"]},
]

MOTIVATIONAL_BOOSTS = [
    "You are a star ⭐!",
    "💡 Thanks for driving innovation and bringing great ideas to the table.",
    "✨ Taking a quick pause to celebrate your continuous impact on our mission!",
    "⭐ Your focus and problem-solving keep moving us forward—thank you!",
    "Your work matters, even when the results aren't immediately visible.",
    "Every meaningful achievement starts with a small step. Keep going!",
    "You bring something valuable to this team that nobody else can replace.",
    "Progress is not always loud. Sometimes it is simply showing up and doing your best.",
    "Your ideas have the power to make a difference. Don't hold them back.",
    "A little consistency can lead to extraordinary results.",
    "The effort you put in today helps create better outcomes tomorrow.",
    "Your contribution is part of something bigger. Thank you for being here.",
    "Challenges are opportunities to discover what you're capable of.",
    "Keep learning, keep improving, and keep bringing your perspective to the table.",
    "Great teams are built by people who care about the work and each other.",
    "You don't have to have everything figured out to make meaningful progress.",
    "Your willingness to learn is one of your greatest strengths.",
    "The small things you do consistently can create a big impact.",
    "Your perspective matters. Your voice deserves to be heard.",
    "Let's make room for fresh ideas and better possibilities this week.",
    "Remember to recognise how far you've come, not just how far you have to go.",
    "Good work deserves appreciation, and your efforts do not go unnoticed.",
    "A positive attitude doesn't remove challenges, but it helps us face them.",
    "You are capable of more than you sometimes give yourself credit for.",
    "Take pride in the effort, the learning, and the progress.",
    "One thoughtful action can make someone's entire day better.",
    "Keep bringing your curiosity, creativity, and commitment.",
    "The mission moves forward because people like you make it happen.",
    "Give yourself credit for the work you do behind the scenes.",
    "Let's approach the week with purpose, openness, and a little optimism.",
]


# ============================================================
# 3. DATABASE HELPERS AND CONTENT ROTATION
# ============================================================

def db_select_one(table, **filters):
    query = supabase.table(table).select("*")
    for key, value in filters.items():
        query = query.eq(key, value)
    result = query.limit(1).execute()
    return result.data[0] if result.data else None


def db_update(table, filters, values):
    query = supabase.table(table).update(values)
    for key, value in filters.items():
        query = query.eq(key, value)
    return query.execute()


def get_campaign_by_id(campaign_id):
    return db_select_one("campaigns", id=campaign_id)


def get_delivery(campaign_id, user_id):
    return db_select_one(
        "campaign_deliveries",
        campaign_id=campaign_id,
        slack_user_id=user_id
    )


def get_response(campaign_id, user_id, response_type):
    return db_select_one(
        "campaign_responses",
        campaign_id=campaign_id,
        slack_user_id=user_id,
        response_type=response_type
    )


def make_content_key(item):
    if isinstance(item, str):
        return item
    return json.dumps(item, ensure_ascii=False, sort_keys=True)


def choose_rotating_item(items, category):
    if not items:
        raise ValueError(f"No content available for {category}")

    used_result = (
        supabase.table("used_content")
        .select("content_key")
        .eq("content_type", category)
        .execute()
    )
    used = {row["content_key"] for row in (used_result.data or [])}
    available = [item for item in items if make_content_key(item) not in used]

    if not available:
        supabase.table("used_content").delete().eq(
            "content_type", category
        ).execute()
        available = list(items)

    selected = random.choice(available)
    supabase.table("used_content").insert({
        "content_type": category,
        "content_key": make_content_key(selected)
    }).execute()
    return selected


def shoutouts_enabled(campaign_date):
    try:
        campaign_day = date.fromisoformat(str(campaign_date))
        anchor_day = date.fromisoformat(SHOUTOUT_ANCHOR_DATE)
    except (TypeError, ValueError):
        logger.exception("Invalid campaign or shout-out anchor date.")
        return False
    days_between = (campaign_day - anchor_day).days
    return days_between >= 0 and days_between % 14 == 0


# ============================================================
# 4. CAMPAIGN CREATION
# ============================================================

def get_campaign(day_name, campaign_date=None):
    if day_name not in ("monday", "friday"):
        raise ValueError("Invalid campaign day.")

    campaign_date = campaign_date or datetime.now(TIMEZONE).date().isoformat()
    parsed_date = date.fromisoformat(campaign_date)
    if parsed_date.isoweekday() != (1 if day_name == "monday" else 5):
        raise ValueError(f"{campaign_date} is not a {day_name.title()}.")

    existing = (
        supabase.table("campaigns")
        .select("*")
        .eq("campaign_date", campaign_date)
        .eq("campaign_type", day_name)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    question_bank, poll_bank = (
        (MONDAY_QUESTIONS, MONDAY_POLLS)
        if day_name == "monday"
        else (FRIDAY_QUESTIONS, FRIDAY_POLLS)
    )
    activity_type = random.choice(["question", "poll"])
    question = None
    poll = None

    if activity_type == "question":
        question = choose_rotating_item(question_bank, f"{day_name}_questions")
    else:
        poll = choose_rotating_item(poll_bank, f"{day_name}_polls")

    motivation = choose_rotating_item(MOTIVATIONAL_BOOSTS, "motivational_messages")

    result = supabase.table("campaigns").insert({
        "campaign_date": campaign_date,
        "campaign_type": day_name,
        "activity_type": activity_type,
        "question": question,
        "poll_question": poll["question"] if poll else None,
        "poll_options": poll["options"] if poll else None,
        "motivation": motivation,
        "status": "sent"
    }).execute()

    if not result.data:
        raise RuntimeError("Supabase did not return the created campaign.")
    return result.data[0]


def campaign_to_payload(row):
    activity_type = row.get("activity_type")
    if activity_type not in ("question", "poll"):
        raise ValueError("Campaign has an invalid activity_type.")

    payload = {
        "campaign_id": str(row["id"]),
        "day": row["campaign_type"],
        "date": row["campaign_date"],
        "activity_type": activity_type,
        "motivation": row.get("motivation") or "",
        "shoutouts_enabled": (
            row["campaign_type"] == "friday"
            and shoutouts_enabled(row["campaign_date"])
        ),
    }
    if activity_type == "question":
        if not row.get("question"):
            raise ValueError("Question campaign has no question.")
        payload["question"] = row["question"]
    else:
        if not row.get("poll_question") or not row.get("poll_options"):
            raise ValueError("Poll campaign has no question or options.")
        payload["poll"] = {
            "question": row["poll_question"],
            "options": row["poll_options"]
        }
    return payload


# ============================================================
# 5. SLACK HELPERS AND MESSAGE FORMATTING
# ============================================================

def escape_slack_text(value):
    return (
        str(value).replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def send_dm(user_id, message, blocks=None):
    conversation = app.client.conversations_open(users=user_id)
    channel_id = conversation["channel"]["id"]
    arguments = {"channel": channel_id, "text": message}
    if blocks:
        arguments["blocks"] = blocks
    return app.client.chat_postMessage(**arguments)


def get_channel_members():
    """Return active human members of the configured Watercooler channel."""
    member_ids = set()
    cursor = None
    while True:
        args = {"channel": WATERCOOLER_CHANNEL_ID, "limit": 200}
        if cursor:
            args["cursor"] = cursor
        response = app.client.conversations_members(**args)
        member_ids.update(response.get("members", []))
        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    human_ids = []
    cursor = None
    while True:
        args = {"limit": 200}
        if cursor:
            args["cursor"] = cursor
        response = app.client.users_list(**args)
        for user in response.get("members", []):
            if (
                user.get("id") in member_ids
                and not user.get("is_bot")
                and not user.get("deleted")
                and user.get("id") != app.client.auth_test()["user_id"]
            ):
                human_ids.append(user["id"])
        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    return sorted(set(human_ids))


def build_campaign_blocks(campaign):
    day_name = campaign["day"]
    if day_name == "monday":
        heading = "🌱 TEAM PULSE"
        introduction = "A new week is here! "
    else:
        heading = "🎉 FRIDAY FUN"
        introduction = "Happy Friday, everyone! "

    opening = introduction + escape_slack_text(campaign.get("motivation") or "")
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": heading, "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": opening}},
    ]

    if campaign["activity_type"] == "question":
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": (
                "*💬 Today's question*\n"
                + escape_slack_text(campaign["question"])
                + "\n\n_Reply to this DM. Your answer will be shared "
                  "automatically in the Watercooler channel._"
            )}
        })
    elif campaign["activity_type"] == "poll":
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": (
                "📊 *Today's poll is now in the Watercooler channel.*\n"
                "Vote there using the buttons below the poll. "
                "Your individual vote is private, and you can change it."
            )}
        })
    else:
        raise ValueError("Unknown campaign activity type.")

    if campaign.get("shoutouts_enabled"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": (
                "👏 *Shout-outs are open this Friday!*\n"
                "To appreciate a colleague, send a separate DM beginning with:\n"
                "`Shoutout: Colleague's name — reason for appreciation`\n"
                "Your shout-out will be shared in the Watercooler channel."
            )}
        })
    return blocks


# ============================================================
# 6. POLL MESSAGE IN WATERCOOLER CHANNEL
# ============================================================

def get_poll_vote_counts(campaign_id, options):
    result = (
        supabase.table("poll_votes")
        .select("option_index")
        .eq("campaign_id", campaign_id)
        .execute()
    )
    counts = [0] * len(options)
    for vote in result.data or []:
        try:
            index = int(vote["option_index"])
            if 0 <= index < len(counts):
                counts[index] += 1
        except (KeyError, TypeError, ValueError):
            logger.warning("Ignoring malformed poll vote row.")
    return counts


def build_channel_poll_blocks(campaign):
    poll = campaign["poll"]
    options = poll["options"]
    if not options or len(options) > 5:
        raise ValueError("Slack polls must contain between one and five options.")
    counts = get_poll_vote_counts(campaign["campaign_id"], options)

    return [
        {"type": "header", "text": {"type": "plain_text", "text": "📊 WATERCOOLER POLL", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": (
            f"*{escape_slack_text(poll['question'])}*\n"
            "_Cast your vote below. Your individual choice is private. "
            "You can change your vote at any time._"
        )}},
        {"type": "actions", "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": str(option), "emoji": True},
                "action_id": f"watercooler_poll_vote_{index}",
                "value": json.dumps({"campaign_id": campaign["campaign_id"], "option_index": index})
            }
            for index, option in enumerate(options)
        ]},
        {"type": "section", "text": {"type": "mrkdwn", "text": (
            "*Current results*\n" + "\n".join(
                f"• {escape_slack_text(option)} — {counts[index]} "
                f"{'vote' if counts[index] == 1 else 'votes'}"
                for index, option in enumerate(options)
            )
        )}},
        {"type": "context", "elements": [{
            "type": "mrkdwn",
            "text": "Only aggregate totals are shown. Individual votes are private."
        }]}
    ]


def publish_or_update_channel_poll(campaign):
    campaign_id = campaign["campaign_id"]
    row = get_campaign_by_id(campaign_id)
    if not row:
        raise RuntimeError("Cannot find campaign for channel poll.")
    blocks = build_channel_poll_blocks(campaign)
    text = f"Watercooler poll: {campaign['poll']['question']}"
    existing_ts = row.get("poll_message_ts")
    existing_channel = row.get("poll_channel_id") or WATERCOOLER_CHANNEL_ID

    if existing_ts:
        return app.client.chat_update(
            channel=existing_channel, ts=existing_ts, text=text, blocks=blocks
        )

    response = app.client.chat_postMessage(
        channel=WATERCOOLER_CHANNEL_ID, text=text, blocks=blocks
    )
    message_ts = response.get("ts")
    if not message_ts:
        raise RuntimeError("Slack did not return a timestamp for the poll.")
    db_update("campaigns", {"id": campaign_id}, {
        "poll_message_ts": message_ts,
        "poll_channel_id": WATERCOOLER_CHANNEL_ID
    })
    return response


def update_channel_poll_results(campaign_id):
    row = get_campaign_by_id(campaign_id)
    if not row or not row.get("poll_message_ts"):
        logger.warning("Poll message timestamp is missing for %s", campaign_id)
        return
    campaign = campaign_to_payload(row)
    if campaign["activity_type"] == "poll":
        publish_or_update_channel_poll(campaign)


# ============================================================
# 7. CAMPAIGN DELIVERY TO ALL CHANNEL MEMBERS
# ============================================================

def create_or_get_delivery(campaign_id, user_id, campaign):
    existing = get_delivery(campaign_id, user_id)
    if existing:
        return existing

    question_status = "awaiting" if campaign["activity_type"] == "question" else "done"
    shoutout_status = "awaiting" if campaign.get("shoutouts_enabled") else "not_applicable"

    result = supabase.table("campaign_deliveries").insert({
        "campaign_id": campaign_id,
        "slack_user_id": user_id,
        "question_status": question_status,
        "shoutout_status": shoutout_status
    }).execute()
    if not result.data:
        raise RuntimeError(f"Could not create delivery for Slack user {user_id}.")
    return result.data[0]


def send_campaign(day_name, campaign_date=None):
    if day_name not in ("monday", "friday"):
        raise ValueError("Choose monday or friday.")

    campaign_row = get_campaign(day_name, campaign_date)
    campaign = campaign_to_payload(campaign_row)
    campaign_id = campaign["campaign_id"]

    if campaign["activity_type"] == "poll":
        publish_or_update_channel_poll(campaign)

    recipients = get_channel_members()
    if not recipients:
        raise RuntimeError("No human members found in the Watercooler channel.")

    sent_count = 0
    skipped_count = 0
    failed = []

    for user_id in recipients:
        try:
            existing = get_delivery(campaign_id, user_id)
            if existing and existing.get("sent_at"):
                skipped_count += 1
                continue

            delivery = create_or_get_delivery(campaign_id, user_id, campaign)
            send_dm(
                user_id,
                f"{day_name.title()} Watercooler campaign",
                build_campaign_blocks(campaign)
            )
            db_update("campaign_deliveries", {"id": delivery["id"]}, {
                "sent_at": datetime.now(timezone.utc).isoformat()
            })
            sent_count += 1
        except Exception as exc:
            logger.exception("Campaign delivery failed for Slack user %s", user_id)
            failed.append({"user_id": user_id, "error": str(exc)[:300]})

    logger.info(
        "Campaign %s on %s: sent=%s skipped=%s failed=%s",
        day_name, campaign["date"], sent_count, skipped_count, len(failed)
    )
    return {
        "campaign_id": campaign_id,
        "activity_type": campaign["activity_type"],
        "shoutouts_enabled": campaign["shoutouts_enabled"],
        "recipients_found": len(recipients),
        "sent": sent_count,
        "skipped_already_sent": skipped_count,
        "failed": failed
    }


# ============================================================
# 8. ACTIVE DELIVERY LOOKUP
# ============================================================

def get_latest_active_delivery(user_id):
    result = (
        supabase.table("campaign_deliveries")
        .select("*")
        .eq("slack_user_id", user_id)
        .order("sent_at", desc=True)
        .limit(30)
        .execute()
    )
    for delivery in result.data or []:
        if not delivery.get("sent_at"):
            continue
        campaign = get_campaign_by_id(delivery["campaign_id"])
        if not campaign:
            continue
        question_active = delivery.get("question_status") == "awaiting"
        shoutout_active = delivery.get("shoutout_status") == "awaiting"
        if question_active or shoutout_active:
            return delivery, campaign
    return None, None


# ============================================================
# 9. AUTOMATIC CONTRIBUTION PUBLISHING
# ============================================================

def publish_contribution(user_id, campaign, delivery, kind, contribution):
    campaign_id = str(campaign["id"])
    existing = get_response(campaign_id, user_id, kind)

    if existing:
        if existing["share_status"] == "shared":
            send_dm(user_id, "Your contribution has already been shared. Thank you! 💙")
            return
        if existing["share_status"] == "approved":
            send_dm(user_id, "Your contribution is already being processed. Please wait.")
            return
        if existing["share_status"] != "pending":
            send_dm(user_id, "A contribution has already been recorded.")
            return
        response = existing
    else:
        inserted = supabase.table("campaign_responses").insert({
            "campaign_id": campaign_id,
            "slack_user_id": user_id,
            "response_type": kind,
            "response_text": contribution,
            "share_status": "pending"
        }).execute()
        if not inserted.data:
            raise RuntimeError("Could not save the contribution.")
        response = inserted.data[0]

    supabase.table("campaign_responses").update({
        "share_status": "approved"
    }).eq("id", response["id"]).eq("share_status", "pending").execute()

    latest = get_response(campaign_id, user_id, kind)
    if not latest or latest["share_status"] != "approved":
        send_dm(user_id, "Your contribution is already being processed.")
        return
    contribution = latest["response_text"]

    if kind == "question":
        channel_text = (
            "*Watercooler contribution:*\n\n"
            f"*Q:* {escape_slack_text(campaign['question'])}\n"
            f"*A:* {escape_slack_text(contribution)}"
        )
    elif kind == "shoutout":
        channel_text = "👏 *Friday shout-out:*\n\n" + escape_slack_text(contribution)
    else:
        raise ValueError("Invalid contribution type.")

    try:
        app.client.chat_postMessage(
            channel=WATERCOOLER_CHANNEL_ID, text=channel_text, mrkdwn=True
        )
    except Exception:
        logger.exception("Could not publish contribution to Watercooler.")
        supabase.table("campaign_responses").update({
            "share_status": "pending"
        }).eq("id", response["id"]).execute()
        send_dm(
            user_id,
            "I couldn't publish your contribution just now. "
            "Your response is saved. Please send it again to retry."
        )
        return

    supabase.table("campaign_responses").update({
        "share_status": "shared"
    }).eq("id", response["id"]).execute()
    status_field = "question_status" if kind == "question" else "shoutout_status"
    db_update("campaign_deliveries", {"id": delivery["id"]}, {status_field: "done"})
    send_dm(user_id, "Thank you! Your contribution has been shared in the Watercooler channel. 💙")
    logger.info("Contribution published: %s | %s | %s", campaign_id, user_id, kind)


# ============================================================
# 10. PRIVATE MESSAGE HANDLING
# ============================================================

def handle_message(event, client, logger):
    user_id = event.get("user")
    if not user_id or event.get("channel_type") != "im":
        return
    if event.get("subtype") or event.get("bot_id"):
        return
    answer = (event.get("text") or "").strip()
    if not answer:
        return

    with STATE_LOCK:
        delivery, campaign = get_latest_active_delivery(user_id)
        if not delivery or not campaign:
            send_dm(user_id, "There is no active Watercooler campaign awaiting a response.")
            return

        day_name = campaign["campaign_type"]
        is_shoutout = bool(re.match(r"^\s*Shoutout\s*:", answer, re.IGNORECASE))

        if is_shoutout:
            if day_name != "friday":
                send_dm(user_id, "Shout-outs are only available during Friday Fun.")
                return
            if delivery.get("shoutout_status") != "awaiting":
                send_dm(user_id, "Shout-outs are not open for this Friday.")
                return
            contribution = re.sub(r"^\s*Shoutout\s*:\s*", "", answer, flags=re.IGNORECASE).strip()
            kind = "shoutout"
        else:
            if campaign.get("activity_type") != "question":
                send_dm(
                    user_id,
                    "This campaign has a poll rather than an open-ended question. "
                    "Please vote in the Watercooler channel."
                )
                return
            if delivery.get("question_status") != "awaiting":
                send_dm(user_id, "Your question response has already been handled.")
                return
            contribution = answer
            kind = "question"

        if not contribution:
            send_dm(user_id, "Please include details in your contribution.")
            return
        publish_contribution(user_id, campaign, delivery, kind, contribution)


app.event("message")(handle_message)


# ============================================================
# 11. CHANNEL POLL VOTING
# ============================================================

@app.action(re.compile(r"^watercooler_poll_vote_\d+$"))
def handle_poll_vote(ack, body, action):
    ack()
    user_id = body.get("user", {}).get("id")
    action_id = action.get("action_id", "")
    match = re.match(r"^watercooler_poll_vote_(\d+)$", action_id)
    if not match:
        logger.warning("Invalid poll action ID: %s", action_id)
        return

    action_option_index = int(match.group(1))
    try:
        vote_data = json.loads(action.get("value", "{}"))
        campaign_id = str(vote_data["campaign_id"])
        option_index = int(vote_data["option_index"])
    except (ValueError, KeyError, TypeError):
        logger.warning("Invalid poll vote payload.")
        return
    if option_index != action_option_index:
        logger.warning("Poll action ID and option index do not match.")
        return

    campaign_row = get_campaign_by_id(campaign_id)
    if not campaign_row or campaign_row.get("activity_type") != "poll":
        return

    delivery = get_delivery(campaign_id, user_id)
    if not delivery or not delivery.get("sent_at"):
        return

    options = campaign_row.get("poll_options") or []
    if option_index < 0 or option_index >= len(options):
        return

    try:
        supabase.table("poll_votes").upsert({
            "campaign_id": campaign_id,
            "slack_user_id": user_id,
            "option_index": option_index
        }, on_conflict="campaign_id,slack_user_id").execute()
        update_channel_poll_results(campaign_id)
    except Exception:
        logger.exception("Could not save or publish updated poll results.")
        send_dm(user_id, "We couldn't record your vote. Please try again.")
        return

    send_dm(
        user_id,
        f"Your vote has been recorded: *{escape_slack_text(options[option_index])}*. "
        "You can change your vote by choosing another option. 📊"
    )


# ============================================================
# 12. PRODUCTION HEALTH AND SCHEDULER ENDPOINTS
# ============================================================

@flask_app.route("/", methods=["GET"])
def home():
    return "Watercooler Bot 2.0 is running.", 200


@flask_app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "watercooler-bot-2.0"}, 200


@flask_app.route("/trigger", methods=["POST"])
def trigger_campaign():
    supplied_secret = request.headers.get("X-Scheduler-Secret", "")
    logger.warning(
        "Scheduler auth diagnostic: header_present=%s, supplied_length=%d, expected_length=%d",
        bool(supplied_secret), len(supplied_secret), len(SCHEDULER_SECRET)
    )
    if not hmac.compare_digest(supplied_secret, SCHEDULER_SECRET):
        return {"status": "error", "message": "Unauthorized"}, 401

    data = request.get_json(silent=True) or {}
    day_name = str(data.get("day", "")).lower().strip()
    campaign_date = str(data.get("date") or datetime.now(TIMEZONE).date().isoformat())

    if day_name not in ("monday", "friday"):
        return {"status": "error", "message": "Use monday or friday."}, 400

    try:
        result = send_campaign(day_name, campaign_date)
        return {"status": "success", "message": f"{day_name.title()} campaign processed.", **result}, 200
    except Exception:
        logger.exception("Production campaign trigger failed.")
        return {
            "status": "error",
            "message": "Campaign could not be processed. Check Render logs."
        }, 500


# ============================================================
# 13. START APPLICATION
# ============================================================

def run_flask():
    port = int(os.getenv("PORT", "10000"))
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)


if __name__ == "__main__":
    logger.info("Starting Watercooler Bot 2.0 in PRODUCTION MODE.")
    threading.Thread(target=run_flask, daemon=True).start()
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
