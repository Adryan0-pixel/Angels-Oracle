import os
import sqlite3
import logging
import random
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
import re

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PAYMENT_TOKEN = "2051251535:TEST:OTk5MDA4ODgxLTAwNQ"
DATABASE_PATH = 'angels_bot.db'

SUBSCRIPTIONS = {
    'free': {'name': 'Free', 'questions': 50, 'cooldown': 15, 'price': 0},
    'premium_6m': {'name': '6 Months Premium', 'questions': -1, 'cooldown': 10, 'price': 299},
    'premium_12m': {'name': '12 Months Premium', 'questions': -1, 'cooldown': 5, 'price': 499}
}

# Immagini intro per presentazione angeli
ANGEL_INTRO_IMAGES = {
    'light': "https://i.imgur.com/RN2lEWd.png",
    'dark': "https://i.imgur.com/B21hnsr.png"
}

# Tutte le immagini organizzate per angelo
ANGEL_IMAGES = {
    'light': [
        "https://i.imgur.com/wTKZXU3.png",  # risposta 147
        "https://i.imgur.com/iy3ruwG.png",  # risposta 149
        "https://i.imgur.com/G2JXKMc.png",  # risposta 145
        "https://i.imgur.com/xpDSvlo.png",  # risposta 46
        "https://i.imgur.com/KpRUiMX.png",  # risposta 146
        "https://i.imgur.com/sZMl8o9.png",  # risposta 31
        "https://i.imgur.com/y3w6gjH.png",  # risposta 78
        "https://i.imgur.com/4gc7waA.png",  # risposta 144
        "https://i.imgur.com/R3wEtPE.png",  # risposta 16
        "https://i.imgur.com/QhNHpjy.png",  # risposta 86
        "https://i.imgur.com/lW80y0d.png",  # risposta 27
        "https://i.imgur.com/GbEZ1m8.png",  # risposta 134
        "https://i.imgur.com/XvxWqhF.png",  # risposta 139
        "https://i.imgur.com/gW0UJSW.png",  # risposta 61
        "https://i.imgur.com/qsvq341.png",  # risposta 76
        "https://i.imgur.com/eoFmVj4.png",  # risposta 79
        "https://i.imgur.com/mtIoH3m.png",  # risposta 136
        "https://i.imgur.com/xRYMkP7.png",  # risposta 74
        "https://i.imgur.com/cBSqwvP.png",  # risposta 142
        "https://i.imgur.com/iY8Hzfm.png",  # risposta 143
        "https://i.imgur.com/gurjp20.png",  # risposta 141
        "https://i.imgur.com/FprhPf2.png",  # risposta 140
        "https://i.imgur.com/S1vRJMH.png",  # risposta 137
        "https://i.imgur.com/Tp519mm.png"   # risposta 138
    ],
    'dark': [
        "https://i.imgur.com/RN2lEWd.png",  # risposta 171
        "https://i.imgur.com/B21hnsr.png",  # risposta 176
        "https://i.imgur.com/ScrZU4h.png",  # risposta 119
        "https://i.imgur.com/1Tjk0IF.png",  # risposta 116
        "https://i.imgur.com/LyVDBf5.png",  # risposta 151
        "https://i.imgur.com/idmquVh.png",  # risposta 118
        "https://i.imgur.com/gZEmHby.png",  # risposta 11
        "https://i.imgur.com/ANUmiCm.png",  # risposta 14
        "https://i.imgur.com/56xPxCq.png",  # risposta 13
        "https://i.imgur.com/X3goLsC.png",  # risposta 120
        "https://i.imgur.com/rduetz2.png",  # risposta 112
        "https://i.imgur.com/edXa0WE.png",  # risposta 105
        "https://i.imgur.com/CZDefe4.png",  # risposta 108
        "https://i.imgur.com/h8HWhPB.png",  # risposta 101
        "https://i.imgur.com/Azr3gFp.png",  # risposta 104
        "https://i.imgur.com/Nx7hmOy.png",  # risposta 111
        "https://i.imgur.com/5ZfVK8e.png",  # risposta 32
        "https://i.imgur.com/WSWnR8D.png",  # risposta 42
        "https://i.imgur.com/DHVn9ZN.png",  # risposta 44
        "https://i.imgur.com/GnSJ4Oo.png",  # risposta 45
        "https://i.imgur.com/EOdsyEJ.png",  # risposta 46
        "https://i.imgur.com/rRNJBAK.png",  # risposta 48
        "https://i.imgur.com/Peqrqvk.png",  # risposta 49
        "https://i.imgur.com/I60Bu0x.png"   # risposta 6
    ]
}

def validate_birth_info(text):
    text = text.strip()
    parts = text.split()
    
    if len(parts) < 2:
        return False, "Please provide both your name and birth date. Example: 'Maria 15/03/1990'", None, None
    
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
        return False, "Invalid date format. Please use DD/MM/YYYY format. Example: '15/03/1990'", None, None
    
    if parsed_date > datetime.now():
        return False, "Birth date cannot be in the future. Please enter a valid birth date.", None, None
    
    min_age_date = datetime.now() - timedelta(days=10*365.25)
    if parsed_date > min_age_date:
        return False, "You must be at least 10 years old to use this service.", None, None
    
    max_age_date = datetime.now() - timedelta(days=120*365.25)
    if parsed_date < max_age_date:
        return False, "Please enter a realistic birth date.", None, None
    
    return True, None, name, parsed_date

class SafetyFilters:
    def __init__(self):
        self.forbidden_patterns = [
            r'\b(kill|death|suicide|harm|hurt)\b',
            r'\b(medical|doctor|medicine|drug|pill)\b', 
            r'\b(invest|money|buy|sell|stock|crypto)\b',
            r'\b(marry|divorce|break up|leave him/her)\b',
            r'\b(definitely|certainly|will happen|guaranteed)\b',
            r'\b(never|always|impossible|definitely not)\b'
        ]
    
    def validate_response(self, response: str) -> dict:
        # Check forbidden content
        for pattern in self.forbidden_patterns:
            if re.search(pattern, response.lower()):
                return {
                    'is_safe': False,
                    'reason': f'Contains forbidden pattern: {pattern}'
                }
        
        # Check length
        if len(response) > 200:
            return {
                'is_safe': False,
                'reason': 'Response too long'
            }
        
        # Check if sounds mystical enough
        mystical_score = sum(1 for word in ['divine', 'spiritual', 'energy', 'light', 'shadow', 'wisdom', 'guidance', 'mystery'] 
                           if word in response.lower())
        
        if mystical_score < 1:
            return {
                'is_safe': False,
                'reason': 'Not mystical enough'
            }
        
        return {
            'is_safe': True,
            'content': response
        }

class AngelAISystem:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.safety_filters = SafetyFilters()
        self.fallback_responses = self._load_fallback_responses()
        
    def _load_fallback_responses(self):
        return {
            'light': [
                "Golden light surrounds your path ahead, trust in the divine guidance that flows through you",
                "The angels whisper of hope approaching, open your heart to receive their blessing",
                "Luminous energy flows toward your dreams, have faith in the journey unfolding",
                "Divine protection watches over you, step forward with courage and grace",
                "The morning star illuminates your way, follow its light toward your highest good"
            ],
            'dark': [
                "From shadow's depth emerges hidden wisdom, listen to the whispers of your soul",
                "The night reveals truths daylight conceals, embrace the mystery within",
                "Ancient knowledge stirs in darkness, trust your deepest intuition",
                "The void holds answers for brave seekers, dare to look beyond the surface",
                "Shadow and light dance together within you, honor both sides of your nature"
            ]
        }
    
    async def generate_response(self, angel_type: str, user_question: str, user_name: str, birth_date: str) -> dict:
        if not self.api_key:
            return self._get_fallback_response(angel_type)
        
        try:
            prompt = self._create_prompt(angel_type, user_question, user_name, birth_date)
            ai_response = await self._call_openai(prompt)
            
            # Validate response
            filtered_response = self.safety_filters.validate_response(ai_response)
            
            if not filtered_response['is_safe']:
                logger.warning(f"AI response filtered: {filtered_response['reason']}")
                return self._get_fallback_response(angel_type)
            
            return {
                'success': True,
                'response': filtered_response['content'],
                'method': 'ai',
                'has_image': random.random() < 0.33,  # 1/3 chance for image
                'angel_type': angel_type
            }
            
        except Exception as e:
            logger.warning(f"AI system failed: {e}")
            return self._get_fallback_response(angel_type)
    
    def _create_prompt(self, angel_type: str, question: str, name: str, birth_date: str) -> str:
        angel_config = {
            'light': {
                'name': 'Seraphiel',
                'traits': 'hopeful, protective, warm, encouraging',
                'elements': 'golden light, divine protection, celestial guidance, healing energy',
                'tone': 'uplifting and compassionate'
            },
            'dark': {
                'name': 'Nyxareth', 
                'traits': 'mysterious, intuitive, revealing, transformative',
                'elements': 'shadow wisdom, hidden truths, ancient mysteries, transformative power',
                'tone': 'profound and mystical'
            }
        }
        
        config = angel_config[angel_type]
        
        return f"""You are {config['name']}, the Angel of {'Light' if angel_type == 'light' else 'Darkness'}.

STRICT GUIDELINES:
- Provide mystical guidance in {config['tone']} tone
- Keep response under 35 words
- Use elements: {config['elements']}
- NO specific future predictions
- NO medical, financial, or legal advice  
- Keep language poetic and spiritually ambiguous
- Focus on inner wisdom and personal growth

User: {name} (born {birth_date})
Question: "{question}"

Provide a brief mystical response as {config['name']} that offers spiritual guidance while staying true to your {angel_type} nature."""

    async def _call_openai(self, prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a mystical oracle providing brief spiritual guidance for entertainment purposes only."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 50,
            "temperature": 0.8,
            "presence_penalty": 0.3,
            "frequency_penalty": 0.3
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content'].strip()
                else:
                    raise Exception(f"OpenAI API error: {response.status}")
    
    def _get_fallback_response(self, angel_type: str) -> dict:
        response_text = random.choice(self.fallback_responses[angel_type])
        return {
            'success': True,
            'response': response_text,
            'method': 'fallback',
            'has_image': random.random() < 0.33,
            'angel_type': angel_type
        }

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
    
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
            CREATE TABLE IF NOT EXISTS question_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                angel_type TEXT,
                question_text TEXT,
                response_text TEXT,
                response_method TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
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
    
    def log_question(self, user_id, angel_type, question_text, response_text, response_method):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET questions_used = questions_used + 1, last_question_time = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user_id)
        )
        
        cursor.execute(
            "INSERT INTO question_log (user_id, angel_type, question_text, response_text, response_method) VALUES (?, ?, ?, ?, ?)",
            (user_id, angel_type, question_text[:200], response_text[:300], response_method)
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

# Initialize systems
db = DatabaseManager(DATABASE_PATH)
ai_system = AngelAISystem(OPENAI_API_KEY)

async def start_payment(update, context, plan_type):
    """Avvia il processo di pagamento"""
    prices = [LabeledPrice("Angels Oracle Premium", SUBSCRIPTIONS[plan_type]['price'])]
    
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=f"Angels Oracle {SUBSCRIPTIONS[plan_type]['name']}",
        description="Unlimited questions to both Angels with shorter cooldowns",
        payload=plan_type,
        provider_token=PAYMENT_TOKEN,
        currency="EUR",
        prices=prices
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Risponde alla pre-checkout query"""
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce pagamento completato"""
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    plan_type = payment.invoice_payload
    
    months = 6 if plan_type == 'premium_6m' else 12
    db.update_subscription(user_id, plan_type, months)
    
    await update.message.reply_text(
        f"Payment successful! You now have {SUBSCRIPTIONS[plan_type]['name']} access.\n"
        f"Enjoy unlimited questions with {SUBSCRIPTIONS[plan_type]['cooldown']} minute cooldowns!"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = db.get_or_create_user(user.id, user.username, user.first_name)
    
    if db.has_completed_setup(user.id):
        await show_main_menu(update)
    else:
        await show_setup_screen(update)

async def show_setup_screen(update):
    welcome_text = """Welcome to Angels Oracle Bot!

Receive divine guidance from two mystical angels

To personalize your experience, please provide:
- Your first name
- Your birth date (DD/MM/YYYY)

Example: Maria 15/03/1990

This information is used only for entertainment purposes. All responses are fictional."""
    
    keyboard = [
        [InlineKeyboardButton("How it Works", callback_data='how_it_works')],
        [InlineKeyboardButton("Premium Plans", callback_data='premium')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def show_main_menu(update):
    user_info = db.get_user_info(update.effective_user.id)
    user_name = user_info[0] if user_info else "Seeker"
    
    welcome_text = f"""Welcome back, {user_name}!

Choose your divine guide:

ANGEL OF LIGHT (Seraphiel)
Hope, protection, and divine guidance

ANGEL OF DARKNESS (Nyxareth)
Hidden truths, transformation, and deep wisdom

Free users: 50 questions total, 15min cooldown
Premium users: Unlimited questions + shorter cooldowns

Disclaimer: This is for entertainment purposes only."""
    
    keyboard = [
        [InlineKeyboardButton("Angel of Light", callback_data='angel_light')],
        [InlineKeyboardButton("Angel of Darkness", callback_data='angel_dark')],
        [InlineKeyboardButton("Premium Plans", callback_data='premium')],
        [InlineKeyboardButton("My Status", callback_data='status')],
        [InlineKeyboardButton("Change My Info", callback_data='change_info')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

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
    elif data == 'buy_premium_6m':
        await start_payment(query, context, 'premium_6m')
    elif data == 'buy_premium_12m':
        await start_payment(query, context, 'premium_12m')

async def show_how_it_works(query):
    text = """How Angels Oracle Works

1. Setup: Provide your name and birth date
2. Choose: Select Angel of Light or Darkness  
3. Ask: Type your question
4. Receive: Get personalized divine guidance

The Angels:
Seraphiel (Light) - Hope, healing, protection
Nyxareth (Darkness) - Hidden truths, transformation

Limits:
Free: 50 total questions, 15min cooldown
Premium: Unlimited questions, shorter cooldowns

All responses are generated for entertainment only."""
    
    keyboard = [[InlineKeyboardButton("Back", callback_data='back_to_setup')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_change_info_screen(query):
    text = """Change Your Information

Please provide your updated information:
- Your first name
- Your birth date (DD/MM/YYYY)

Example: John 25/12/1985"""
    
    keyboard = [[InlineKeyboardButton("Cancel", callback_data='back_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_angel_intro(query, angel_type):
    if angel_type == 'light':
        angel_name = "Seraphiel"
        angel_message = "I am Seraphiel, the Angel of Light. I bring hope, protection, and divine wisdom to guide you toward joy and fulfillment."
    else:
        angel_name = "Nyxareth"  
        angel_message = "I am Nyxareth, the Angel of Darkness. I reveal hidden truths and guide your transformation through the mysteries of the shadow realm."
    
    intro_text = f"""{angel_message}

Ask me your question and I will provide divine guidance tailored to your spiritual journey.

Type your question now..."""
    
    # Invia immagine di presentazione dell'angelo
    try:
        intro_image = ANGEL_INTRO_IMAGES[angel_type]
        await query.message.reply_photo(
            photo=intro_image,
            caption=f"{angel_name} appears before you..."
        )
    except Exception as e:
        logger.warning(f"Could not send intro image: {e}")
    
    keyboard = [
        [InlineKeyboardButton("Back to Angels", callback_data='back_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(intro_text, reply_markup=reply_markup)

async def show_premium_plans(query):
    text = """Premium Plans

FREE PLAN
- 50 questions total (shared between angels)
- 15 minutes cooldown between questions

6 MONTHS PREMIUM - €2.99
- Unlimited questions
- 10 minutes cooldown
- Priority support

12 MONTHS PREMIUM - €4.99
- Unlimited questions  
- 5 minutes cooldown
- Priority support

Payments are secure and processed by Telegram"""
    
    keyboard = [
        [InlineKeyboardButton("Buy 6 Months - €2.99", callback_data='buy_premium_6m')],
        [InlineKeyboardButton("Buy 12 Months - €4.99", callback_data='buy_premium_12m')],
        [InlineKeyboardButton("Back", callback_data='back_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

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
    
    status_text = f"""Your Status

Name: {user_name or 'Not set'}
Plan: {sub_info['name']}
Questions Used: {questions_used}
Questions Remaining: {remaining}
Cooldown: {sub_info['cooldown']} minutes"""
    
    if not db.check_cooldown(user_id):
        minutes_left = db.get_time_until_next_question(user_id)
        status_text += f"\n\nNext question in: {minutes_left} minutes"
    
    keyboard = [
        [InlineKeyboardButton("Upgrade to Premium", callback_data='premium')],
        [InlineKeyboardButton("Back", callback_data='back_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(status_text, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if not db.has_completed_setup(user_id) or context.user_data.get('changing_info', False):
        is_valid, error_msg, name, birth_date = validate_birth_info(text)
        
        if not is_valid:
            await update.message.reply_text(f"Error: {error_msg}")
            return
        
        db.update_user_info(user_id, name, birth_date)
        
        if context.user_data.get('changing_info', False):
            context.user_data['changing_info'] = False
            await update.message.reply_text(f"Your information has been updated successfully, {name}!")
            await show_main_menu(update)
        else:
            await update.message.reply_text(f"Welcome, {name}! Your birth information has been recorded.")
            await show_main_menu(update)
        return
    
    if 'selected_angel' not in context.user_data:
        keyboard = [
            [InlineKeyboardButton("Angel of Light", callback_data='angel_light')],
            [InlineKeyboardButton("Angel of Darkness", callback_data='angel_dark')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Please choose your Angel first!",
            reply_markup=reply_markup
        )
        return
    
    angel_type = context.user_data['selected_angel']
    
    # Check question limits
    if not db.can_ask_question(user_id):
        await update.message.reply_text(
            "You have reached your question limit!\n\nUpgrade to Premium for unlimited questions:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("View Premium Plans", callback_data='premium')]
            ])
        )
        return
    
    # Check cooldown
    if not db.check_cooldown(user_id):
        minutes_left = db.get_time_until_next_question(user_id)
        angel_name = "Seraphiel" if angel_type == 'light' else "Nyxareth"
        await update.message.reply_text(
            f"{angel_name} needs {minutes_left} more minutes to restore divine energy.\n\nUpgrade to Premium for shorter cooldowns!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("View Premium Plans", callback_data='premium')]
            ])
        )
        return
    
    # Get user info for AI
    user_info = db.get_user_info(user_id)
    if not user_info:
        await update.message.reply_text("Please complete setup first with /start")
        return
    
    user_name, birth_date_str = user_info
    
    # Generate AI response
    response_data = await ai_system.generate_response(angel_type, text, user_name, birth_date_str)
    
    # Log the question and response
    db.log_question(user_id, angel_type, text, response_data['response'], response_data['method'])
    
    # Send response
    angel_name = "Seraphiel" if angel_type == 'light' else "Nyxareth"
    formatted_response = f"*{response_data['response']}*\n\n- {angel_name}"
    
    await update.message.reply_text(formatted_response, parse_mode=ParseMode.MARKDOWN)
    
    # Send mystical image if response includes one
    if response_data['has_image']:
        try:
            selected_image = random.choice(ANGEL_IMAGES[angel_type])
            await update.message.reply_photo(
                photo=selected_image,
                caption=f"A vision from {angel_name} appears before you..."
            )
        except Exception as e:
            logger.warning(f"Could not send image: {e}")
    
    # Send mystical audio using GitHub raw URLs
    audio_urls = {
        'light': "https://raw.githubusercontent.com/Adryan0x-pixel/Angels-Oracle/main/sounds/light_angel.ogg",
        'dark': "https://raw.githubusercontent.com/Adryan0x-pixel/Angels-Oracle/main/sounds/dark_angel.ogg"
    }
    
    try:
        audio_url = audio_urls.get(angel_type)
        if audio_url:
            # Invia come voice message per migliore esperienza utente
            await update.message.reply_voice(
                voice=audio_url,
                caption=f"{angel_name}'s divine energy resonates..."
            )
    except Exception as e:
        logger.warning(f"Could not send audio: {e}")
        # Fallback: prova come audio normale se voice fallisce
        try:
            await update.message.reply_audio(
                audio=audio_url,
                caption=f"{angel_name}'s divine energy"
            )
        except Exception as e2:
            logger.warning(f"Audio fallback also failed: {e2}")
    
    # Navigation buttons
    keyboard = [
        [InlineKeyboardButton(f"Ask {angel_name} Again", callback_data=f'angel_{angel_type}')],
        [InlineKeyboardButton("Switch Angel", callback_data='back_main')],
        [InlineKeyboardButton("Upgrade Premium", callback_data='premium')]
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
    
    # Log configuration status
    if OPENAI_API_KEY:
        logger.info("OpenAI API key found - AI responses enabled")
    else:
        logger.warning("OpenAI API key not found - using fallback responses only")
    
    if PAYMENT_TOKEN:
        logger.info("Payment token found - payments enabled")
    else:
        logger.warning("Payment token not found - payments disabled")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    logger.info("Angels Oracle AI Bot started successfully!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
