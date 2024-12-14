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

        # Verificar si el usuario ya existe
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM users WHERE user_id = %s;
            """, (user_id,))
            exists = cur.fetchone()[0]

            if exists == 0:
                # Si no existe, insertamos el usuario
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

    disclaimer_message = f"""
    🌟 *¡Gracias por la confianza en nosotros, {first_name}! ¡Te damos la bienvenida a nuestra familia!*

    🎉 ¡Bienvenido/a al Sistema de Señales de Trading de *Latino Swing Trading*! 🚀

    📈 Con nosotros, estarás un paso más cerca de tomar decisiones de inversión informadas, ¡y lo mejor es que te ayudamos a hacerlo de forma *automatizada*, precisa y oportuna!

    🔹 Nuestro objetivo es brindarte las herramientas necesarias para maximizar tu rendimiento. ¡Aquí recibirás señales de trading **confiables y oportunas**! 🎯

    📢 *¡No olvides seguirnos en nuestras redes sociales para estar al día con todas las novedades y consejos!* 

    ➡️ Instagram: [@latinoswingtrading](https://www.instagram.com/latinoswingtrading) 
    ➡️ TikTok: [@latinosswingtrading](https://www.tiktok.com/@latinosswingtrading) 

    🔹 **Antes de continuar, revisa este aviso importante:**

    ⚠️ *Aviso de Riesgo* ⚠️
    ⚠️ *Advertencia de riesgo* ⚠️
    Invertir en el mercado de valores implica riesgos significativos, incluyendo la posible pérdida de su capital. Los precios de las acciones son altamente volátiles y están influenciados por condiciones del mercado, factores económicos y eventos imprevistos.

    📚 *Propósito de respaldo* 📚
    Los análisis y señales proporcionados por esta herramienta son únicamente para fines informativos y de respaldo. No deben considerarse como asesoramiento financiero ni como una recomendación final para comprar, vender o mantener ningún valor.

    💡 *Responsabilidad del usuario* 💡
    Los usuarios son los únicos responsables de sus decisiones de inversión. Recomendamos encarecidamente que realice su propia investigación y consulte con un asesor financiero licenciado para evaluar su tolerancia al riesgo y sus objetivos de inversión.

    ✅ *Al usar este bot, aceptas que comprendes los riesgos y estás de acuerdo con estos términos.*
    """

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    accept_button = types.KeyboardButton("Sí, he leído y entiendo los riesgos")
    decline_button = types.KeyboardButton("No, gracias")
    markup.add(accept_button, decline_button)

    bot.send_message(chat_id, disclaimer_message, parse_mode='Markdown')
    bot.send_message(chat_id, "Por favor, confirma si has leído y entendido los riesgos asociados.", reply_markup=markup)
    bot.register_next_step_handler(message, process_disclaimer_response)

# Procesar respuesta al disclaimer
def process_disclaimer_response(message):
    chat_id = message.chat.id
    if message.text == "Sí, he leído y entiendo los riesgos":
        bot.send_message(chat_id, "Gracias por aceptar los términos. Ahora, por favor, ingresa tu primer nombre:")
        bot.register_next_step_handler(message, process_first_name)
    else:
        bot.send_message(chat_id, "Gracias por tu tiempo. Si deseas reconsiderar los riesgos, por favor intenta registrarte nuevamente más tarde.")
        bot.send_message(chat_id, "Te deseamos lo mejor en tus decisiones de inversión. ¡Hasta pronto! 👋")

# Pedir nombre y apellido manualmente
def process_first_name(message):
    chat_id = message.chat.id
    first_name = message.text.strip()
    bot.send_message(chat_id, "Ahora, por favor ingresa tu apellido.")
    bot.register_next_step_handler(message, process_last_name, first_name)

def process_last_name(message, first_name):
    chat_id = message.chat.id
    last_name = message.text.strip()
    
    # Guardar el nombre completo en la base de datos
    save_telegram_user(chat_id, first_name, last_name, message.chat.username, chat_id)
    
    # Pedir el correo electrónico
    bot.send_message(chat_id, "Ahora, por favor ingresa tu correo electrónico:")
    bot.register_next_step_handler(message, process_email, first_name, last_name)

def process_email(message, first_name, last_name):
    email = message.text.strip()

    # Guardar el correo electrónico
    save_telegram_user(message.chat.id, first_name, last_name, message.chat.username, message.chat.id, email=email)
    
    # Continuar con el proceso de elegir un plan
    ask_for_plan(message.chat.id)

def ask_for_plan(chat_id):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    plan_boton = types.KeyboardButton("Plan Básico")
    plan_avanzado_boton = types.KeyboardButton("Plan Avanzado")
    markup.add(plan_boton, plan_avanzado_boton)
    bot.send_message(chat_id, "Por favor, selecciona tu plan de trading:", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text in ['Plan Básico', 'Plan Avanzado'])
    def handle_plan(message):
        plan = message.text
        bot.send_message(message.chat.id, f"Has seleccionado el {plan}. Ahora, por favor, ingresa los tickers (separados por comas seguido de espacios despues de cada coma, Ejemplo: AAPL, MSFT, TSLA).")
        bot.register_next_step_handler(message, handle_tickers, plan)

def handle_tickers(message, plan):
    tickers = message.text.split(',')
    tickers = [ticker.strip() for ticker in tickers]

    # Validar el número de tickers según el plan
    if plan == "Plan Básico" and len(tickers) > 4:
        bot.send_message(message.chat.id, "⚠️ ¡Advertencia! El Plan Básico solo permite un máximo de 4 tickers. Por favor, ingresa hasta 4 tickers.")
        bot.send_message(message.chat.id, "Por favor, ingresa los tickers separados por comas (Ejemplo: AAPL, MSFT, TSLA).")
        bot.register_next_step_handler(message, handle_tickers, plan)
        return
    elif plan == "Plan Avanzado" and len(tickers) > 8:
        bot.send_message(message.chat.id, "⚠️ ¡Advertencia! El Plan Avanzado solo permite un máximo de 8 tickers. Por favor, ingresa hasta 8 tickers.")
        bot.send_message(message.chat.id, "Por favor, ingresa los tickers separados por comas (Ejemplo: AAPL, MSFT, TSLA).")
        bot.register_next_step_handler(message, handle_tickers, plan)
        return

    bot.send_message(message.chat.id, f"Por favor, asegúrate de que los tickers sean correctos: {', '.join(tickers)}.\n")
    example_message = (
        "Ejemplo: AAPL, MSFT, TSLA\n\n"
        "Por favor, asegúrate de separar los tickers con comas (Ejemplo: AAPL, MSFT, TSLA)."
    )
    bot.send_message(message.chat.id, example_message)

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    yes_button = types.KeyboardButton("Sí")
    no_button = types.KeyboardButton("No")
    markup.add(yes_button, no_button)
    bot.send_message(message.chat.id, "¿Estás seguro de que los tickers son correctos?", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text in ['Sí', 'No'])
    def confirm_tickers(message):
        if message.text == 'Sí':
            save_telegram_user(message.chat.id, message.chat.first_name, message.chat.last_name, message.chat.username, message.chat.id, plan, ', '.join(tickers))
            bot.send_message(message.chat.id, "¡Los tickers han sido guardados exitosamente!")
            send_payment_link(message.chat.id, plan)
        else:
            bot.send_message(message.chat.id, "Por favor, ingresa los tickers nuevamente.")
            bot.send_message(message.chat.id, "Por favor, ingresa los tickers separados por comas (Ejemplo: AAPL, MSFT, TSLA).")
            bot.register_next_step_handler(message, handle_tickers, plan)

def send_payment_link(chat_id, plan):
    if plan == 'Plan Básico':
        payment_link = "https://www.paypal.com/ncp/payment/69XUA69WNW88N"
    else:
        payment_link = "https://www.paypal.com/ncp/payment/L2EAYV77BQS6S"

    bot.send_message(chat_id, f"Gracias por tu preferencia. Aquí está tu link de pago: {payment_link}")
    bot.send_message(chat_id, "Este es tu link de pago de acuerdo al plan que has seleccionado. Tenlo por aquí en cuenta, una vez tu periodo de prueba gratuita esté por concluir, te enviaremos un recordatorio con tu nuevo link de pago.")

# Actualización del webhook en vez de polling
if __name__ == "__main__":
    # Configurar webhook
    bot.remove_webhook()
    bot.set_webhook(url="https://tradingbot-production-1412.up.railway.app/paypal-webhook")  # Usa tu URL generada en Railway

    print("🤖 Bot de Telegram iniciado en webhook.")
