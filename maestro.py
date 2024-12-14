import psycopg2
import paypalrestsdk
import requests
import schedule
import time
from datetime import datetime, timedelta

# Configuración de la base de datos
DB_CONFIG = {
    "host": "junction.proxy.rlwy.net",
    "database": "railway",
    "user": "postgres",
    "password": "EuXtszvtkOoQaBwbvuNpQQCjIIukLQAT",
    "port": "57247",
}

# Configuración de PayPal
PAYPAL_CLIENT_ID = 'AfXKDZFvIOS3RkD0bViTN8VibRsmKJEkaG4nMj_B_Pp0mTcSCgIFF3Oc3mrFMF6bT7ANsX71zozdp75y'
PAYPAL_SECRET = 'EFVLUnC3d8FY4Nyf2gfBprZfgj3E2kMskeRkbUy0dlSPeoayIQUqjyk-K_nWHHK3fymfnn8tGeJlUvcH'

paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_SECRET
})

# Configuración de Telegram
TELEGRAM_BOT_TOKEN = '7467249877:AAEHXU8hwa0V-4gyIpeVC1ge13-ynAbP0_A'
TELEGRAM_REPORT_BOT_TOKEN = '7545414519:AAE4pvyKjGrvexry-v6AGvv3TUgm0csi6J8'
TELEGRAM_REPORT_CHAT_ID = '-1002321451206'

# Conexión a la base de datos
def connect_db():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

# Obtener usuarios activos
def get_active_users():
    conn = connect_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, username, email, telegram_id, subscription_plan, tickers, analysis_type, subscription_active 
            FROM users WHERE subscription_active = TRUE;
        """)
        users = cur.fetchall()
    conn.close()
    return users

# Proceso de prueba gratuita
def start_trial(user_id):
    conn = connect_db()
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE users 
            SET subscription_active = TRUE, 
                start_date = NOW(), 
                end_date = NOW() + interval '2 days' 
            WHERE id = %s;
        """, (user_id,))
        conn.commit()

# Enviar notificaciones de vencimiento
def notify_expiration():
    conn = connect_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, telegram_id FROM users 
            WHERE end_date <= NOW() + interval '1 day' 
            AND subscription_active = TRUE;
        """)
        users = cur.fetchall()
    for user in users:
        telegram_id = user[1]
        if telegram_id:
            message = "⚠️ Tu prueba gratuita está a punto de expirar. Haz tu pago para seguir recibiendo señales."
            send_telegram_message(telegram_id, message)

# Enviar mensaje de Telegram
def send_telegram_message(chat_id, message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
    requests.post(url, data=payload)

# Generar pago PayPal
def generate_paypal_payment_link(user_id, plan):
    price = 1.0 if plan == "basic" else 1.5
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": "http://localhost:5000/payment/success",
            "cancel_url": "http://localhost:5000/payment/cancel"
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

# Verificar pago
def verify_payment(payment_id):
    payment = paypalrestsdk.Payment.find(payment_id)
    return payment.state == "approved"

# Reporte semanal
def send_weekly_report():
    message = "📈 *Reporte semanal*\n- Suscriptores: 50\n- Ganancias: $500\n- Planes: Básico: 30, Avanzado: 20"
    url = f'https://api.telegram.org/bot{TELEGRAM_REPORT_BOT_TOKEN}/sendMessage'
    payload = {'chat_id': TELEGRAM_REPORT_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    requests.post(url, data=payload)

# Programar tareas
schedule.every().monday.at("09:30").do(send_weekly_report)
schedule.every().day.at("08:30").do(notify_expiration)

# Bucle principal
def main():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
