from flask import Flask, request, jsonify, render_template, make_response
import psycopg2
import os
from functools import wraps

# Configura la base de datos
DB_URL = os.getenv("DB_URL", "postgresql://postgres:dhFTmlmpvcveKIINwsRIGaszgwDWfERR@postgres-q-ls.railway.internal:5432/railway")

# Crear aplicación Flask
app = Flask(__name__)

# Credenciales de autenticación para el dashboard
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "password123")

# ---------------------------------------
# 🔐 Función de autenticación básica
# ---------------------------------------
def check_auth(username, password):
    """Verifica si el nombre de usuario y la contraseña son correctos"""
    return username == DASHBOARD_USERNAME and password == DASHBOARD_PASSWORD

def authenticate():
    """Envia un mensaje 401 para solicitar autenticación"""
    response = make_response('Necesitas iniciar sesión para acceder al dashboard', 401)
    response.headers['WWW-Authenticate'] = 'Basic realm="Acceso al Dashboard"'
    return response

def requires_auth(f):
    """Decorador para proteger rutas con autenticación"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ---------------------------------------
# 🌐 Endpoint para recibir el webhook de PayPal
# ---------------------------------------
@app.route('/paypal-webhook', methods=['POST'])
def paypal_webhook():
    try:
        data = request.get_json(force=True)  # Asegurarse de obtener el JSON correctamente
        print("📥 Datos recibidos del webhook de PayPal:", data)

        if data.get('event_type') == 'PAYMENT.SALE.COMPLETED':
            user_id = data['resource']['payer']['payer_info']['payer_id']
            status = 'active'

            conn = psycopg2.connect(DB_URL)
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET subscription_status = %s
                    WHERE user_id = %s;
                """, (status, user_id))
                if cursor.rowcount == 0:
                    print(f"⚠️ No se encontró un usuario con user_id = {user_id}")
                conn.commit()
            conn.close()

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"❌ Error al procesar el webhook de PayPal: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------------------------------------
# 📊 Dashboard de monitoreo
# ---------------------------------------
@app.route('/dashboard', methods=['GET'])
@requires_auth
def dashboard():
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cursor:
            # Consultar estadísticas de suscriptores
            cursor.execute("""
                SELECT 
                    COUNT(*) AS active_subscriptions,
                    SUM(CASE WHEN subscription_status = 'active' THEN 1 ELSE 0 END) AS active_users,
                    COALESCE(SUM(payment_amount), 0) AS total_revenue
                FROM users;
            """)
            stats = cursor.fetchone()
            
            # Extraer los valores
            total_subscriptions = stats[0] or 0
            active_users = stats[1] or 0
            total_revenue = stats[2] or 0

            # Generar estadísticas adicionales (semanales, mensuales, anuales)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(payment_amount), 0) AS weekly_revenue
                FROM payments
                WHERE payment_date >= CURRENT_DATE - INTERVAL '7 days';
            """)
            weekly_revenue = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT 
                    COALESCE(SUM(payment_amount), 0) AS monthly_revenue
                FROM payments
                WHERE payment_date >= CURRENT_DATE - INTERVAL '1 month';
            """)
            monthly_revenue = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT 
                    COALESCE(SUM(payment_amount), 0) AS yearly_revenue
                FROM payments
                WHERE payment_date >= CURRENT_DATE - INTERVAL '1 year';
            """)
            yearly_revenue = cursor.fetchone()[0] or 0

            stats = {
                'active_subscriptions': total_subscriptions,
                'active_users': active_users,
                'total_revenue': total_revenue,
                'weekly_revenue': weekly_revenue,
                'monthly_revenue': monthly_revenue,
                'yearly_revenue': yearly_revenue
            }

        conn.close()
        
        return render_template('dashboard.html', stats=stats)

    except Exception as e:
        print(f"❌ Error al cargar el dashboard: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------
# 🚀 Iniciar la aplicación Flask
# ---------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))  # Cambia este puerto si el 5050 está en uso
    app.run(debug=False, host='0.0.0.0', port=port)
