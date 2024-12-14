from flask import Flask, request, jsonify
import psycopg2  # Para manejar la base de datos
import os

# Configura tu base de datos
DB_URL = os.getenv("DB_URL", "tu_url_de_base_de_datos_aqui")

# Crear aplicación Flask
app = Flask(__name__)

# Endpoint para recibir el webhook de PayPal
@app.route('/paypal-webhook', methods=['POST'])
def paypal_webhook():
    try:
        # Recibe los datos del webhook de PayPal
        data = request.json

        # Aquí puedes hacer lo que necesites con los datos del pago
        print("Datos recibidos del webhook de PayPal:", data)

        # Ejemplo: verifica si el pago fue exitoso
        if data['event_type'] == 'PAYMENT.SALE.COMPLETED':
            # Aquí es donde actualizamos la base de datos, por ejemplo:
            # Actualizamos el estado del pago en la base de datos
            user_id = data['resource']['payer']['payer_info']['payer_id']
            status = 'active'
            
            # Conecta a la base de datos y actualiza el estado
            conn = psycopg2.connect(DB_URL)
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET subscription_status = %s
                    WHERE user_id = %s;
                """, (status, user_id))
                conn.commit()
            conn.close()

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("Error al procesar el webhook de PayPal:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
