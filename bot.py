import os
import psycopg2
import logging
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
OWNER_USER_ID = int(os.environ['OWNER_USER_ID'])

DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''
  CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    sticker_filter INTEGER DEFAULT 0
  )
''')
cursor.execute('''
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    points INTEGER DEFAULT 0
  )
''')
cursor.execute('''
  CREATE TABLE IF NOT EXISTS point_actions (
    id SERIAL PRIMARY KEY,
    action TEXT UNIQUE,
    points INTEGER DEFAULT 0
  )
''')
conn.commit()


# --- Logging ---

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- Command Handlers ---


def start(update, context):
    welcome_message = """
Hello! I'm your learning group bot. Here are the commands you can use:

/tagall - Tag all members (except bots).
/reward <username> - Award a point to a member.
/givepoints <username> <points> - (Owner) Award points to a member.
/mypoints - Check your points.
/kick <username> - (Owner) Kick a member.
/stickerfilter - (Owner) Toggle sticker deletion.
/pin - (Owner) Pin the replied message.
/del - (Owner) Delete the replied message.
/leaderboard - See the top point earners.
/setpoints <action> <points> - (Owner) Set points for an action (e.g., /setpoints quiz_answer 5).

Participate and earn points!
"""
    context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

# ... other command handlers (tagall, reward, givepoints, mypoints, kick, stickerfilter, pin, del_message, leaderboard, setpoints) - include their implementation from your previous code


# --- Message Handler ---

def on_message(update, context):
    # ... (Add logic here to check if the message matches any action 
    #      in point_actions table and award points accordingly)
    user_id = update.effective_user.id
    username = update.effective_user.username

    # 1. Award points for sending any message
    cursor.execute(
        'INSERT INTO users (id, username, points) VALUES (%s, %s, 1) ON CONFLICT (id) DO UPDATE SET points = points + 1',
        (user_id, username)
    )
    conn.commit()

    # 2. Award points for specific actions (example: answering a quiz correctly)
    message_text = update.message.text.lower()
    if message_text.startswith("answer:"):
        cursor.execute('SELECT points FROM point_actions WHERE action = %s', ('quiz_answer',))
        result = cursor.fetchone()
        if result:
            points_to_add = result[0]
            cursor.execute('UPDATE users SET points = points + %s WHERE id = %s', (points_to_add, user_id))
            conn.commit()


# --- Error Handler ---

def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


# --- Main Bot Setup ---

if __name__ == '__main__':
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Add command handlers
    dp.add_handler(CommandHandler("start", start))
    # ... (add handlers for other commands)

    dp.add_handler(MessageHandler(Filters.all, on_message))
    dp.add_error_handler(error)

    # Start the webhook (for Heroku)
    PORT = int(os.environ.get('PORT', '8443'))
    updater.start_webhook(listen="0.0.0.0",
                         port=PORT,
                         url_path=BOT_TOKEN,
                         webhook_url=f"https://{os.environ['HEROKU_APP_NAME']}.herokuapp.com/{BOT_TOKEN}")

    updater.idle()
