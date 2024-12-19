from flask import Flask, render_template, make_response, request
import psycopg2
import os
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta
from functools import wraps

# ---------------------------------------
# 🔐 Configuración de la base de datos
# ---------------------------------------
DB_URL = os.getenv("DB_URL")

# ---------------------------------------
# 🔐 Credenciales de autenticación
# ---------------------------------------
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "password123")

# ---------------------------------------
# 🌐 Configurar aplicación Flask
# ---------------------------------------
app = Flask(__name__)

# ---------------------------------------
# 🔐 Funciones de autenticación
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
# 📈 Obtener estadísticas
# ---------------------------------------
def get_statistics():
    try:
        conn = connect_db()
        if not conn:
            return None

        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE subscription_active = TRUE) AS active_subscriptions,
                    COALESCE(SUM(amount), 0) AS total_revenue,
                    COALESCE(SUM(amount) FILTER (WHERE payment_status = 'completed' AND payment_date >= current_date - interval '7 days'), 0) AS weekly_revenue,
                    COALESCE(SUM(amount) FILTER (WHERE payment_status = 'completed' AND payment_date >= current_date - interval '1 month'), 0) AS monthly_revenue,
                    COALESCE(SUM(amount) FILTER (WHERE payment_status = 'completed' AND payment_date >= current_date - interval '1 year'), 0) AS yearly_revenue,
                    COUNT(*) FILTER (WHERE created_at >= current_date - interval '7 days' AND subscription_active = TRUE) AS weekly_subscriptions,
                    COUNT(*) FILTER (WHERE created_at >= current_date - interval '1 month' AND subscription_active = TRUE) AS monthly_subscriptions,
                    COUNT(*) FILTER (WHERE created_at >= current_date - interval '1 year' AND subscription_active = TRUE) AS yearly_subscriptions
                FROM users 
                LEFT JOIN payments ON payments.user_id = users.user_id;
            """)
            stats = cur.fetchone()

        conn.close()

        return {
            "active_subscriptions": stats[0] or 0,
            "total_revenue": stats[1] or 0.0,
            "weekly_revenue": stats[2] or 0.0,
            "monthly_revenue": stats[3] or 0.0,
            "yearly_revenue": stats[4] or 0.0,
            "weekly_subscriptions": stats[5] or 0,
            "monthly_subscriptions": stats[6] or 0,
            "yearly_subscriptions": stats[7] or 0,
        }
    except Exception as e:
        print(f"❌ Error al obtener estadísticas: {e}")
        return None

# ---------------------------------------
# 📊 Generar gráfico de tendencias de ganancias
# ---------------------------------------
def generate_revenue_chart():
    try:
        data = get_statistics()
        if not data:
            return None

        fig, ax = plt.subplots()
        ax.plot(
            ["Semana", "Mes", "Año"],
            [data["weekly_revenue"], data["monthly_revenue"], data["yearly_revenue"]],
            marker="o"
        )
        ax.set_title('Tendencia de Ganancias')
        ax.set_ylabel('Ganancias en USD')
        ax.set_xlabel('Período')

        img = io.BytesIO()
        fig.savefig(img, format="png")
        img.seek(0)
        img_base64 = base64.b64encode(img.getvalue()).decode("utf8")
        plt.close(fig)  # 🔥 Liberar la memoria
        return img_base64
    except Exception as e:
        print(f"❌ Error al generar gráfico de tendencias: {e}")
        return None

# ---------------------------------------
# 📊 Ruta principal del dashboard
# ---------------------------------------
@app.route('/')
@requires_auth
def index():
    try:
        stats = get_statistics()
        revenue_chart = generate_revenue_chart()
        return render_template('dashboard.html', stats=stats, revenue_chart=revenue_chart)
    except Exception as e:
        print(f"❌ Error al cargar la página del dashboard: {e}")
        return 'Error interno del servidor', 500

# ---------------------------------------
# 🚀 Iniciar aplicación
# ---------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5050))  # Cambiar este puerto si el 5050 está en uso
    app.run(debug=False, host='0.0.0.0', port=port)
