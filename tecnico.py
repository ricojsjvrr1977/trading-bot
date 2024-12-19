import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt  # Importación necesaria para gráficos
from datetime import datetime, timedelta, timezone
import time
import requests
from xgboost import XGBClassifier, XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error

# Configuration
TIMEFRAME = '1h'
RSI_PERIOD = 14
STOCH_PERIOD = 14
ATR_PERIOD = 14
import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7545414519:AAE4pvyKjGrvexry-v6AGvv3TUgm0csi6J8')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1002321451206')

PREDICTION_DAYS = 7  # Default timeframe for price prediction

# Función para generar gráficos avanzados
def generate_advanced_charts(data, ticker):
    try:
        print("Generando gráficos avanzados...")
        plt.figure(figsize=(12, 8))

        # Gráfico del precio con RSI
        plt.subplot(3, 1, 1)
        plt.plot(data.index, data[f'Close_{ticker}'], label='Precio de Cierre', color='blue')
        plt.title(f"Precio de Cierre y RSI para {ticker}")
        plt.xlabel("Fecha")
        plt.ylabel("Precio de Cierre")
        plt.legend()

        plt.twinx()  # Eje secundario para RSI
        plt.plot(data.index, data['RSI'], label='RSI', color='orange', linestyle='--')
        plt.ylabel("RSI")
        plt.axhline(y=70, color='red', linestyle='--', label='Sobrecomprado (70)')
        plt.axhline(y=30, color='green', linestyle='--', label='Sobrevendido (30)')
        plt.legend(loc='upper left')

        # Gráfico de MACD y Signal Line
        plt.subplot(3, 1, 2)
        plt.plot(data.index, data['MACD'], label='MACD', color='purple')
        plt.plot(data.index, data['Signal_Line'], label='Signal Line', color='red', linestyle='--')
        plt.title(f"MACD y Signal Line para {ticker}")
        plt.xlabel("Fecha")
        plt.ylabel("MACD")
        plt.legend()

        # Gráfico de ATR
        plt.subplot(3, 1, 3)
        plt.plot(data.index, data['ATR'], label='ATR', color='green')
        plt.title(f"ATR (True Range Promedio) para {ticker}")
        plt.xlabel("Fecha")
        plt.ylabel("ATR")
        plt.legend()

        # Guardar y mostrar los gráficos
        plt.tight_layout()
        plt.savefig(f"{ticker}_advanced_charts.png")
        print(f"Gráficos guardados como {ticker}_advanced_charts.png")
        plt.show()
    except Exception as e:
        print(f"Error generando gráficos avanzados para {ticker}: {e}")

# Fetch historical data
def fetch_historical_data(ticker, interval):
    try:
        print(f"Fetching historical data for {ticker} with interval {interval}...")
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=60) if interval in ['1h', '30m', '15m'] else end_time - timedelta(days=10 * 365)
        try:
            data = yf.download(ticker, start=start_time, end=end_time, interval=interval)
            if data.empty:
                raise ValueError(f"No data available for {ticker} with interval {interval}.")
            print("Historical data fetched successfully.")
            return data
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
    except Exception as e:
        print(f"Error obteniendo datos históricos para {ticker}: {e}")

# Flatten Columns Function
def flatten_columns(data):
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = ['_'.join(filter(None, map(str, col))) for col in data.columns]
    data.columns = data.columns.str.strip().str.replace(' ', '_').str.replace('[^A-Za-z0-9_]', '', regex=True)
    return data

# Technical Indicators
def calculate_rsi(data, period, ticker):
    delta = data[f'Close_{ticker}'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_stochastic(data, period, ticker):
    high_period = data[f'High_{ticker}'].rolling(window=period).max()
    low_period = data[f'Low_{ticker}'].rolling(window=period).min()
    stoch = (data[f'Close_{ticker}'] - low_period) / (high_period - low_period) * 100
    return stoch

def calculate_atr(data, period, ticker):
    high_low = data[f'High_{ticker}'] - data[f'Low_{ticker}']
    high_close = np.abs(data[f'High_{ticker}'] - data[f'Close_{ticker}'].shift())
    low_close = np.abs(data[f'Low_{ticker}'] - data[f'Close_{ticker}'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr

# Feature Engineering
def generate_features(data, ticker):
    try:
        print("Generating features...")
        data = flatten_columns(data)
        data['RSI'] = calculate_rsi(data, RSI_PERIOD, ticker)
        data['Stochastic'] = calculate_stochastic(data, STOCH_PERIOD, ticker)
        data['ATR'] = calculate_atr(data, ATR_PERIOD, ticker)
        data['SMA'] = data[f'Close_{ticker}'].rolling(window=20).mean()
        data['EMA'] = data[f'Close_{ticker}'].ewm(span=20, adjust=False).mean()
        data['MACD'] = data[f'Close_{ticker}'].ewm(span=12, adjust=False).mean() - data[f'Close_{ticker}'].ewm(span=26, adjust=False).mean()
        data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['Volume_Change'] = data[f'Volume_{ticker}'].pct_change()
        data['Lag_Close'] = data[f'Close_{ticker}'].shift(1)
        data.dropna(inplace=True)
        print("Features generated.")
        return data
    except Exception as e:
        print(f"Error generando características para {ticker}: {e}")

# ML Training
def train_model(data, ticker):
    try:
        print("Training models...")
        data['Label'] = np.where(data[f'Close_{ticker}'].shift(-1) > data[f'Close_{ticker}'], 1, 0)
        features = ['RSI', 'Stochastic', 'ATR', 'SMA', 'EMA', 'MACD', 'Signal_Line', 'Volume_Change', 'Lag_Close']
        X = data[features]
        y = data['Label']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        classifier = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.05, random_state=42)
        classifier.fit(X_train, y_train)
        y_pred = classifier.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Classification model accuracy: {accuracy:.2f}")

        # Train regression model for price prediction
        data['Future_Close'] = data[f'Close_{ticker}'].shift(-PREDICTION_DAYS)
        regression_data = data.dropna(subset=['Future_Close'])
        X_reg = regression_data[features]
        y_reg = regression_data['Future_Close']
        X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(X_reg, y_reg, test_size=0.2, random_state=42)
        regressor = XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.05, random_state=42)
        regressor.fit(X_train_reg, y_train_reg)
        y_pred_reg = regressor.predict(X_test_reg)
        mae = mean_absolute_error(y_test_reg, y_pred_reg)
        print(f"Regression model trained. Mean Absolute Error: {mae:.2f}")
        return classifier, regressor, accuracy
    except Exception as e:
        print(f"Error entrenando modelo para {ticker}: {e}")

# Backtesting
def backtest_strategy(data, model, ticker):
    try:
        features = ['RSI', 'Stochastic', 'ATR', 'SMA', 'EMA', 'MACD', 'Signal_Line', 'Volume_Change', 'Lag_Close']
        data = flatten_columns(data)
        data['Prediction'] = model.predict(data[features])
        shifted_close = data[f'Close_{ticker}'].shift(-1)
        success_conditions = (data['Prediction'] == 1) & (shifted_close > data[f'Close_{ticker}'])
        success_count = success_conditions.sum()
        total_signals = data['Prediction'].sum()
        success_count = int(success_count)
        total_signals = int(total_signals)
        backtesting_success = (success_count / total_signals * 100) if total_signals > 0 else 0.0
        return backtesting_success
    except Exception as e:
        print(f"Error en backtesting para {ticker}: {e}")

# Generate Trading Signal
def generate_trading_signal(model, data, regressor, ticker):
    try:
        features = ['RSI', 'Stochastic', 'ATR', 'SMA', 'EMA', 'MACD', 'Signal_Line', 'Volume_Change', 'Lag_Close']
        latest_data = data.iloc[-1:]
        prediction = model.predict(latest_data[features])[0]
        future_price = regressor.predict(latest_data[features])[0]
        if prediction == 1 and latest_data['RSI'].iloc[0] < 30:
            action = "Comprar 🐂"
        elif prediction == 0 and latest_data['RSI'].iloc[0] > 70:
            action = "Vender 🐻"
        else:
            action = "Mantener 📊"
        return action, future_price
    except Exception as e:
        print(f"Error generando señal de trading para {ticker}: {e}")

# Telegram Report
def generate_telegram_report(stock_name, ticker, current_price, action, indicators, future_price, accuracy, backtesting_success):
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
    potential_profit = (future_price - current_price) if "Comprar" in action else None

    atr_interpretation = (
        "Alta volatilidad 📈" if indicators['ATR'] > 1.5 else 
        "Moderada volatilidad 📊" if 0.75 <= indicators['ATR'] <= 1.5 else 
        "Baja volatilidad 📉"
    )
    sma_interpretation = (
        f"El precio está por encima de la SMA 🟢 (Tendencia Alcista 🐂)"
        if current_price > indicators['SMA'] else
        f"El precio está por debajo de la SMA 🔴 (Tendencia Bajista 🐻)"
    )
    ema_interpretation = (
        f"El precio está por encima de la EMA ✅ (Momentum Positivo 🟢)"
        if current_price > indicators['EMA'] else
        f"El precio está por debajo de la EMA ⚠️ (Momentum Negativo 🔴)"
    )
    rsi_interpretation = (
        "⚠️ Sobrecomprado" if indicators['RSI'] > 70 else
        "🟢 Sobrevendido" if indicators['RSI'] < 30 else
        "🟡 Neutral"
    )
    stoch_interpretation = (
        "⚠️ Sobrecomprado" if indicators['Stochastic'] > 80 else
        "🟢 Sobrevendido" if indicators['Stochastic'] < 20 else
        "🟡 Neutral"
    )

    kpi_details = f"""
    📊 *Indicadores*:
    - 🎯 RSI: {indicators['RSI']:.2f} ({rsi_interpretation})
    - 📈 Estocástico: {indicators['Stochastic']:.2f} ({stoch_interpretation})
    - 📊 ATR: {indicators['ATR']:.2f} ({atr_interpretation})
    - 📉 SMA: {indicators['SMA']:.2f} ({sma_interpretation})
    - 📊 EMA: {indicators['EMA']:.2f} ({ema_interpretation})
    """

    signal_analysis = f"✅ Señal ML: {action}. Precio proyectado: {future_price:.2f} USD." if future_price else f"🔴 Señal ML: {action}."
    profit_info = f"🤑 Ganancia Potencial: {potential_profit:.2f} USD." if potential_profit is not None else ""

    message = f"""
    🏦 *{stock_name}* ({ticker})
    💰 Precio Actual: {current_price:.2f} USD
    📅 {now}
    📢 Señal: *{action}*
    📉 Precio Proyectado (Próximos 7 días): {future_price:.2f} USD
    {profit_info}

    {kpi_details}

    🧠 *Análisis del Machine Learning*:
    {signal_analysis}

    🔍 *Porcentaje de Éxito en Backtesting*: {backtesting_success:.2f}%
    📌 *Precisión del Modelo*: {accuracy:.2f}%
    """
    send_telegram_message(message)

def send_telegram_message(message, image_path=None):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
        response = requests.post(url, data=payload)

        if image_path:
            url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto'
            with open(image_path, 'rb') as photo:
                files = {'photo': photo}
                payload = {'chat_id': TELEGRAM_CHAT_ID}
                response = requests.post(url, data=payload, files=files)

            if response.status_code != 200:
                print(f"Error enviando imagen a Telegram: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Error enviando mensaje de Telegram: {e}")

# Nueva función para el maestro
def execute_technical_analysis(user, tickers):
    """
    Ejecuta el análisis técnico para un usuario específico y una lista de tickers.
    """
    for ticker in set(tickers):  # Eliminar duplicados
        print(f"Procesando análisis técnico para {ticker} para el usuario {user}...")
        data = fetch_historical_data(ticker, TIMEFRAME)
        if data is None or data.empty:
            print(f"No se pudo obtener datos o los datos están vacíos para {ticker}.")
            continue
        data = generate_features(data, ticker)
        model, regressor, accuracy = train_model(data, ticker)
        backtesting_success = backtest_strategy(data, model, ticker)

        # Generar gráficos avanzados
        chart_path = f"{ticker}_advanced_charts.png"
        generate_advanced_charts(data, ticker)

        # Generar reporte y enviarlo
        current_price = data[f'Close_{ticker}'].iloc[-1]
        action, future_price = generate_trading_signal(model, data, regressor, ticker)
        indicators = {
            "RSI": data['RSI'].iloc[-1],
            "Stochastic": data['Stochastic'].iloc[-1],
            "ATR": data['ATR'].iloc[-1],
            "SMA": data['SMA'].iloc[-1],
            "EMA": data['EMA'].iloc[-1],
        }
        report_message = generate_telegram_report(
            stock_name=ticker,
            ticker=ticker,
            current_price=current_price,
            action=action,
            indicators=indicators,
            future_price=future_price,
            accuracy=accuracy,
            backtesting_success=backtesting_success,
        )
        send_telegram_message(report_message, image_path=chart_path)

# Main Execution
def main():
    ticker = input("Ingrese el símbolo del ticker: ").upper()
    stock_name = input("Ingrese el nombre de la compañía: ")
    data = fetch_historical_data(ticker, TIMEFRAME)
    if data is None:
        return
    data = generate_features(data, ticker)
    model, regressor, accuracy = train_model(data, ticker)
    backtesting_success = backtest_strategy(data, model, ticker)

    # Generar gráficos avanzados
    chart_path = f"{ticker}_advanced_charts.png"
    generate_advanced_charts(data, ticker)

    # Generar reporte inicial y enviar con gráficos
    report_message = "Reporte inicial generado automáticamente con análisis avanzado."
    send_telegram_message(report_message, image_path=chart_path)

    while True:
        latest_data = fetch_historical_data(ticker, TIMEFRAME) or data
        if latest_data is None:
            time.sleep(3600)
            continue
        latest_data = generate_features(latest_data, ticker)
        action, future_price = generate_trading_signal(model, latest_data, regressor, ticker)
        current_price = latest_data[f'Close_{ticker}'].iloc[-1].item()
        indicators = {
            "RSI": latest_data['RSI'].iloc[-1],
            "Stochastic": latest_data['Stochastic'].iloc[-1],  # Ensure Stochastic is included
            "ATR": latest_data['ATR'].iloc[-1],
            "SMA": latest_data['SMA'].iloc[-1],
            "EMA": latest_data['EMA'].iloc[-1],
        }
        report_message = generate_telegram_report(
            stock_name=stock_name,
            ticker=ticker,
            current_price=current_price,
            action=action,
            indicators=indicators,
            future_price=future_price,
            accuracy=accuracy,
            backtesting_success=backtesting_success,
        )
        
        # Generar gráficos nuevamente y enviar
        generate_advanced_charts(latest_data, ticker)
        send_telegram_message(report_message, image_path=chart_path)

        time.sleep(300)

if __name__ == "__main__":
    main()