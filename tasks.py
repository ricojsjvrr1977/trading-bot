from celery import Celery
from time import sleep

# Crear instancia de Celery y configurar con la URL de Redis
app = Celery('tasks', broker='redis://default:dapYHNuAoJsGZbjiWJslsSMnzVZDsihU@redis.railway.internal:6379')

@app.task
def example_task():
    """Una tarea de ejemplo que simula un trabajo pesado."""
    print("Iniciando tarea...")
    sleep(10)  # Simulamos un retraso de 10 segundos
    print("Tarea completada.")

@app.task
def process_user_data(user_id):
    """Tarea que procesa los datos de los usuarios."""
    print(f"Procesando datos del usuario {user_id}...")
    sleep(5)  # Simulamos un retraso de 5 segundos
    print(f"Datos del usuario {user_id} procesados con éxito.")

@app.task
def generate_report(user_id, report_type):
    """Genera un reporte para un usuario determinado."""
    print(f"Generando reporte para el usuario {user_id} de tipo {report_type}...")
    sleep(15)  # Simulamos un retraso de 15 segundos
    print(f"Reporte para el usuario {user_id} de tipo {report_type} generado con éxito.")
