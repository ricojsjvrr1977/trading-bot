import psycopg2
import paypalrestsdk
import requests
import os
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

# ---------------------------------------
# 🔐 Configuración de la base de datos
# ---------------------------------------
DB_URL = os.getenv("DB_URL")

# ---------------------------------------
# 🔐 Configuración de PayPal
# ---------------------------------------
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")

paypalrestsdk.configure({
    "mode": "sandbox",  # Cambiar a "live" para producción
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_SECRET
})

# ---------------------------------------
# 🔐 Configuración de Telegram
# ---------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_REPORT_BOT_TOKEN = os.getenv("TELEGRAM_REPORT_BOT_TOKEN")
TELEGRAM_REPORT_CHAT_ID = os.getenv("TELEGRAM_REPORT_CHAT_ID")

# ---------------------------------------
# 📡 Conexión a la base de datos
# ---------------------------------------
def connect_db():
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        return None

# ---------------------------------------
# 📦 Control de Tickers
# ---------------------------------------
def update_tickers(user_id, new_tickers):
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users 
                    SET tickers = %s 
                    WHERE id = %s AND subscription_active = TRUE;
                """, (new_tickers, user_id))
                conn.commit()
    except Exception as e:
        print(f"❌ Error al actualizar los tickers: {e}")

# ---------------------------------------
# 📅 Enviar notificaciones de vencimiento
# ---------------------------------------
def notify_expiration():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, telegram_id, end_date FROM users 
                    WHERE end_date <= NOW() + interval '1 day' 
                    AND subscription_active = TRUE;
                """)
                users = cur.fetchall()
        
        for user in users:
            telegram_id = user[1]
            if telegram_id:
                message = "⚠️ Tu prueba gratuita está a punto de expirar. Haz tu pago para seguir recibiendo señales."
                send_telegram_message(telegram_id, message)
    except Exception as e:
        print(f"❌ Error al notificar expiraciones: {e}")

# ---------------------------------------
# 📩 Enviar mensaje de Telegram
# ---------------------------------------
def send_telegram_message(chat_id, message):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Error al enviar mensaje de Telegram: {e}")

# ---------------------------------------
# 💰 Generar link de pago PayPal
# ---------------------------------------
def generate_paypal_payment_link(user_id, plan):
    try:
        price = 1.0 if plan == "basic" else 2
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": "https://your-domain.com/payment/success",
                "cancel_url": "https://your-domain.com/payment/cancel"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"Suscripción {plan.capitalize()}",
                        "sku": f"{plan}_plan",
                        "price": f"{price}",
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {"total": f"{price}", "currency": "USD"},
                "description": f"Suscripción al plan {plan.capitalize()} para usuario {user_id}"
            }]
        })
        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    return link.href
        else:
            return None
    except Exception as e:
        print(f"❌ Error al generar link de pago de PayPal: {e}")
        return None

# ---------------------------------------
# 📈 Enviar reporte semanal
# ---------------------------------------
def send_weekly_report():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as total_users, 
                           SUM(CASE WHEN subscription_active = TRUE THEN 1 ELSE 0 END) AS active_users, 
                           COALESCE(SUM(amount), 0) AS total_revenue 
                    FROM users;
                """)
                stats = cur.fetchone()
        
        message = f"""
        📈 *Reporte semanal* 
        - Total de suscriptores: {stats[0]}
        - Usuarios activos: {stats[1]}
        - Ganancias totales: ${stats[2]:.2f}
        """
        
        url = f'https://api.telegram.org/bot{TELEGRAM_REPORT_BOT_TOKEN}/sendMessage'
        payload = {'chat_id': TELEGRAM_REPORT_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Error al enviar reporte semanal: {e}")

# ---------------------------------------
# ⏰ Programar tareas con APScheduler
# ---------------------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(send_weekly_report, 'cron', day_of_week='mon', hour=9, minute=30)
scheduler.add_job(notify_expiration, 'cron', hour=8, minute=30)
scheduler.start()

# ---------------------------------------
# 🚀 Iniciar aplicación principal
# ---------------------------------------
if __name__ == "__main__":
    print("🚀 Maestro en ejecución...")
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("❌ Maestro detenido.")
        scheduler.shutdown()
