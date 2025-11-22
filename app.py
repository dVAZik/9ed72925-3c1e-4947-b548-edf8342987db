from flask import Flask, request, jsonify, render_template
import json
import random
import time
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Для Render нужно использовать их порт
port = int(os.environ.get("PORT", 5000))

# Данные игроков (в памяти)
game_data = {"players": {}}

# Криптовалюты
CRYPTOS = {
    "bitcoin": {"name": "Bitcoin", "symbol": "BTC", "color": "#f7931a"},
    "ethereum": {"name": "Ethereum", "symbol": "ETH", "color": "#627eea"},
    "dogecoin": {"name": "Dogecoin", "symbol": "DOGE", "color": "#c2a633"},
    "cardano": {"name": "Cardano", "symbol": "ADA", "color": "#0033ad"}
}

# Генерация реалистичного графика цен
def generate_price_history(base_price, volatility=0.02, points=50):
    """Генерирует историю цен с реалистичными колебаниями"""
    prices = [base_price]
    for i in range(1, points):
        change_percent = random.uniform(-volatility, volatility)
        # Добавляем тренд для реалистичности
        trend = random.uniform(-0.005, 0.005)
        change_percent += trend
        
        new_price = prices[-1] * (1 + change_percent)
        # Минимальная цена 0.1
        new_price = max(new_price, 0.1)
        prices.append(round(new_price, 2))
    
    return prices

def get_current_prices():
    """Возвращает текущие цены для всех криптовалют"""
    return {
        "bitcoin": random.uniform(45000, 55000),
        "ethereum": random.uniform(2500, 3500),
        "dogecoin": random.uniform(0.1, 0.2),
        "cardano": random.uniform(0.4, 0.6)
    }

# CORS headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Health check
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "crypto-trader"})

# Получить данные игрока
@app.route('/api/player/<user_id>', methods=['GET'])
def get_player_data(user_id):
    try:
        if user_id not in game_data["players"]:
            # Создаем нового игрока
            current_prices = get_current_prices()
            player_data = {
                "balance": 10000.00,  # Стартовый баланс
                "portfolio": {crypto: 0 for crypto in CRYPTOS},
                "portfolio_value": 0,
                "total_value": 10000.00,
                "transaction_history": [],
                "created_at": datetime.now().isoformat(),
                # Генерируем историю цен для графиков
                "price_history": {
                    crypto: generate_price_history(current_prices[crypto]) 
                    for crypto in CRYPTOS
                },
                "current_prices": current_prices
            }
            game_data["players"][user_id] = player_data
        
        # Обновляем текущие цены и стоимость портфеля
        player = game_data["players"][user_id]
        player["current_prices"] = get_current_prices()
        
        # Пересчитываем стоимость портфеля
        portfolio_value = sum(
            player["portfolio"][crypto] * player["current_prices"][crypto] 
            for crypto in CRYPTOS
        )
        player["portfolio_value"] = round(portfolio_value, 2)
        player["total_value"] = round(player["balance"] + portfolio_value, 2)
        
        return jsonify(player)
        
    except Exception as e:
        print(f"Error in get_player_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Купить криптовалюту
@app.route('/api/buy', methods=['POST'])
def buy_crypto():
    try:
        user_id = request.json.get('user_id')
        crypto = request.json.get('crypto')
        amount = float(request.json.get('amount', 0))
        
        if not user_id or not crypto or amount <= 0:
            return jsonify({"error": "Invalid parameters"}), 400
            
        if user_id not in game_data["players"]:
            return jsonify({"error": "Player not found"}), 404
            
        if crypto not in CRYPTOS:
            return jsonify({"error": "Invalid cryptocurrency"}), 400
            
        player = game_data["players"][user_id]
        price = player["current_prices"][crypto]
        total_cost = amount * price
        
        if player["balance"] < total_cost:
            return jsonify({
                "success": False,
                "error": f"Недостаточно средств. Нужно: ${total_cost:.2f}"
            })
        
        # Совершаем покупку
        player["balance"] -= total_cost
        player["portfolio"][crypto] += amount
        
        # Добавляем в историю транзакций
        transaction = {
            "type": "buy",
            "crypto": crypto,
            "amount": amount,
            "price": price,
            "total": total_cost,
            "timestamp": datetime.now().isoformat()
        }
        player["transaction_history"].append(transaction)
        
        # Обновляем график (добавляем новую точку)
        new_price = price * random.uniform(0.99, 1.01)  # Небольшое изменение
        player["price_history"][crypto].append(round(new_price, 2))
        # Держим только последние 50 точек
        if len(player["price_history"][crypto]) > 50:
            player["price_history"][crypto].pop(0)
        
        return jsonify({
            "success": True,
            "message": f"Куплено {amount} {CRYPTOS[crypto]['symbol']} за ${total_cost:.2f}",
            "player": player
        })
        
    except Exception as e:
        print(f"Error in buy_crypto: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Продать криптовалюту
@app.route('/api/sell', methods=['POST'])
def sell_crypto():
    try:
        user_id = request.json.get('user_id')
        crypto = request.json.get('crypto')
        amount = float(request.json.get('amount', 0))
        
        if not user_id or not crypto or amount <= 0:
            return jsonify({"error": "Invalid parameters"}), 400
            
        if user_id not in game_data["players"]:
            return jsonify({"error": "Player not found"}), 404
            
        if crypto not in CRYPTOS:
            return jsonify({"error": "Invalid cryptocurrency"}), 400
            
        player = game_data["players"][user_id]
        
        if player["portfolio"][crypto] < amount:
            return jsonify({
                "success": False,
                "error": f"Недостаточно {CRYPTOS[crypto]['symbol']} для продажи"
            })
        
        price = player["current_prices"][crypto]
        total_income = amount * price
        
        # Совершаем продажу
        player["balance"] += total_income
        player["portfolio"][crypto] -= amount
        
        # Добавляем в историю транзакций
        transaction = {
            "type": "sell",
            "crypto": crypto,
            "amount": amount,
            "price": price,
            "total": total_income,
            "timestamp": datetime.now().isoformat()
        }
        player["transaction_history"].append(transaction)
        
        # Обновляем график
        new_price = price * random.uniform(0.99, 1.01)
        player["price_history"][crypto].append(round(new_price, 2))
        if len(player["price_history"][crypto]) > 50:
            player["price_history"][crypto].pop(0)
        
        return jsonify({
            "success": True,
            "message": f"Продано {amount} {CRYPTOS[crypto]['symbol']} за ${total_income:.2f}",
            "player": player
        })
        
    except Exception as e:
        print(f"Error in sell_crypto: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Обновить цены (имитация рыночных изменений)
@app.route('/api/update_prices', methods=['POST'])
def update_prices():
    try:
        user_id = request.json.get('user_id')
        
        if user_id not in game_data["players"]:
            return jsonify({"error": "Player not found"}), 404
            
        player = game_data["players"][user_id]
        
        # Генерируем новые цены с более значительными изменениями
        for crypto in CRYPTOS:
            current_price = player["current_prices"][crypto]
            # Более волатильные изменения (до 5%)
            change_percent = random.uniform(-0.05, 0.05)
            new_price = current_price * (1 + change_percent)
            new_price = max(new_price, 0.1)  # Минимальная цена
            
            player["current_prices"][crypto] = round(new_price, 2)
            
            # Обновляем график
            player["price_history"][crypto].append(round(new_price, 2))
            if len(player["price_history"][crypto]) > 50:
                player["price_history"][crypto].pop(0)
        
        return jsonify({
            "success": True,
            "message": "Цены обновлены",
            "player": player
        })
        
    except Exception as e:
        print(f"Error in update_prices: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"🚀 Starting Crypto Trader on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
