from flask import Flask, request, jsonify
import psycopg2
import os

# Configura la base de datos
DB_URL = os.getenv("DB_URL", "postgresql://postgres:dhFTmlmpvcveKIINwsRIGaszgwDWfERR@postgres-q-ls.railway.internal:5432/railway")

# Crear aplicación Flask
app = Flask(__name__)

# Endpoint para recibir el webhook de PayPal
@app.route('/paypal-webhook', methods=['POST'])
def paypal_webhook():
    try:
        data = request.get_json(force=True)  # Asegurarse de obtener el JSON correctamente
        print("📥 Datos recibidos del webhook de PayPal:", data)

        if data['event_type'] == 'PAYMENT.SALE.COMPLETED':
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
