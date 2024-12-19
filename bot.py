import telebot
import os
import psycopg2
from telebot import types
from flask import Flask, request

# ---------------------------------------
# 🔐 Configuración de la base de datos
# ---------------------------------------
DB_URL = os.getenv("DB_URL")

# ---------------------------------------
# 🔐 Configuración del bot de Telegram
# ---------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# ---------------------------------------
# 🌐 Inicialización de la aplicación Flask
# ---------------------------------------
app = Flask(__name__)

# ---------------------------------------
# 📡 Conexión a la base de datos
# ---------------------------------------
def connect_db():
    try:
        conn = psycopg2.connect(DB_URL)
        print("✅ Conexión exitosa a la base de datos.")
        return conn
    except Exception as e:
        print(f"❌ Error conectándose a la base de datos: {e}")
        return None

# ---------------------------------------
# 📦 Guardar el Telegram ID del usuario
# ---------------------------------------
def save_telegram_user(user_id, first_name, last_name, username, telegram_id, plan=None, tickers=None, email=None):
    try:
        conn = connect_db()
        if not conn:
            return

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE user_id = %s;", (user_id,))
            exists = cur.fetchone()[0]

            if exists == 0:
                cur.execute("""
                    INSERT INTO users (user_id, first_name, last_name, username, telegram_id, plan, tickers, email) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, (user_id, first_name, last_name, username, telegram_id, plan or 'Pendiente', tickers or '', email or ''))
                conn.commit()
                print(f"✅ Usuario registrado con éxito. ID de usuario: {user_id}")
    except Exception as e:
        print(f"❌ Error al guardar el usuario: {e}")
    finally:
        if conn:
            conn.close()

# ---------------------------------------
# 📜 Mostrar el disclaimer completo
# ---------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome_with_disclaimer(message):
    chat_id = message.chat.id
    first_name = message.chat.first_name
    last_name = message.chat.last_name
    username = message.chat.username

    conn = connect_db()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users WHERE user_id = %s;", (chat_id,))
                exists = cur.fetchone()[0]

                if exists == 0:
                    disclaimer_message = f"""
                    🌟 *¡Gracias por la confianza en nosotros, {first_name}! ¡Te damos la bienvenida a nuestra familia!*
                    """
                    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                    markup.add(types.KeyboardButton("Sí, he leído y entiendo los riesgos"))
                    bot.send_message(chat_id, disclaimer_message, parse_mode='Markdown')
        except Exception as e:
            print(f"❌ Error en send_welcome_with_disclaimer: {e}")
        finally:
            conn.close()

# ---------------------------------------
# 🌐 Endpoint del webhook de Telegram
# ---------------------------------------
@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = telebot.types.Update.de_json(request.get_json(force=True))
        bot.process_new_updates([update])
        return 'OK', 200
    except Exception as e:
        print(f"❌ Error al procesar el webhook de Telegram: {e}")
        return 'Internal Server Error', 500

# ---------------------------------------
# 🔗 Configurar webhook
# ---------------------------------------
def start_webhook():
    webhook_url = 'https://tradingbot-production-1412.up.railway.app/telegram-webhook'
    try:
        current_webhook_info = bot.get_webhook_info()
        if not current_webhook_info.url or current_webhook_info.url != webhook_url:
            print("🔄 Configurando nuevo webhook...")
            bot.set_webhook(url=webhook_url)
            print(f"🟢 Webhook configurado correctamente: {webhook_url}")
        else:
            print(f"✅ El webhook ya está configurado: {webhook_url}")
    except Exception as e:
        print(f"❌ Error configurando el webhook: {e}")

# ---------------------------------------
# 🚀 Iniciar la aplicación
# ---------------------------------------
if __name__ == "__main__":
    start_webhook()
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
