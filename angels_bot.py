import os
import sqlite3
import logging
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
import asyncio

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
PAYMENT_TOKEN = os.getenv('PAYMENT_TOKEN')
DATABASE_PATH = 'angels_bot.db'

# Subscription types and pricing (in cents)
SUBSCRIPTIONS = {
    'free': {'name': 'Free', 'questions': 50, 'cooldown': 30, 'price': 0},
    'premium_6m': {'name': '6 Months Premium', 'questions': -1, 'cooldown': 15, 'price': 299},   # €2.99
    'premium_12m': {'name': '12 Months Premium', 'questions': -1, 'cooldown': 10, 'price': 499}  # €4.99
}

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
        self.populate_responses()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
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
                birth_date TEXT
            )
        ''')
        
        # Responses table
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
        
        # Question log for analytics
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
    
    def get_image_path(self, angel_type, response_number):
        """Find the correct image path based on your file names"""
        if angel_type == 'light':
            folder = "luce"
        else:  # dark
            folder = "OSCURITÀ"
        
        # Try different extensions and name formats
        possible_names = [
            f"images/{folder}/risposta {response_number}.png",
            f"images/{folder}/risposta {response_number}.jpg",
            f"images/{folder}/risposta_{response_number}.png", 
            f"images/{folder}/risposta_{response_number}.jpg",
            f"images/{folder}/risposta{response_number}.png",
            f"images/{folder}/risposta{response_number}.jpg",
        ]
        
        for path in possible_names:
            if os.path.exists(path):
                return path
        
        return None  # No image found
    
    def populate_responses(self):
        """Populate responses if empty - ALL IN ENGLISH"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if responses already exist
        cursor.execute("SELECT COUNT(*) FROM responses")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # Angel of Light responses - ALL IN ENGLISH
        light_responses = [
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
            (144, "Blessed valleys provide shelter from life's storms, rest in their protective embrace", False),
            (145, "Enchanted forests whisper secrets of growth, listen to their ancient wisdom", False),
            (146, "Your inner sun never sets on love's horizon, let it shine without eclipse", False),
            (147, "Your spiritual compass always points toward truth, follow its unwavering direction", False),
            (149, "Your heart's garden blooms with flowers of compassion, tend them with kindness", False),
            # Additional Light responses for variety
            (1, "I see golden light in your future, let it guide you toward joy", False),
            (2, "The morning star reveals that hope approaches, have faith in your heart", False),
            (3, "Luminous winds whisper that patience will be rewarded, bless this moment", False),
            (4, "The light within you will shine brighter, prepare to welcome grace", False),
            (5, "A bridge of light is being built for you, cross it with courage and faith", False),
            (6, "Divine flames burn away your doubts, trust that clarity will emerge", False),
            (7, "Sacred geometry patterns your path with divine order, trust the perfect design", False),
            (8, "Angels gather around your sleeping hours, rest knowing you are protected", False),
            (9, "The lighthouse of your soul beams across stormy seas, guide others to safety", False),
            (10, "Crystal tears of joy fall from celestial eyes, weep with happiness when it comes", False),
        ]
        
        # Angel of Darkness responses - ALL IN ENGLISH
        dark_responses = [
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
            (151, "Obsidian mirrors reflect not your face but your potential, gaze into tomorrow's self", False),
            (155, "Tourmaline transmutes chaos into creative force, harness the storm within you", False),
            (165, "Antidotes hide within the very substances that harm, seek wisdom in opposition", False),
            (171, "Raven caws prophecy from skeletal branches, interpret the omens they deliver", False),
            (176, "The void pregnant with infinite potential calls you, enter the fertile nothingness", False),
            # Additional Dark responses for variety
            (1, "From night's depths emerges that mystery will unveil itself, listen to your intuition", False),
            (2, "Shadow whispers speak of secrets for you, prepare to discover the unexpected", False),
            (3, "In the cup of shadow your future is mixed, drink with awareness", False),
            (4, "Your soul's deep roots are strengthening, nurture the inner growth", False),
            (5, "From midnight's embrace comes the gift of solitude, learn what silence teaches", False),
            (7, "The black mother's womb nurtures your rebirth, gestate in her protective embrace", False),
            (8, "Your shadow self holds keys to forbidden rooms, explore them with conscious intent", False),
            (9, "Beneath the surface of your calm waters, ancient wisdom stirs with patient power", False),
            (10, "Night-blooming flowers open only in darkness, find beauty in your struggles", False),
        ]
        
        # Insert light responses
        for response_num, text, has_image in light_responses:
            image_path = self.get_image_path('light', response_num) if has_image else None
            cursor.execute(
                "INSERT INTO responses (response_number, angel_type, text_content, has_image, image_path) VALUES (?, ?, ?, ?, ?)",
                (response_num, 'light', text, has_image, image_path)
            )
        
        # Insert dark responses  
        for response_num, text, has_image in dark_responses:
            image_path = self.get_image_path('dark', response_num) if has_image else None
            cursor.execute(
                "INSERT INTO responses (response_number, angel_type, text_content, has_image, image_path) VALUES (?, ?, ?, ?, ?)",
                (response_num, 'dark', text, has_image, image_path)
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
    
    def can_ask_question(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT subscription_type, questions_used, subscription_expires FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        sub_type, questions_used, expires = result
        
        # Check if premium subscription is still valid
        if sub_type in ['premium_6m', 'premium_12m']:
            if expires and datetime.fromisoformat(expires) > datetime.now():
                return True
            else:
                # Expired premium, revert to free
                self.update_subscription(user_id, 'free')
                sub_type = 'free'
        
        # Check free tier limits
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
            return True  # If datetime parsing fails, allow question
    
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
    
    def log_question(self, user_id, angel_type, response_id, question_text=""):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update user stats
        cursor.execute(
            "UPDATE users SET questions_used = questions_used + 1, last_question_time = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        
        # Log the question
        cursor.execute(
            "INSERT INTO question_log (user_id, angel_type, response_id, question_text) VALUES (?, ?, ?, ?)",
            (user_id, angel_type, response_id, question_text[:500])  # Limit question length
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
    
    def get_user_stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_type != 'free'")
        premium_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM question_log WHERE DATE(timestamp) = DATE('now')")
        questions_today = cursor.fetchone()[0]
        
        conn.close()
        return total_users, premium_users, questions_today

# Initialize database
db = DatabaseManager(DATABASE_PATH)

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.first_name)
    
    welcome_text = """✨ Welcome to the Angels Oracle Bot! 🌙

Choose your divine guide:
✨ **Angel of Light** - Hope, protection, and guidance  
🖤 **Angel of Darkness** - Hidden truths, transformation, and deep wisdom

**How it works:**
1. Choose your Angel
2. Share your name and birth date (for personalization)  
3. Ask your question
4. Receive divine guidance

**Free users:** 50 questions total
**Premium users:** Unlimited questions + shorter cooldowns

⚠️ *Disclaimer: This is for entertainment purposes only. Responses are not real spiritual guidance.*"""
    
    keyboard = [
        [InlineKeyboardButton("✨ Angel of Light", callback_data='angel_light')],
        [InlineKeyboardButton("🖤 Angel of Darkness", callback_data='angel_dark')],
        [InlineKeyboardButton("💎 View Premium Plans", callback_data='premium')],
        [InlineKeyboardButton("ℹ️ My Status", callback_data='status')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith('angel_'):
        angel_type = 'light' if data == 'angel_light' else 'dark'
        context.user_data['selected_angel'] = angel_type
        
        if angel_type == 'light':
            angel_name = "Seraphiel"
            angel_message = "I am Seraphiel, the Angel of Light. I am here to guide you toward hope, protection, and divine wisdom."
            angel_emoji = "✨"
        else:
            angel_name = "Nyxareth"
            angel_message = "I am Nyxareth, the Angel of Darkness. I am here to show you hidden truths and guide your transformation."
            angel_emoji = "🖤"
        
        intro_text = f"{angel_emoji} **{angel_message}** {angel_emoji}\n\n" \
                    f"Please share your first name and birth date for personalized guidance:\n" \
                    f"Example: 'Maria 15/03/1990'\n\n" \
                    f"Then ask your question and receive divine insight!"
        
        await query.edit_message_text(intro_text, parse_mode=ParseMode.MARKDOWN)
    
    elif data == 'premium':
        await show_premium_plans(query)
    
    elif data == 'status':
        await show_user_status(query, user_id)
    
    elif data.startswith('buy_'):
        sub_type = data.replace('buy_', '')
        if PAYMENT_TOKEN:
            await initiate_payment(query, user_id, sub_type)
        else:
            await query.edit_message_text("💳 Payment system not configured. Please contact support.")
    
    elif data == 'back_main':
        await start_from_callback(query, context)

async def start_from_callback(query, context):
    """Restart bot from callback"""
    user = query.from_user
    db.get_or_create_user(user.id, user.username, user.first_name)
    
    welcome_text = """✨ Welcome to the Angels Oracle Bot! 🌙

Choose your divine guide:
✨ **Angel of Light** - Hope, protection, and guidance  
🖤 **Angel of Darkness** - Hidden truths, transformation, and deep wisdom

**Free users:** 50 questions total
**Premium users:** Unlimited questions + shorter cooldowns

⚠️ *Disclaimer: This is for entertainment purposes only.*"""
    
    keyboard = [
        [InlineKeyboardButton("✨ Angel of Light", callback_data='angel_light')],
        [InlineKeyboardButton("🖤 Angel of Darkness", callback_data='angel_dark')],
        [InlineKeyboardButton("💎 View Premium Plans", callback_data='premium')],
        [InlineKeyboardButton("ℹ️ My Status", callback_data='status')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def show_premium_plans(query):
    text = """💎 **Premium Plans** 💎

🆓 **Free Plan**
• 50 questions total (shared between angels)
• 30 minutes cooldown between questions
• Includes some spectacular images

💎 **6 Months Premium** - €2.99
• Unlimited questions
• 15 minutes cooldown
• All exclusive images
• Priority support

💎💎 **12 Months Premium** - €4.99
• Unlimited questions  
• 10 minutes cooldown
• All exclusive images
• Early access to new features
• Priority support

*Payments are secure and processed by Telegram*"""
    
    keyboard = []
    if PAYMENT_TOKEN:
        keyboard.extend([
            [InlineKeyboardButton("💎 Buy 6 Months - €2.99", callback_data='buy_premium_6m')],
            [InlineKeyboardButton("💎💎 Buy 12 Months - €4.99", callback_data='buy_premium_12m')],
        ])
    else:
        keyboard.append([InlineKeyboardButton("💳 Payment Coming Soon", callback_data='payment_soon')])
    
    keyboard.append([InlineKeyboardButton("← Back to Main Menu", callback_data='back_main')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def show_user_status(query, user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT subscription_type, questions_used, subscription_expires FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        await query.edit_message_text("User not found. Please use /start")
        return
    
    sub_type, questions_used, expires = result
    sub_info = SUBSCRIPTIONS[sub_type]
    
    remaining = "Unlimited" if sub_info['questions'] == -1 else max(0, sub_info['questions'] - questions_used)
    
    status_text = f"""📊 **Your Status** 📊

**Plan:** {sub_info['name']}
**Questions Used:** {questions_used}
**Questions Remaining:** {remaining}
**Cooldown:** {sub_info['cooldown']} minutes"""
    
    if expires:
        try:
            exp_date = datetime.fromisoformat(expires).strftime("%Y-%m-%d")
            status_text += f"\n**Expires:** {exp_date}"
        except ValueError:
            pass
    
    # Add cooldown info if applicable
    if not db.check_cooldown(user_id):
        minutes_left = db.get_time_until_next_question(user_id)
        status_text += f"\n\n⏰ **Next question in:** {minutes_left} minutes"
    
    keyboard = [
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data='premium')],
        [InlineKeyboardButton("← Back to Main Menu", callback_data='back_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Check if user has selected an angel
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
    
    # Check if this looks like name/birthdate (contains numbers and date separators)
    has_numbers = any(char.isdigit() for char in text)
    has_date_sep = any(sep in text for sep in ['/', '-', '.'])
    
    if has_numbers and has_date_sep and len(text.split()) <= 3:
        # Store user info
        context.user_data['user_info'] = text
        angel_type = context.user_data['selected_angel']
        angel_name = "Seraphiel" if angel_type == 'light' else "Nyxareth"
        
        # Update database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET user_name = ?, birth_date = ? WHERE user_id = ?", 
                      (text, text, user_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"Your essence has been recognized by {angel_name}. 🔮\n\n"
            f"Now ask your question to receive divine guidance:"
        )
        return
    
    # This is a question
    angel_type = context.user_data['selected_angel']
    
    # Check limits and cooldown
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
    
    # Get response
    response = db.get_random_response(angel_type)
    if not response:
        await update.message.reply_text("⛔ Sorry, no responses available.")
        return
    
    response_id, response_number, angel_type, text_content, has_image, image_path, language = response
    
    # Log the question
    db.log_question(user_id, angel_type, response_id, text[:200])
    
    # Send response with angel signature
    angel_name = "Seraphiel" if angel_type == 'light' else "Nyxareth"
    angel_emoji = "✨" if angel_type == 'light' else "🖤"
    formatted_response = f"{angel_emoji} *{text_content}*\n\n*- {angel_name}*"
    
    # Try to send with image
    image_sent = False
    if has_image and image_path:
        try:
            if os.path.exists(image_path):
                with open(image_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=formatted_response,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    image_sent = True
                    logger.info(f"Sent image: {image_path}")
