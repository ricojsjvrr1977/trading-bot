import telebot
import os
import psycopg2
from telebot import types
from datetime import datetime
from flask import Flask, request

# Configuración de la base de datos
DB_URL = os.getenv("DB_URL", "postgresql://postgres:dhFTmlmpvcveKIINwsRIGaszgwDWfERR@autorack.proxy.rlwy.net:39614/railway")

# Configuración del bot de Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7467249877:AAEHXU8hwa0V-4gyIpeVC1ge13-ynAbP0_A")

# Inicialización del bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Inicialización de la aplicación Flask
app = Flask(__name__)

# Conexión a la base de datos
def connect_db():
    try:
        conn = psycopg2.connect(DB_URL)
        print("👌 Conexión exitosa a la base de datos.")
        return conn
    except Exception as e:
        print(f"❌ Error conectándose a la base de datos: {e}")
        return None

# Guardar el Telegram ID del usuario
def save_telegram_user(user_id, first_name, last_name, username, telegram_id, plan=None, tickers=None, email=None):
    try:
        conn = connect_db()
        if not conn:
            return

        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM users WHERE user_id = %s;
            """, (user_id,))
            exists = cur.fetchone()[0]

            if exists == 0:
                cur.execute("""
                    INSERT INTO users (user_id, first_name, last_name, username, telegram_id, plan, tickers, email) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    user_id, 
                    first_name, 
                    last_name, 
                    username, 
                    telegram_id,
                    plan or 'Pendiente',
                    tickers or '',
                    email or ''
                ))
                conn.commit()
                print(f"👌 Usuario {first_name} {last_name} registrado con éxito.")
            else:
                print(f"⚠️ El usuario {first_name} {last_name} ya está registrado.")
    except Exception as e:
        print(f"❌ Error al guardar el usuario: {e}")
    finally:
        if conn:
            conn.close()

# Funcíón para mostrar el disclaimer completo
@bot.message_handler(commands=['start'])
def send_welcome_with_disclaimer(message):
    chat_id = message.chat.id
    first_name = message.chat.first_name
    last_name = message.chat.last_name
    username = message.chat.username

    conn = connect_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM users WHERE user_id = %s;
        """, (chat_id,))
        exists = cur.fetchone()[0]
        if exists == 0:
            disclaimer_message = f"""
            🌟 *¡Gracias por la confianza en nosotros, {first_name}! ¡Te damos la bienvenida a nuestra familia!*

            🎉 ¡Bienvenido/a al Sistema de Señales de Trading de *Latino Swing Trading*! 🚀

            📈 Con nosotros, estarás un paso más cerca de tomar decisiones de inversión informadas, ¡y lo mejor es que te ayudamos a hacerlo de forma *automatizada*, precisa y oportuna!

            ✅ *Al usar este bot, aceptas que comprendes los riesgos y estás de acuerdo con estos términos.*
            """
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            accept_button = types.KeyboardButton("Sí, he leído y entiendo los riesgos")
            decline_button = types.KeyboardButton("No, gracias")
            markup.add(accept_button, decline_button)

            bot.send_message(chat_id, disclaimer_message, parse_mode='Markdown')
            bot.send_message(chat_id, "Por favor, confirma si has leído y entendido los riesgos asociados.", reply_markup=markup)

# Continuar con el flujo de selección de plan
def ask_for_plan(chat_id):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    plan_boton = types.KeyboardButton("Plan Básico")
    plan_avanzado_boton = types.KeyboardButton("Plan Avanzado")
    markup.add(plan_boton, plan_avanzado_boton)
    bot.send_message(chat_id, "Por favor, selecciona tu plan de trading:", reply_markup=markup)

# Enviar link de pago
def send_payment_link(chat_id, plan):
    if plan == 'Plan Básico':
        payment_link = "https://www.paypal.com/ncp/payment/69XUA69WNW88N"
    else:
        payment_link = "https://www.paypal.com/ncp/payment/L2EAYV77BQS6S"

    bot.send_message(chat_id, f"Gracias por tu preferencia. Aquí está tu link de pago: {payment_link}")

# Endpoint del webhook para Telegram
@app.route('/paypal-webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = telebot.types.Update.de_json(request.get_json(force=True))
        bot.process_new_updates([update])
        return 'OK', 200
    except Exception as e:
        print(f"❌ Error al procesar el webhook de Telegram: {e}")
        return 'Internal Server Error', 500

# Configurar webhook
def start_webhook():
    webhook_url = 'https://tradingbot-production-1412.up.railway.app/paypal-webhook'
    try:
        print("🔄 Eliminando webhook existente...")
        bot.remove_webhook()
        print("🟢 Configurando nuevo webhook...")
        result = bot.set_webhook(url=webhook_url)
        print(f"🟢 Webhook configurado correctamente: {result}")
    except Exception as e:
        print(f"❌ Error configurando el webhook: {e}")

if __name__ == "__main__":
    start_webhook()
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
