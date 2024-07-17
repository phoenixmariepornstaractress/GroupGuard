from telegram import Update, Bot, ParseMode, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler, JobQueue
from telegram.utils.helpers import mention_html
import logging
import re
import random
import string
from datetime import timedelta, datetime
import json
import os
import requests

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define the bot token
TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

# Define blocklist and notes dictionary
BLOCKLIST = ["spam", "bannedword"]
NOTES = {}
WARNINGS = {}
CAPTCHA_DICT = {}
MUTE_TIME = 300  # in seconds (5 minutes)
USER_MESSAGES = {}
REMINDERS = {}
FAQ = {}
BIRTHDAYS = {}
SCHEDULED_MESSAGES = []
QUOTES = ["Quote 1", "Quote 2", "Quote 3"]
WEATHER_API_KEY = 'YOUR_WEATHER_API_KEY'
AUTO_BACKUP_INTERVAL = 86400  # in seconds (24 hours)

# Start command handler
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hi! I am your group management bot. Type /help to see what I can do.')

# Help command handler
def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/setnote <note> <content> - Set a note\n"
        "/getnote <note> - Get a note\n"
        "/warn <user> - Warn a user\n"
        "/mute <user> - Mute a user\n"
        "/unmute <user> - Unmute a user\n"
        "/ban <user> - Ban a user\n"
        "/unban <user> - Unban a user\n"
        "/groupinfo - Get group info\n"
        "/userinfo <user> - Get user info\n"
        "/backupnotes - Backup notes\n"
        "/restorenotes - Restore notes\n"
        "/setwelcome <message> - Set custom welcome message\n"
        "/stats - Get daily stats\n"
        "/createpoll <question> - Create a poll\n"
        "/remind <time> <message> - Set a reminder\n"
        "/addfaq <question> <answer> - Add an FAQ\n"
        "/getfaq <question> - Get an FAQ\n"
        "/adminpanel - Open admin panel\n"
        "/customcommand - Set a custom command\n"
        "/dailyreport - Get daily report\n"
        "/weeklyreport - Get weekly report\n"
        "/setbirthday <date> - Set your birthday\n"
        "/getbirthday <user> - Get a user's birthday\n"
        "/schedulemsg <time> <message> - Schedule a message\n"
        "/quote - Get the quote of the day\n"
        "/weather <city> - Get the current weather for a city\n"
    )
    update.message.reply_text(help_text)

# Welcome new members
def welcome(update: Update, context: CallbackContext) -> None:
    for member in update.message.new_chat_members:
        # Generate CAPTCHA
        captcha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        CAPTCHA_DICT[member.id] = captcha
        welcome_message = context.bot_data.get("welcome_message", "Welcome {name}! Please verify yourself by sending the following code: {captcha}")
        update.message.reply_text(
            welcome_message.format(name=mention_html(member.id, member.full_name), captcha=captcha),
            parse_mode=ParseMode.HTML
        )

# Verify CAPTCHA
def verify_captcha(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in CAPTCHA_DICT:
        if update.message.text == CAPTCHA_DICT[user_id]:
            update.message.reply_text("You have been verified!")
            del CAPTCHA_DICT[user_id]
        else:
            update.message.reply_text("Incorrect CAPTCHA. Please try again.")

# Goodbye members
def goodbye(update: Update, context: CallbackContext) -> None:
    if update.message.left_chat_member:
        update.message.reply_text(f"Goodbye {mention_html(update.message.left_chat_member.id, update.message.left_chat_member.full_name)}!", parse_mode=ParseMode.HTML)

# Blocklist handler
def blocklist(update: Update, context: CallbackContext) -> None:
    message_text = update.message.text.lower()
    for word in BLOCKLIST:
        if re.search(r'\b' + word + r'\b', message_text):
            try:
                update.message.delete()
                update.message.reply_text(f"Message deleted. '{word}' is not allowed here.")
            except Exception as e:
                logger.warning(f"Failed to delete message: {e}")

# Lock handler example (locking links)
def lock_links(update: Update, context: CallbackContext) -> None:
    if 'http' in update.message.text or 'www' in update.message.text:
        try:
            update.message.delete()
            update.message.reply_text("Links are not allowed in this group.")
        except Exception as e:
            logger.warning(f"Failed to delete message: {e}")

# Set note
def set_note(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) >= 2:
        note = args[0]
        content = ' '.join(args[1:])
        NOTES[note] = content
        update.message.reply_text(f"Note '{note}' has been set.")
    else:
        update.message.reply_text("Usage: /setnote <note> <content>")

# Get note
def get_note(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) == 1:
        note = args[0]
        if note in NOTES:
            update.message.reply_text(NOTES[note])
        else:
            update.message.reply_text(f"Note '{note}' not found.")
    else:
        update.message.reply_text("Usage: /getnote <note>")

# Filter keywords and respond
def filter_keywords(update: Update, context: CallbackContext) -> None:
    if 'hello' in update.message.text.lower():
        update.message.reply_text("Hi there!")
    elif 'bye' in update.message.text.lower():
        update.message.reply_text("Goodbye!")

# Anti-flood system
def anti_flood(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_name = update.message.from_user.username
    if user_id not in WARNINGS:
        WARNINGS[user_id] = 1
    else:
        WARNINGS[user_id] += 1

    if WARNINGS[user_id] > 5:  # threshold for warnings
        update.message.chat.kick_member(user_id)
        update.message.reply_text(f"{user_name} has been kicked for spamming.")
        del WARNINGS[user_id]

# Warn a user
def warn(update: Update, context: CallbackContext) -> None:
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        user_name = update.message.reply_to_message.from_user.username
        if user_id not in WARNINGS:
            WARNINGS[user_id] = 1
        else:
            WARNINGS[user_id] += 1
        update.message.reply_text(f"{user_name} has been warned ({WARNINGS[user_id]}/3).")

        if WARNINGS[user_id] >= 3:
            update.message.chat.kick_member(user_id)
            update.message.reply_text(f"{user_name} has been banned for multiple warnings.")
            del WARNINGS[user_id]
    else:
        update.message.reply_text("Reply to a user's message to warn them.")

# Mute a user
def mute(update: Update, context: CallbackContext) -> None:
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        user_name = update.message.reply_to_message.from_user.username
        until_date = update.message.date + timedelta(seconds=MUTE_TIME)
        permissions = ChatPermissions(can_send_messages=False)
        update.message.chat.restrict_member(user_id, permissions, until_date)
        update.message.reply_text(f"{user_name} has been muted for {MUTE_TIME//60} minutes.")
    else:
        update.message.reply_text("Reply to a user's message to mute them.")

# Unmute a user
def unmute(update: Update, context: CallbackContext) -> None:
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        user_name = update.message.reply_to_message.from_user.username
        permissions = ChatPermissions(can_send_messages=True)
        update.message.chat.restrict_member(user_id, permissions)
        update.message.reply_text(f"{user_name} has been unmuted.")
    else:
        update.message.reply_text("Reply to a user's message to unmute them.")

# Ban a user
def ban(update: Update, context: CallbackContext) -> None:
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        user_name = update.message.reply_to_message.from_user.username
        update.message.chat.kick_member(user_id)
        update.message.reply_text(f"{user_name} has been banned.")
    else:
        update.message.reply_text("Reply to a user's message to ban them.")

# Unban a user
def unban(update: Update, context: CallbackContext) -> None:
    if context.args:
        user_id = context.args[0]
        update.message.chat.unban_member(user_id)
        update.message.reply_text(f"User {user_id} has been unbanned.")
    else:
        update.message.reply_text("Usage: /unban <user_id>")

# Get group info
def group_info(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    update.message.reply_text(
        f"Group Name: {chat.title}\n"
        f"Group ID: {chat.id}\n"
        f"Member Count: {chat.get_members_count()}\n"
    )

# Get user info
def user_info(update: Update, context: CallbackContext) -> None:
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        update.message.reply_text(
            f"User Name: {user.full_name}\n"
            f"User ID: {user.id}\n"
            f"Username: {user.username}\n"
        )
    else:
        update.message.reply_text("Reply to a user's message to get their info.")

# Backup notes
def backup_notes(update: Update, context: CallbackContext) -> None:
    with open('notes_backup.json', 'w') as f:
        json.dump(NOTES, f)
    update.message.reply_text("Notes have been backed up.")

# Restore notes
def restore_notes(update: Update, context: CallbackContext) -> None:
    if os.path.exists('notes_backup.json'):
        with open('notes_backup.json', 'r') as f:
            global NOTES
            NOTES = json.load(f)
        update.message.reply_text("Notes have been restored.")
    else:
        update.message.reply_text("No backup found.")

# Set custom welcome message
def set_welcome(update: Update, context: CallbackContext) -> None:
    if context.args:
        welcome_message = ' '.join(context.args)
        context.bot_data["welcome_message"] = welcome_message
        update.message.reply_text("Welcome message has been set.")
    else:
        update.message.reply_text("Usage: /setwelcome <message>")

# Create poll
def create_poll(update: Update, context: CallbackContext) -> None:
    if context.args:
        question = ' '.join(context.args)
        update.message.reply_poll(question=question, options=["Option 1", "Option 2", "Option 3"])
    else:
        update.message.reply_text("Usage: /createpoll <question>")

# Set reminder
def set_reminder(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) >= 2:
        time = int(args[0])
        reminder_message = ' '.join(args[1:])
        job_queue = context.job_queue
        job_queue.run_once(remind_user, time, context=update.message.chat_id, name=reminder_message)
        update.message.reply_text(f"Reminder set for {time} seconds.")
    else:
        update.message.reply_text("Usage: /remind <time_in_seconds> <message>")

# Reminder function
def remind_user(context: CallbackContext) -> None:
    job = context.job
    context.bot.send_message(job.context, text=job.name)

# Add FAQ
def add_faq(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) >= 2:
        question = args[0]
        answer = ' '.join(args[1:])
        FAQ[question] = answer
        update.message.reply_text(f"FAQ '{question}' has been added.")
    else:
        update.message.reply_text("Usage: /addfaq <question> <answer>")

# Get FAQ
def get_faq(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) == 1:
        question = args[0]
        if question in FAQ:
            update.message.reply_text(FAQ[question])
        else:
            update.message.reply_text(f"FAQ '{question}' not found.")
    else:
        update.message.reply_text("Usage: /getfaq <question>")

# Admin panel
def admin_panel(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Backup Notes", callback_data='backup_notes')],
        [InlineKeyboardButton("Restore Notes", callback_data='restore_notes')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Admin Panel:', reply_markup=reply_markup)

# Button handler for admin panel
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    if query.data == 'backup_notes':
        backup_notes(update, context)
    elif query.data == 'restore_notes':
        restore_notes(update, context)

# Custom command
def custom_command(update: Update, context: CallbackContext) -> None:
    # Placeholder for custom command
    update.message.reply_text("This is a custom command.")

# Daily report
def daily_report(update: Update, context: CallbackContext) -> None:
    # Placeholder for daily report
    update.message.reply_text("This is the daily report.")

# Weekly report
def weekly_report(update: Update, context: CallbackContext) -> None:
    # Placeholder for weekly report
    update.message.reply_text("This is the weekly report.")

# Set birthday
def set_birthday(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) == 1:
        date = args[0]
        BIRTHDAYS[update.message.from_user.id] = date
        update.message.reply_text("Birthday has been set.")
    else:
        update.message.reply_text("Usage: /setbirthday <date>")

# Get birthday
def get_birthday(update: Update, context: CallbackContext) -> None:
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        if user_id in BIRTHDAYS:
            update.message.reply_text(f"Birthday: {BIRTHDAYS[user_id]}")
        else:
            update.message.reply_text("Birthday not set.")
    else:
        update.message.reply_text("Reply to a user's message to get their birthday.")

# Schedule a message
def schedule_message(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) >= 2:
        time = int(args[0])
        message = ' '.join(args[1:])
        SCHEDULED_MESSAGES.append((time, message))
        job_queue = context.job_queue
        job_queue.run_once(send_scheduled_message, time, context=(update.message.chat_id, message))
        update.message.reply_text(f"Message scheduled for {time} seconds.")
    else:
        update.message.reply_text("Usage: /schedulemsg <time_in_seconds> <message>")

# Send scheduled message
def send_scheduled_message(context: CallbackContext) -> None:
    job = context.job
    chat_id, message = job.context
    context.bot.send_message(chat_id, text=message)

# Get quote of the day
def quote(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(random.choice(QUOTES))

# Get weather
def weather(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) == 1:
        city = args[0]
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()
        if data['cod'] == 200:
            weather_data = (
                f"City: {data['name']}\n"
                f"Temperature: {data['main']['temp']}°C\n"
                f"Weather: {data['weather'][0]['description']}"
            )
            update.message.reply_text(weather_data)
        else:
            update.message.reply_text("City not found.")
    else:
        update.message.reply_text("Usage: /weather <city>")

# Automatic backup
def auto_backup(context: CallbackContext) -> None:
    with open('notes_backup.json', 'w') as f:
        json.dump(NOTES, f)
    context.bot.send_message(context.job.context, text="Automatic backup completed.")

def main() -> None:
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("setnote", set_note))
    dispatcher.add_handler(CommandHandler("getnote", get_note))
    dispatcher.add_handler(CommandHandler("warn", warn))
    dispatcher.add_handler(CommandHandler("mute", mute))
    dispatcher.add_handler(CommandHandler("unmute", unmute))
    dispatcher.add_handler(CommandHandler("ban", ban))
    dispatcher.add_handler(CommandHandler("unban", unban))
    dispatcher.add_handler(CommandHandler("groupinfo", group_info))
    dispatcher.add_handler(CommandHandler("userinfo", user_info))
    dispatcher.add_handler(CommandHandler("backupnotes", backup_notes))
    dispatcher.add_handler(CommandHandler("restorenotes", restore_notes))
    dispatcher.add_handler(CommandHandler("setwelcome", set_welcome))
    dispatcher.add_handler(CommandHandler("createpoll", create_poll))
    dispatcher.add_handler(CommandHandler("remind", set_reminder))
    dispatcher.add_handler(CommandHandler("addfaq", add_faq))
    dispatcher.add_handler(CommandHandler("getfaq", get_faq))
    dispatcher.add_handler(CommandHandler("adminpanel", admin_panel))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(CommandHandler("customcommand", custom_command))
    dispatcher.add_handler(CommandHandler("dailyreport", daily_report))
    dispatcher.add_handler(CommandHandler("weeklyreport", weekly_report))
    dispatcher.add_handler(CommandHandler("setbirthday", set_birthday))
    dispatcher.add_handler(CommandHandler("getbirthday", get_birthday))
    dispatcher.add_handler(CommandHandler("schedulemsg", schedule_message))
    dispatcher.add_handler(CommandHandler("quote", quote))
    dispatcher.add_handler(CommandHandler("weather", weather))

    job_queue.run_daily(auto_backup, time=datetime.time(hour=0, minute=0), context=job_queue)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
