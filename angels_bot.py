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
        
        # Responses table - MODIFICATA per includere response_number
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
        """Trova il percorso corretto dell'immagine basandosi sui tuoi nomi file"""
        if angel_type == 'light':
            folder = "luce"
        else:  # dark
            folder = "OSCURITÀ"
        
        # Prova diverse estensioni e formati di nome
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
        
        return None  # Nessuna immagine trovata
    
    def populate_responses(self):
        """Populate responses if empty - AGGIORNATA con i tuoi numeri di risposta"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if responses already exist
        cursor.execute("SELECT COUNT(*) FROM responses")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # Angel of Light responses - CON I NUMERI DELLE TUE IMMAGINI
        light_responses = [
            (16, "Vedo ali di luce proteggerti nel tuo viaggio, confida nella protezione divina", True),
            (27, "Una porta dorata si sta aprendo davanti a te, varcala con speranza e gratitudine", True),
            (31, "A golden thread weaves through your destiny, follow it with trust and wonder", True),
            (46, "I see golden rain falling on your garden, let abundance grow in every corner", True),
            (61, "Heaven's gate opens wider with each kind act, step through with generosity", True),
            (74, "The sail of your dreams catches winds of opportunity, navigate toward your goals", True),
            (76, "Sunrise paints your tomorrow with colors of possibility, wake to new chances", True),
            (78, "Rainbows arch over your trials with promises of beauty, look up after storms", True),
            (79, "Butterflies carry wishes on gossamer wings to the divine, release your desires", True),
            (86, "Your guardian's wings cast shadows of protection, rest in their shelter", True),
            (121, "Starlight weaves silver threads through your dreams, follow them to manifest reality", True),
            (122, "Moonbeams paint pathways across your night sky, walk them toward your destiny", True),
            (124, "Candlelight flickers with messages of hope, interpret their dancing shadows", True),
            (126, "Angels collect your tears in crystal vials, transforming sorrow into wisdom", True),
            (132, "The golden fleece awaits your heroic journey, embark on your personal quest", True),
            (133, "The holy grail fills with whatever you truly need, drink from your authentic desires", True),
            (134, "The philosopher's stone transforms your lead experiences into gold, embrace alchemy", True),
            (136, "White horses carry your prayers across celestial plains, mount them with faith", True),
            (137, "Doves deliver messages between earth and heaven, send your requests upward", True),
            (138, "Eagles soar with visions of your highest potential, spread your wings and follow", True),
            (139, "Swans glide gracefully through turbulent waters, embody their serene elegance", True),
            (140, "Peacocks display your true colors with pride, show your authentic beauty", True),
            (141, "Crystal caves echo with sounds of your healing, enter them with reverence", True),
            (142, "Sacred springs bubble with waters of renewal, bathe in their restorative power", True),
            (143, "Holy mountains offer perspectives from above, climb them for expanded vision", True),
            (144, "Blessed valleys provide shelter from life's storms, rest in their protective embrace", True),
            (145, "Enchanted forests whisper secrets of growth, listen to their ancient wisdom", True),
            (146, "Your inner sun never sets on love's horizon, let it shine without eclipse", True),
            (147, "Your spiritual compass always points toward truth, follow its unwavering direction", True),
            (149, "Your heart's garden blooms with flowers of compassion, tend them with kindness", True),
            # Aggiungi risposte senza immagine per completare
            (1, "Vedo una luce dorata nel tuo futuro, lascia che ti guidi verso la gioia", False),
            (2, "La stella del mattino mi rivela che la speranza si avvicina, abbi fiducia nel tuo cuore", False),
            (3, "Il vento luminoso ti sussurra che la pazienza sarà premiata, benedici questo momento", False),
            (4, "La luce che è in te brillerà più forte, preparati ad accogliere la grazia", False),
            (5, "Un ponte di luce si sta costruendo per te, attraversalo con coraggio e fiducia", False),
        ]
        
        # Angel of Darkness responses - CON I NUMERI DELLE TUE IMMAGINI  
        dark_responses = [
            (6, "Le ombre danzanti mi mostrano che devi guardare oltre l'apparenza, trova la verità nascosta", True),
            (11, "La luna crescente rivela che la tua trasformazione è iniziata, abbraccia ciò che diventerai", True),
            (13, "La luna piena rivela che la tua forza è al culmine, abbraccia il tuo potere", True), 
            (14, "La luna nuova rivela che un nuovo ciclo inizia, abbraccia l'ignoto", True),
            (32, "Dalle ombre del tempo emerge che la verità si rivelerà, ascolta il tuo istinto", True),
            (37, "The black mirror shows your hidden strengths, look deeper than surface fears", True),
            (41, "Raven wings carry messages from your depths, decode the symbols they bring", True),
            (42, "Wolf howls echo your primal knowing, remember the wildness you've forgotten", True),
            (44, "Spider webs show intricate connections, weave the pattern that calls you", True),
            (45, "Owl eyes pierce through illusion's veil, see the truth others fear to face", True),
            (46, "In the cavern of your unconscious, treasures wait for the bold explorer", True),
            (48, "In the forest of your dreams, wisdom grows for the patient wanderer", True),
            (49, "In the ocean of your emotions, pearls form for the deep diver", True),
            (67, "Your dark twin whispers truths you fear to hear, listen with courageous ears", True),
            (94, "Below the noise of constant chatter, profound silence holds deep answers", True),
            (101, "The cauldron of transformation bubbles with your becoming, stir it with intention", True),
            (104, "The pentacle of protection shields your vulnerability, invoke it when needed", True),
            (105, "Dusk contemplations prepare you for night's teachings, welcome the darkness", True),
            (108, "Dawn reflections merge shadow and light within you, embrace your complexity", True),
            (111, "The underworld rivers carry messages from your depths, decode their meaning", True),
            (112, "The shadow realm mirrors show inverted truths, read them backwards", True),
            (116, "Your inner vampire thirsts for authentic experience, feed it real encounters", True),
            (118, "Your secret witch brews potions of possibility, trust her ancient recipes", True),
            (119, "Your dormant dragon guards treasures of power, awaken it with courage", True),
            (120, "Your sleeping phoenix prepares for rebirth through flames, surrender to transformation", True),
            (151, "Obsidian mirrors reflect not your face but your potential, gaze into tomorrow's self", True),
            (155, "Tourmaline transmutes chaos into creative force, harness the storm within you", True),
            (165, "Antidotes hide within the very substances that harm, seek wisdom in opposition", True),
            (171, "Raven caws prophecy from skeletal branches, interpret the omens they deliver", True),
            (176, "The void pregnant with infinite potential calls you, enter the fertile nothingness", True),
            # Aggiungi risposte senza immagine per completare
            (1, "Dalle profondità della notte emerge che il mistero si svelerà, ascolta la tua intuizione", False),
            (2, "I sussurri delle ombre parlano di segreti per te, preparati a scoprire l'inaspettato", False),
            (3, "Nel calice dell'ombra si mescola il tuo futuro, bevi con consapevolezza", False),
            (4, "Le radici profonde della tua anima si stanno rafforzando, nutri la crescita interiore", False),
            (5, "From midnight's embrace comes the gift of solitude, learn what silence teaches", False),
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
        logger.info(f"Database popolato con {len(light_responses)} risposte luce e {len(dark_responses)} risposte oscurità")
    
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
    
    welcome_text = """🌟 Benvenuto nel Bot Oracolo degli Angeli! 🌙

Scegli la tua guida divina:
✨ **Angelo di Luce** - Speranza, protezione e guida  
🖤 **Angelo dell'Oscurità** - Verità nascoste, trasformazione e saggezza profonda

**Come funziona:**
1. Scegli il tuo Angelo
2. Condividi nome e data di nascita (per personalizzare)  
3. Fai la tua domanda
4. Ricevi la guida divina

**Utenti gratuiti:** 50 domande totali
**Utenti premium:** Domande illimitate + tempi di attesa ridotti

⚠️ *Disclaimer: Questo è solo per intrattenimento. Le risposte non sono vera guida spirituale.*"""
    
    keyboard = [
        [InlineKeyboardButton("✨ Angelo di Luce", callback_data='angel_light')],
        [InlineKeyboardButton("🖤 Angelo dell'Oscurità", callback_data='angel_dark')],
        [InlineKeyboardButton("💎 Piani Premium", callback_data='premium')],
        [InlineKeyboardButton("ℹ️ Il Mio Stato", callback_data='status')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

# [Il resto delle funzioni rimane identico al codice originale...]
# [Continuo con le altre funzioni senza modifiche...]

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
            angel_message = "Io sono Seraphiel, l'Angelo di Luce. Sono qui per guidarti verso speranza, protezione e saggezza divina."
            angel_emoji = "✨"
        else:
            angel_name = "Nyxareth"
            angel_message = "Io sono Nyxareth, l'Angelo dell'Oscurità. Sono qui per mostrarti verità nascoste e guidare la tua trasformazione."
            angel_emoji = "🖤"
        
        intro_text = f"{angel_emoji} **{angel_message}** {angel_emoji}\n\n" \
                    f"Per favore condividi il tuo nome di battesimo e data di nascita per una guida personalizzata:\n" \
                    f"Esempio: 'Maria 15/03/1990'\n\n" \
                    f"Poi fai la tua domanda e ricevi la saggezza divina!"
        
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
            await query.edit_message_text("💳 Sistema pagamenti non configurato. Contatta il supporto.")
    
    elif data == 'back_main':
        await start_from_callback(query, context)

# [Continuo con tutte le altre funzioni identiche al codice originale...]
# [Per brevità includo solo le funzioni principali, il resto rimane uguale]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Check if user has selected an angel
    if 'selected_angel' not in context.user_data:
        keyboard = [
            [InlineKeyboardButton("✨ Angelo di Luce", callback_data='angel_light')],
            [InlineKeyboardButton("🖤 Angelo dell'Oscurità", callback_data='angel_dark')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Per favore scegli prima il tuo Angelo! 🌟",
            reply_markup=reply_markup
        )
        return
    
    # [Il resto della logica rimane identica...]
    # Get response
    response = db.get_random_response(context.user_data['selected_angel'])
    if not response:
        await update.message.reply_text("⛔ Spiacente, nessuna risposta disponibile.")
        return
    
    # MODIFICATO: ora usiamo i campi corretti dal database
    response_id, response_number, angel_type, text_content, has_image, image_path, language = response
    
    # Log the question
    db.log_question(user_id, angel_type, response_id, text[:200])
    
    # Send response with angel signature
    angel_name = "Seraphiel" if angel_type == 'light' else "Nyxareth"
    angel_emoji = "✨" if angel_type == 'light' else "🖤"
    formatted_response = f"{angel_emoji} *{text_content}*\n\n*- {angel_name}*"
    
    # Try to send with image - MIGLIORATA la gestione delle immagini
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
                    logger.info(f"Inviata immagine: {image_path}")
            else:
                logger.warning(f"Immagine non trovata: {image_path}")
        except Exception as e:
            logger.warning(f"Errore invio immagine {image_path}: {e}")
    
    # Send text if image failed or no image
    if not image_sent:
        await update.message.reply_text(formatted_response, parse_mode=ParseMode.MARKDOWN)
    
    # Show options for next action
    keyboard = [
        [InlineKeyboardButton(f"Chiedi di nuovo a {angel_name}", callback_data=f'angel_{angel_type}')],
        [InlineKeyboardButton("Cambia Angelo", callback_data='back_main')],
        [InlineKeyboardButton("💎 Premium", callback_data='premium')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Le energie divine hanno parlato. Cosa vorresti fare ora?",
        reply_markup=reply_markup
    )

# [Tutte le altre funzioni rimangono identiche...]
# [Per brevità non le riscrivo, ma vanno incluse nel file finale]

def main():
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Payment handlers (only if payment token is available)
    if PAYMENT_TOKEN:
        application.add_handler(PreCheckoutQueryHandler(lambda update, context: update.pre_checkout_query.answer(ok=True)))
        application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, lambda update, context: update.message.reply_text("🎉 Pagamento riuscito! 🎉")))
    
    logger.info("Bot Oracolo degli Angeli avviato con successo!")
    
    # Start the bot
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()