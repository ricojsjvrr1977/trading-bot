from flask import Flask, request, jsonify, render_template, make_response
import psycopg2
import os
from functools import wraps

# ---------------------------------------
# 🔐 Configuración de la base de datos
# ---------------------------------------
DB_URL = os.getenv("DB_URL")

# ---------------------------------------
# 🔐 Credenciales de autenticación
# ---------------------------------------
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD")

if not DASHBOARD_USERNAME or not DASHBOARD_PASSWORD:
    raise ValueError("❌ ERROR: DASHBOARD_USERNAME y DASHBOARD_PASSWORD deben estar configurados en las variables de entorno.")

# Crear aplicación Flask
app = Flask(__name__)

# ---------------------------------------
# 🌐 Webhook de PayPal
# ---------------------------------------
@app.route('/paypal-webhook', methods=['POST'])
def paypal_webhook():
    try:
        data = request.get_json(force=True)
        if data.get('event_type') != 'PAYMENT.SALE.COMPLETED':
            return jsonify({"status": "error", "message": "Evento no válido"}), 400

        user_id = data.get('resource', {}).get('payer', {}).get('payer_info', {}).get('payer_id')
        if not user_id:
            return jsonify({"status": "error", "message": "user_id no encontrado"}), 400

        conn = None
        try:
            conn = psycopg2.connect(DB_URL)
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET subscription_active = %s
                    WHERE user_id = %s;
                """, (True, user_id))
                conn.commit()
        finally:
            if conn:
                conn.close()

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"❌ Error al procesar el webhook de PayPal: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------------------------------------
# 📊 Dashboard de Monitoreo
# ---------------------------------------
@app.route('/dashboard', methods=['GET'])
@requires_auth
def dashboard():
    try:
        conn = None
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_active = TRUE;")
            active_users = cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM payments;")
            total_revenue = cursor.fetchone()[0]

        return render_template('dashboard.html', stats={
            'active_users': active_users,
            'total_revenue': total_revenue
        })

    except Exception as e:
        print(f"❌ Error al cargar el dashboard: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if conn:
            conn.close()

# ---------------------------------------
# 🚀 Iniciar la aplicación Flask
# ---------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5050))
    app.run(debug=False, host='0.0.0.0', port=port)
