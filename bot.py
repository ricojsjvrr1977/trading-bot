import telebot
import os
import psycopg2
from telebot import types
from datetime import datetime

# Configuración de la base de datos
DB_URL = 'postgresql://postgres:dhFTmlmpvcveKIINwsRIGaszgwDWfERR@autorack.proxy.rlwy.net:39614/railway'

# Configuración del bot de Telegram
TELEGRAM_BOT_TOKEN = '7467249877:AAEHXU8hwa0V-4gyIpeVC1ge13-ynAbP0_A'

# Inicialización del bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Conexión a la base de datos
def connect_db():
    try:
        conn = psycopg2.connect(DB_URL)
        print("✅ Conexión exitosa a la base de datos.")
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
                print(f"✅ Usuario {first_name} {last_name} registrado con éxito.")
            else:
                print(f"⚠️ El usuario {first_name} {last_name} ya está registrado.")
    except Exception as e:
        print(f"❌ Error al guardar el usuario: {e}")
    finally:
        if conn:
            conn.close()

# Función para mostrar el disclaimer completo
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
            bot.register_next_step_handler(message, process_disclaimer_response)
        else:
            bot.send_message(chat_id, "¡Ya estás registrado! Vamos a continuar con la selección de tu plan y tickers.")
            ask_for_plan(chat_id)

# Procesar respuesta al disclaimer
def process_disclaimer_response(message):
    chat_id = message.chat.id
    if message.text == "Sí, he leído y entiendo los riesgos":
        bot.send_message(chat_id, "Gracias por aceptar los términos. Ahora, por favor, selecciona tu plan:")
        ask_for_plan(chat_id)
    else:
        bot.send_message(chat_id, "Gracias por tu tiempo. ¡Hasta pronto! 👋")

# Continuar con el flujo de selección de plan
def ask_for_plan(chat_id):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    plan_boton = types.KeyboardButton("Plan Básico")
    plan_avanzado_boton = types.KeyboardButton("Plan Avanzado")
    markup.add(plan_boton, plan_avanzado_boton)
    bot.send_message(chat_id, "Por favor, selecciona tu plan de trading:", reply_markup=markup)

def handle_tickers(message, plan):
    tickers = message.text.split(',')
    tickers = [ticker.strip() for ticker in tickers]

    if plan == "Plan Básico" and len(tickers) > 4:
        bot.send_message(message.chat.id, "⚠️ El Plan Básico solo permite un máximo de 4 tickers.")
    elif plan == "Plan Avanzado" and len(tickers) > 8:
        bot.send_message(message.chat.id, "⚠️ El Plan Avanzado solo permite un máximo de 8 tickers.")

    bot.send_message(message.chat.id, f"Por favor, asegúrate de que los tickers sean correctos: {', '.join(tickers)}.")
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Sí", "No")
    bot.send_message(message.chat.id, "¿Estás seguro de que los tickers son correctos?", reply_markup=markup)

# Enviar link de pago
def send_payment_link(chat_id, plan):
    if plan == 'Plan Básico':
        payment_link = "https://www.paypal.com/ncp/payment/69XUA69WNW88N"
    else:
        payment_link = "https://www.paypal.com/ncp/payment/L2EAYV77BQS6S"

    bot.send_message(chat_id, f"Gracias por tu preferencia. Aquí está tu link de pago: {payment_link}")

# Configurar webhook
def start_webhook():
    webhook_url = 'https://tradingbot-production-1412.up.railway.app/paypal-webhook'
    print("🔄 Eliminando webhook existente...")
    bot.remove_webhook()
    print("🟢 Configurando nuevo webhook...")
    bot.set_webhook(url=webhook_url)

if __name__ == "__main__":
    start_webhook()
