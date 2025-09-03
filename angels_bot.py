import os
import sqlite3
import logging
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
import re

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
PAYMENT_TOKEN = os.getenv('PAYMENT_TOKEN')
DATABASE_PATH = 'angels_bot.db'

SUBSCRIPTIONS = {
    'free': {'name': 'Free', 'questions': 50, 'cooldown': 30, 'price': 0},
    'premium_6m': {'name': '6 Months Premium', 'questions': -1, 'cooldown': 15, 'price': 299},
    'premium_12m': {'name': '12 Months Premium', 'questions': -1, 'cooldown': 10, 'price': 499}
}

def validate_birth_info(text):
    text = text.strip()
    parts = text.split()
    
    if len(parts) < 2:
        return False, "Please provide both your name and birth date.\nExample: 'Maria 15/03/1990'", None, None
    
    name_parts = parts[:-1]
    date_part = parts[-1]
    name = ' '.join(name_parts)
    
    if len(name) < 2:
        return False, "Please provide a valid name with at least 2 characters.", None, None
    
    date_patterns = [
        r'^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})$',
        r'^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2})$'
    ]
    
    parsed_date = None
    for pattern in date_patterns:
        match = re.match(pattern, date_part)
        if match:
            day, month, year = match.groups()
            
            if len(year) == 2:
                year = int(year)
                if year <= 30:
                    year += 2000
                else:
                    year += 1900
            else:
                year = int(year)
            
            day, month = int(day), int(month)
            
            try:
                parsed_date = datetime(year, month, day)
                break
            except ValueError:
                continue
    
    if not parsed_date:
        return False, "Invalid date format. Please use DD/MM/YYYY format.\nExample: '15/03/1990'", None, None
    
    if parsed_date > datetime.now():
        return False, "Birth date cannot be in the future. Please enter a valid birth date.", None, None
    
    min_age_date = datetime.now() - timedelta(days=10*365.25)
    if parsed_date > min_age_date:
        return False, "You must be at least 10 years old to use this service.", None, None
    
    max_age_date = datetime.now() - timedelta(days=120*365.25)
    if parsed_date < max_age_date:
        return False, "Please enter a realistic birth date.", None, None
    
    return True, None, name, parsed_date

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
        self.populate_responses()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                subscription_type TEXT DEFAULT 'free',
                questions_used INTEGER DEFAULT 0,
                last_question_time DATETIME,
                subscription_expires DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_name TEXT,
                birth_date TEXT,
                has_completed_setup BOOLEAN DEFAULT FALSE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_number INTEGER,
                angel_type TEXT NOT NULL,
                text_content TEXT NOT NULL,
                has_image BOOLEAN DEFAULT FALSE,
                image_path TEXT,
                language TEXT DEFAULT 'en'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                angel_type TEXT,
                response_id INTEGER,
                question_text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def populate_responses(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM responses")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        light_responses = [
            (1, "I see golden light in your future, let it guide you toward joy", False),
            (2, "The morning star reveals that hope approaches, have faith in your heart", False),
            (3, "Luminous winds whisper that patience will be rewarded, bless this moment", False),
            (4, "The light within you will shine brighter, prepare to welcome grace", False),
            (5, "A bridge of light is being built for you, cross it with courage and faith", False),
            (16, "I see wings of light protecting you in your journey, trust in divine protection", False),
            (27, "A golden door is opening before you, step through with hope and gratitude", False),
            (31, "A golden thread weaves through your destiny, follow it with trust and wonder", False),
            (46, "I see golden rain falling on your garden, let abundance grow in every corner", False),
            (61, "Heaven's gate opens wider with each kind act, step through with generosity", False),
            (74, "The sail of your dreams catches winds of opportunity, navigate toward your goals", False),
            (76, "Sunrise paints your tomorrow with colors of possibility, wake to new chances", False),
            (78, "Rainbows arch over your trials with promises of beauty, look up after storms", False),
            (79, "Butterflies carry wishes on gossamer wings to the divine, release your desires", False),
            (86, "Your guardian's wings cast shadows of protection, rest in their shelter", False),
            (121, "Starlight weaves silver threads through your dreams, follow them to manifest reality", False),
            (122, "Moonbeams paint pathways across your night sky, walk them toward your destiny", False),
            (124, "Candlelight flickers with messages of hope, interpret their dancing shadows", False),
            (126, "Angels collect your tears in crystal vials, transforming sorrow into wisdom", False),
            (132, "The golden fleece awaits your heroic journey, embark on your personal quest", False),
            (133, "The holy grail fills with whatever you truly need, drink from your authentic desires", False),
            (134, "The philosopher's stone transforms your lead experiences into gold, embrace alchemy", False),
            (136, "White horses carry your prayers across celestial plains, mount them with faith", False),
            (137, "Doves deliver messages between earth and heaven, send your requests upward", False),
            (138, "Eagles soar with visions of your highest potential, spread your wings and follow", False),
            (139, "Swans glide gracefully through turbulent waters, embody their serene elegance", False),
            (140, "Peacocks display your true colors with pride, show your authentic beauty", False),
            (141, "Crystal caves echo with sounds of your healing, enter them with reverence", False),
            (142, "Sacred springs bubble with waters of renewal, bathe in their restorative power", False),
            (143, "Holy mountains offer perspectives from above, climb them for expanded vision", False),
        ]
        
        dark_responses = [
            (1, "From night's depths emerges that mystery will unveil itself, listen to your intuition", False),
            (2, "Shadow whispers speak of secrets for you, prepare to discover the unexpected", False),
            (3, "In the cup of shadow your future is mixed, drink with awareness", False),
            (4, "Your soul's deep roots are strengthening, nurture the inner growth", False),
            (5, "From midnight's embrace comes the gift of solitude, learn what silence teaches", False),
            (6, "Dancing shadows show you must look beyond appearance, find the hidden truth", False),
            (11, "The growing moon reveals your transformation has begun, embrace what you will become", False),
            (13, "The full moon reveals your strength is at its peak, embrace your power", False),
            (14, "The new moon reveals a new cycle begins, embrace the unknown", False),
            (32, "From time's shadows emerges that truth will reveal itself, listen to your instinct", False),
            (37, "The black mirror shows your hidden strengths, look deeper than surface fears", False),
            (41, "Raven wings carry messages from your depths, decode the symbols they bring", False),
            (42, "Wolf howls echo your primal knowing, remember the wildness you've forgotten", False),
            (44, "Spider webs show intricate connections, weave the pattern that calls you", False),
            (45, "Owl eyes pierce through illusion's veil, see the truth others fear to face", False),
            (46, "In the cavern of your unconscious, treasures wait for the bold explorer", False),
            (48, "In the forest of your dreams, wisdom grows for the patient wanderer", False),
            (49, "In the ocean of your emotions, pearls form for the deep diver", False),
            (67, "Your dark twin whispers truths you fear to hear, listen with courageous ears", False),
            (94, "Below the noise of constant chatter, profound silence holds deep answers", False),
            (101, "The cauldron of transformation bubbles with your becoming, stir it with intention", False),
            (104, "The pentacle of protection shields your vulnerability, invoke it when needed", False),
            (105, "Dusk contemplations prepare you for night's teachings, welcome the darkness", False),
            (108, "Dawn reflections merge shadow and light within you, embrace your complexity", False),
            (111, "The underworld rivers carry messages from your depths, decode their meaning", False),
            (112, "The shadow realm mirrors show inverted truths, read them backwards", False),
            (116, "Your inner vampire thirsts for authentic experience, feed it real encounters", False),
            (118, "Your secret witch brews potions of possibility, trust her ancient recipes", False),
            (119, "Your dormant dragon guards treasures of power, awaken it with courage", False),
            (120, "Your sleeping phoenix prepares for rebirth through flames, surrender to transformation", False),
        ]
        
        for response_num, text, has_image in light_responses:
            cursor.execute(
                "INSERT INTO responses (response_number, angel_type, text_content, has_image, image_path) VALUES (?, ?, ?, ?, ?)",
                (response_num, 'light', text, has_image, None)
            )
        
        for response_num, text, has_image in dark_responses:
            cursor.execute(
                "INSERT INTO responses (response_number, angel_type, text_content, has_image, image_path) VALUES (?, ?, ?, ?, ?)",
                (response_num, 'dark', text, has_image, None)
            )
        
        conn.commit()
        conn.close()
        logger.info(f"Database populated with {len(light_responses)} light and {len(dark_responses)} dark responses")
    
    def get_or_create_user(self, user_id, username=None, first_name=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            cursor.execute(
                "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
        
        conn.close()
        return user
    
    def update_user_info(self, user_id, name, birth_date):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET user_name = ?, birth_date = ?, has_completed_setup = TRUE WHERE user_id = ?",
            (name, birth_date.isoformat(), user_id)
        )
        
        conn.commit()
        conn.close()
    
    def has_completed_setup(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT has_completed_setup FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result and result[0]
    
    def get_user_info(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_name, birth_date FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result
    
    def can_ask_question(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT subscription_type, questions_used, subscription_expires FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        sub_type, questions_used, expires = result
        
        if sub_type in ['premium_6m', 'premium_12m']:
            if expires and datetime.fromisoformat(expires) > datetime.now():
                return True
            else:
                self.update_subscription(user_id, 'free')
                sub_type = 'free'
        
        if sub_type == 'free':
            return questions_used < SUBSCRIPTIONS['free']['questions']
        
        return True
    
    def check_cooldown(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT subscription_type, last_question_time FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[1]:
            return True
        
        sub_type, last_time = result
        cooldown_minutes = SUBSCRIPTIONS.get(sub_type, SUBSCRIPTIONS['free'])['cooldown']
        
        try:
            last_question = datetime.fromisoformat(last_time)
            time_passed = datetime.now() - last_question
            return time_passed >= timedelta(minutes=cooldown_minutes)
        except ValueError:
            return True
    
    def get_time_until_next_question(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT subscription_type, last_question_time FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[1]:
            return 0
        
        sub_type, last_time = result
        cooldown_minutes = SUBSCRIPTIONS.get(sub_type, SUBSCRIPTIONS['free'])['cooldown']
        
        try:
            last_question = datetime.fromisoformat(last_time)
            time_passed = datetime.now() - last_question
            remaining = timedelta(minutes=cooldown_minutes) - time_passed
            return max(0, int(remaining.total_seconds() / 60))
        except ValueError:
            return 0
    
    def get_random_response(self, angel_type):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM responses WHERE angel_type = ?", (angel_type,))
        responses = cursor.fetchall()
        conn.close()
        
        if responses:
            return random.choice(responses)
        return None
    
    def get_sound_path(self, angel_type):
        if angel_type == 'light':
            return 'sounds/light_angel.mp3'
        elif angel_type == 'dark':
            return 'sounds/dark_angel.mp3'
        return None
    
    def log_question(self, user_id, angel_type, response_id, question_text=""):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET questions_used = questions_used + 1, last_question_time = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        
        cursor.execute(
            "INSERT INTO question_log (user_id, angel_type, response_id, question_text) VALUES (?, ?, ?, ?)",
            (user_id, angel_type, response_id, question_text[:500])
        )
        
        conn.commit()
        conn.close()
    
    def update_subscription(self, user_id, sub_type, months=0):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expires = None
        if months > 0:
            expires = (datetime.now() + timedelta(days=months*30)).isoformat()
        
        cursor.execute(
            "UPDATE users SET subscription_type = ?, subscription_expires = ?, questions_used = 0 WHERE user_id = ?",
            (sub_type, expires, user_id)
        )
        
        conn.commit()
        conn.close()

db = DatabaseManager(DATABASE_PATH)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_or_create_user(user.id, user.username, user.first_name)
    
    if db.has_completed_setup(user.id):
        await show_main_menu(update)
    else:
        await show_setup_screen(update)

async def show_setup_screen(update):
    welcome_text = """✨ **Welcome to Angels Oracle Bot!** 🌙

*Receive divine guidance from two mystical angels*

📝 **To personalize your experience, please provide:**
• Your first name
• Your birth date (DD/MM/YYYY)

**Example:** `Maria 15/03/1990`

⚠️ *This information is used only for entertainment purposes. All responses are fictional.*"""
    
    keyboard = [
        [InlineKeyboardButton("ℹ️ How it Works", callback_data='how_it_works')],
        [InlineKeyboardButton("💎 Premium Plans", callback_data='premium')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def show_main_menu(update):
    user_info = db.get_user_info(update.effective_user.id)
    user_name = user_info[0] if user_info else "Seeker"
    
    welcome_text = f"""✨ **Welcome back, {user_name}!** 🌙

**Choose your divine guide:**

✨ **Angel of Light (Seraphiel)**
*Hope, protection, and divine guidance*

🖤 **Angel of Darkness (Nyxareth)**
*Hidden truths, transformation, and deep wisdom*

**Free users:** 50 questions total
**Premium users:** Unlimited questions + shorter cooldowns

⚠️ *Disclaimer: This is for entertainment purposes only.*"""
    
    keyboard = [
        [InlineKeyboardButton("✨ Angel of Light", callback_data='angel_light')],
        [InlineKeyboardButton("🖤 Angel of Darkness", callback_data='angel_dark')],
        [InlineKeyboardButton("💎 Premium Plans", callback_data='premium')],
        [InlineKeyboardButton("ℹ️ My Status", callback_data='status')],
        [InlineKeyboardButton("⚙️ Change My Info", callback_data='change_info')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == 'how_it_works':
        await show_how_it_works(query)
    elif data == 'change_info':
        context.user_data['changing_info'] = True
        await show_change_info_screen(query)
    elif data == 'back_to_setup':
        await show_setup_screen(query)
    elif data == 'back_main':
        await show_main_menu(query)
    elif data.startswith('angel_'):
        angel_type = 'light' if data == 'angel_light' else 'dark'
        context.user_data['selected_angel'] = angel_type
        await show_angel_intro(query, angel_type)
    elif data == 'premium':
        await show_premium_plans(query)
    elif data == 'status':
        await show_user_status(query, user_id)

async def show_how_it_works(query):
    text = """ℹ️ **How Angels Oracle Works**

1️⃣ **Setup**: Provide your name and birth date
2️⃣ **Choose**: Select Angel of Light or Darkness  
3️⃣ **Ask**: Type your question
4️⃣ **Receive**: Get personalized divine guidance

**The Angels:**
✨ **Seraphiel (Light)** - Hope, healing, protection
🖤 **Nyxareth (Darkness)** - Hidden truths, transformation

**Limits:**
• Free: 50 total questions, 30min cooldown
• Premium: Unlimited questions, shorter cooldowns

*All responses are generated for entertainment only.*"""
    
    keyboard = [[InlineKeyboardButton("← Back", callback_data='back_to_setup')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def show_change_info_screen(query):
    text = """⚙️ **Change Your Information**

Please provide your updated information:
• Your first name
• Your birth date (DD/MM/YYYY)

**Example:** `John 25/12/1985`"""
    
    keyboard = [[InlineKeyboardButton("← Cancel", callback_data='back_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def show_angel_intro(query, angel_type):
    if angel_type == 'light':
        angel_name = "Seraphiel"
        angel_message = "I am Seraphiel, the Angel of Light. I bring hope, protection, and divine wisdom to guide you toward joy and fulfillment."
        angel_emoji = "✨"
    else:
        angel_name = "Nyxareth"  
        angel_message = "I am Nyxareth, the Angel of Darkness. I reveal hidden truths and guide your transformation through the mysteries of the shadow realm."
        angel_emoji = "🖤"
    
    intro_text = f"""{angel_emoji} **{angel_message}** {angel_emoji}

Ask me your question and I will provide divine guidance tailored to your spiritual journey.

*Type your question now...*"""
    
    keyboard = [
        [InlineKeyboardButton("← Back to Angels", callback_data='back_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(intro_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def show_premium_plans(query):
    text = """💎 **Premium Plans** 💎

🆓 **Free Plan**
• 50 questions total (shared between angels)
• 30 minutes cooldown between questions

💎 **6 Months Premium** - €2.99
• Unlimited questions
• 15 minutes cooldown
• Priority support

💎💎 **12 Months Premium** - €4.99
• Unlimited questions  
• 10 minutes cooldown
• Priority support

*Payments are secure and processed by Telegram*"""
    
    keyboard = [
        [InlineKeyboardButton("← Back", callback_data='back_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def show_user_status(query, user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT subscription_type, questions_used, user_name FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        await query.edit_message_text("User not found. Please use /start")
        return
    
    sub_type, questions_used, user_name = result
    sub_info = SUBSCRIPTIONS[sub_type]
    
    remaining = "Unlimited" if sub_info['questions'] == -1 else max(0, sub_info['questions'] - questions_used)
    
    status_text = f"""📊 **Your Status** 📊

**Name:** {user_name or 'Not set'}
**Plan:** {sub_info['name']}
**Questions Used:** {questions_used}
**Questions Remaining:** {remaining}
**Cooldown:** {sub_info['cooldown']} minutes"""
    
    if not db.check_cooldown(user_id):
        minutes_left = db.get_time_until_next_question(user_id)
        status_text += f"\n\n⏰ **Next question in:** {minutes_left} minutes"
    
    keyboard = [
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data='premium')],
        [InlineKeyboardButton("← Back", callback_data='back_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if not db.has_completed_setup(user_id) or context.user_data.get('changing_info', False):
        is_valid, error_msg, name, birth_date = validate_birth_info(text)
        
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}")
            return
        
        db.update_user_info(user_id, name, birth_date)
        
        if context.user_data.get('changing_info', False):
            context.user_data['changing_info'] = False
            await update.message.reply_text(f"✅ Your information has been updated successfully, {name}!")
            await show_main_menu(update)
        else:
            await update.message.reply_text(f"✅ Welcome, {name}! Your birth information has been recorded.")
            await show_main_menu(update)
        return
    
    if 'selected_angel' not in context.user_data:
        keyboard = [
            [InlineKeyboardButton("✨ Angel of Light", callback_data='angel_light')],
            [InlineKeyboardButton("🖤 Angel of Darkness", callback_data='angel_dark')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please choose your Angel first! ✨",
            reply_markup=reply_markup
        )
        return
    
    angel_type = context.user_data['selected_angel']
    
    if not db.can_ask_question(user_id):
        await update.message.reply_text(
            "⛔ You have reached your question limit!\n\n"
            "Upgrade to Premium for unlimited questions:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 View Premium Plans", callback_data='premium')]
            ])
        )
        return
    
    if not db.check_cooldown(user_id):
        minutes_left = db.get_time_until_next_question(user_id)
        angel_name = "Seraphiel" if angel_type == 'light' else "Nyxareth"
        await update.message.reply_text(
            f"⏰ {angel_name} needs {minutes_left} more minutes to restore divine energy.\n\n"
            f"Upgrade to Premium for shorter cooldowns!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 View Premium Plans", callback_data='premium')]
            ])
        )
        return
    
    response = db.get_random_response(angel_type)
    if not response:
        await update.message.reply_text("⛔ Sorry, no responses available.")
        return
    
    response_id, response_number, angel_type, text_content, has_image, image_path, language = response
    
    db.log_question(user_id, angel_type, response_id, text[:200])
    
    angel_name = "Seraphiel" if angel_type == 'light' else "Nyxareth"
    angel_emoji = "✨" if angel_type == 'light' else "🖤"
    formatted_response = f"{angel_emoji} *{text_content}*\n\n*- {angel_name}*"
    
    await update.message.reply_text(formatted_response, parse_mode=ParseMode.MARKDOWN)
    
    sound_path = db.get_sound_path(angel_type)
    if sound_path and os.path.exists(sound_path):
        try:
            with open(sound_path, 'rb') as sound_file:
                await update.message.reply_voice(
                    voice=sound_file,
                    caption=f"🎵 {angel_name}'s divine energy resonates...",
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logger.warning(f"Could not send sound file: {e}")
    
    keyboard = [
        [InlineKeyboardButton(f"Ask {angel_name} Again", callback_data=f'angel_{angel_type}')],
        [InlineKeyboardButton("Switch Angel", callback_data='back_main')],
        [InlineKeyboardButton("💎 Upgrade Premium", callback_data='premium')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "The divine energies have spoken. What would you like to do next?",
        reply_markup=reply_markup
    )

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Angels Oracle Bot started successfully!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
