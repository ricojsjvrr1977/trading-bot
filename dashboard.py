from flask import Flask, render_template
import psycopg2
import os
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta

# Configuración de la base de datos
DB_URL = os.getenv("DB_URL", "postgresql://postgres:dhFTmlmpvcveKIINwsRIGaszgwDWfERR@autorack.proxy.rlwy.net:39614/railway")

# Configurar aplicación Flask
app = Flask(__name__)

# Conexión a la base de datos
def connect_db():
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

# Obtener estadísticas
def get_statistics():
    conn = connect_db()
    if not conn:
        return None

    with conn.cursor() as cur:
        # Total de suscripciones activas
        cur.execute("SELECT COUNT(*) FROM users WHERE subscription_active = TRUE;")
        active_subscriptions = cur.fetchone()[0]

        # Ganancias acumuladas (suponiendo que tenemos una tabla de pagos con el campo amount)
        cur.execute("SELECT SUM(amount) FROM payments WHERE payment_status = 'completed';")
        total_revenue = cur.fetchone()[0] or 0.0

        # Ganancias semanales, mensuales y anuales
        cur.execute("SELECT SUM(amount) FROM payments WHERE payment_status = 'completed' AND date >= current_date - interval '7 days';")
        weekly_revenue = cur.fetchone()[0] or 0.0

        cur.execute("SELECT SUM(amount) FROM payments WHERE payment_status = 'completed' AND date >= current_date - interval '1 month';")
        monthly_revenue = cur.fetchone()[0] or 0.0

        cur.execute("SELECT SUM(amount) FROM payments WHERE payment_status = 'completed' AND date >= current_date - interval '1 year';")
        yearly_revenue = cur.fetchone()[0] or 0.0

        # Obtener suscriptores por semana, mes, y año
        cur.execute("SELECT COUNT(*) FROM users WHERE subscription_active = TRUE AND created_at >= current_date - interval '7 days';")
        weekly_subscriptions = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM users WHERE subscription_active = TRUE AND created_at >= current_date - interval '1 month';")
        monthly_subscriptions = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM users WHERE subscription_active = TRUE AND created_at >= current_date - interval '1 year';")
        yearly_subscriptions = cur.fetchone()[0] or 0

    conn.close()

    return {
        "active_subscriptions": active_subscriptions,
        "total_revenue": total_revenue,
        "weekly_revenue": weekly_revenue,
        "monthly_revenue": monthly_revenue,
        "yearly_revenue": yearly_revenue,
        "weekly_subscriptions": weekly_subscriptions,
        "monthly_subscriptions": monthly_subscriptions,
        "yearly_subscriptions": yearly_subscriptions,
    }

# Generar gráfico de tendencias de ganancias
def generate_revenue_chart():
    data = get_statistics()

    if not data:
        return None

    # Generar gráfico
    fig, ax = plt.subplots()
    ax.plot(
        ["Semana", "Mes", "Año"],
        [data["weekly_revenue"], data["monthly_revenue"], data["yearly_revenue"]],
        marker="o"
    )

    ax.set_title('Tendencia de Ganancias')
    ax.set_ylabel('Ganancias en USD')
    ax.set_xlabel('Período')

    # Guardar la imagen en un objeto en memoria
    img = io.BytesIO()
    fig.savefig(img, format="png")
    img.seek(0)
    img_base64 = base64.b64encode(img.getvalue()).decode("utf8")
    return img_base64

# Ruta principal del dashboard
@app.route('/')
def index():
    stats = get_statistics()
    revenue_chart = generate_revenue_chart()
    return render_template('dashboard.html', stats=stats, revenue_chart=revenue_chart)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
