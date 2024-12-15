from celery import Celery
import os

# Obtener la URL de Redis desde las variables de entorno
redis_url = os.getenv('REDIS_URL', 'redis://default:lYwhAvPrrocBWhHmVWPvEmsVsEizKvRu@redis.railway.internal:6379')
# Configuración de Celery
celery = Celery('tasks', broker=redis_url)

celery.conf.update(
    result_backend=redis_url,
    accept_content=['json'],
    task_serializer='json',
)

# Verificar la conexión con Redis
if celery.backend.client.ping():
    print("✅ Conexión exitosa a Redis")
else:
    print("❌ Error al conectar con Redis")

# Una tarea de ejemplo
@celery.task
def add(x, y):
    return x + y
