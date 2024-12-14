import yfinance as yf
import matplotlib.pyplot as plt
import requests
from datetime import datetime
import numpy as np

# Variables para el token y chat_id de Telegram
TELEGRAM_TOKEN = '7545414519:AAE4pvyKjGrvexry-v6AGvv3TUgm0csi6J8'
CHAT_ID = '-1002321451206'

# Función para enviar mensajes y gráficos a Telegram
def send_telegram_message(message, image_path=None):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    response = requests.post(url, data=payload)

    if image_path:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto'
        with open(image_path, 'rb') as photo:
            files = {'photo': photo}
            response = requests.post(url, data={'chat_id': CHAT_ID}, files=files)
            if response.status_code == 200:
                print(f"Imagen enviada: {image_path}")
            else:
                print(f"Error enviando la imagen: {response.status_code} - {response.text}")

# Función para obtener datos fundamentales
def get_stock_fundamentals(stock_symbol):
    stock = yf.Ticker(stock_symbol)
    info = stock.info
    price = info.get('regularMarketPrice') or info.get('previousClose')
    kpis = {
        'Price': round(price, 2) if price else None,
        'PE': round(info.get('trailingPE'), 2) if info.get('trailingPE') else None,
        'PS': round(info.get('priceToSalesTrailing12Months'), 2) if info.get('priceToSalesTrailing12Months') else None,
        'PB': round(info.get('priceToBook'), 2) if info.get('priceToBook') else None,
        'Dividend_Yield': round(info.get('dividendYield') * 100, 2) if info.get('dividendYield') else None,
        'EPS': round(info.get('regularMarketEPS'), 2) if info.get('regularMarketEPS') else None,
        'ROE': round(info.get('returnOnEquity') * 100, 2) if info.get('returnOnEquity') else None,
    }
    return kpis

# Función para calcular valores de referencia dinámicos
def calculate_dynamic_reference(stock_symbol):
    stock = yf.Ticker(stock_symbol)
    hist = stock.history(period="2y")

    pe_mean = hist['Close'].pct_change().mean() * 100
    volatility = hist['Close'].pct_change().std() * 100

    reference = {
        'PE': round(max(10, min(25, 20 - (pe_mean / volatility))), 2),
        'PS': round(2 + (volatility / 50), 2),
        'PB': round(1.5 + (pe_mean / 100), 2),
        'ROE': round(10 + (pe_mean / 2), 2)
    }
    return reference

# Función para interpretar los KPI
def interpret_kpis(kpis, reference):
    interpretation = "\n"
    if kpis['PE']:
        interpretation += f"💵 **PE (Price to Earnings)**: {kpis['PE']} (Referencia: {reference['PE']}): Un PE más bajo puede indicar infravaloración. {kpis['PE']} está en rango aceptable.\n"
    if kpis['PS']:
        interpretation += f"📊 **PS (Price to Sales)**: {kpis['PS']} (Referencia: {reference['PS']}): Un PS bajo puede sugerir que la acción está barata en relación a sus ventas.\n"
    if kpis['PB']:
        interpretation += f"📚 **PB (Price to Book)**: {kpis['PB']} (Referencia: {reference['PB']}): Un PB bajo sugiere que la acción está infravalorada en relación a su valor contable.\n"
    if kpis['Dividend_Yield']:
        interpretation += f"💸 **Dividend Yield**: {kpis['Dividend_Yield']}%: Un rendimiento de dividendo de {kpis['Dividend_Yield']}% es atractivo para ingresos pasivos.\n"
    if kpis['ROE']:
        interpretation += f"📈 **ROE (Return on Equity)**: {kpis['ROE']}% (Referencia: {reference['ROE']}): Un ROE de {kpis['ROE']}% indica buen rendimiento sobre el capital.\n"
    return interpretation

# Generar señales y conclusiones
def generate_fundamental_signal(kpis, reference):
    favorable_conditions = 0
    if kpis['PE'] < reference['PE']:
        favorable_conditions += 1
    if kpis['PS'] < reference['PS']:
        favorable_conditions += 1
    if kpis['PB'] < reference['PB']:
        favorable_conditions += 1
    if kpis['ROE'] > reference['ROE']:
        favorable_conditions += 1

    if favorable_conditions >= 3:
        action = "Comprar 🛒"
        conclusion = "La mayoría de los indicadores fundamentales sugieren una oportunidad de compra."
    else:
        action = "Vender/Mantener 📉"
        conclusion = "Los indicadores fundamentales no son lo suficientemente favorables para comprar."

    return action, conclusion

# Generar gráficos avanzados
def generate_advanced_charts(data, kpis, reference, ticker, action):
    plt.figure(figsize=(14, 10))

    # Gráfico de precio con puntos de compra/venta
    plt.subplot(3, 1, 1)
    plt.plot(data['Close'], label='Precio de Cierre', color='blue')
    plt.axhline(y=kpis['Price'] * 0.85, color='green', linestyle='--', label='Infravalorado')
    plt.axhline(y=kpis['Price'] * 1.15, color='red', linestyle='--', label='Sobrevalorado')
    plt.scatter(
        data.index[data['Close'] < kpis['Price'] * 0.85],
        data['Close'][data['Close'] < kpis['Price'] * 0.85],
        color='green', label='Punto de Compra', s=50, zorder=5
    )
    plt.scatter(
        data.index[data['Close'] > kpis['Price'] * 1.15],
        data['Close'][data['Close'] > kpis['Price'] * 1.15],
        color='red', label='Punto de Venta', s=50, zorder=5
    )
    plt.title(f"Precio y Bandas para {ticker}")
    plt.legend()

    # Gráfico de volatilidad
    volatility = data['Close'].pct_change().rolling(window=30).std() * 100
    plt.subplot(3, 1, 2)
    plt.plot(volatility, label='Volatilidad (%)', color='purple')
    plt.title(f"Volatilidad (30 días) para {ticker}")
    plt.legend()

    # Gráfico de volumen
    plt.subplot(3, 1, 3)
    plt.bar(data.index, data['Volume'], label='Volumen', color='orange', alpha=0.7)
    plt.title(f"Volumen para {ticker}")
    plt.legend()

    plt.tight_layout()
    plt.savefig(f"{ticker}_advanced_charts.png")
    plt.show()

# Nueva función para integrar con el maestro
def execute_fundamental_analysis(ticker, stock_name):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y")

    kpis = get_stock_fundamentals(ticker)
    reference = calculate_dynamic_reference(ticker)

    action, conclusion = generate_fundamental_signal(kpis, reference)
    interpretation = interpret_kpis(kpis, reference)

    report = f"""
📊 **Reporte de la Acción**: {stock_name} ({ticker})
🕒 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔸 **Precio Actual**: ${kpis['Price']}
{interpretation}
---
✅ **Recomendación**: {action}
📌 **Conclusión**: {conclusion}
"""
    print(report)

    # Generar gráficos avanzados
    generate_advanced_charts(hist, kpis, reference, ticker, action)

    # Enviar el reporte por Telegram
    send_telegram_message(report, f"{ticker}_advanced_charts.png")

# Ejecutar reporte
def generate_report():
    ticker = input("Ingrese el símbolo del ticker: ").upper()
    stock_name = input("Ingrese el nombre de la compañía: ")

    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y")

    kpis = get_stock_fundamentals(ticker)
    reference = calculate_dynamic_reference(ticker)

    action, conclusion = generate_fundamental_signal(kpis, reference)
    interpretation = interpret_kpis(kpis, reference)

    report = f"""
📊 **Reporte de la Acción**: {stock_name} ({ticker})
🕒 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔸 **Precio Actual**: ${kpis['Price']}
{interpretation}
---
✅ **Recomendación**: {action}
📌 **Conclusión**: {conclusion}
"""
    print(report)

    generate_advanced_charts(hist, kpis, reference, ticker, action)
    send_telegram_message(report, f"{ticker}_advanced_charts.png")

# Ejecutar reporte
generate_report()