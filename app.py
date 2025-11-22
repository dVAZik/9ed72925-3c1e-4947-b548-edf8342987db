from flask import Flask, request, jsonify, render_template
import json
import random
import math
from datetime import datetime, timedelta
import os
import atexit
import threading
import time

app = Flask(__name__)
port = int(os.environ.get("PORT", 5000))

# Файл для хранения данных
DATA_FILE = "game_data.json"

# Загрузка данных из файла
def load_game_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Loaded game data with {len(data.get('players', {}))} players")
                return data
    except Exception as e:
        print(f"❌ Error loading data: {e}")
    print("🆕 Starting with fresh game data")
    return {"players": {}, "last_save": datetime.now().isoformat()}

# Сохранение данных в файл
def save_game_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            game_data["last_save"] = datetime.now().isoformat()
            json.dump(game_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Game data saved: {len(game_data.get('players', {}))} players")
    except Exception as e:
        print(f"❌ Error saving data: {e}")

# Автосохранение при выходе
def save_on_exit():
    print("💾 Saving data before exit...")
    save_game_data()

atexit.register(save_on_exit)

# Загружаем данные при старте
game_data = load_game_data()

# Популярные криптовалюты с реалистичными параметрами
CRYPTOS = {
    "BTC": {
        "name": "Bitcoin", 
        "color": "#f7931a",
        "volatility": 0.03,
        "base_price": 45000,
        "emoji": "₿"
    },
    "ETH": {
        "name": "Ethereum", 
        "color": "#627eea",
        "volatility": 0.04,
        "base_price": 3000,
        "emoji": "🔷"
    },
    "BNB": {
        "name": "Binance Coin", 
        "color": "#f3ba2f",
        "volatility": 0.05,
        "base_price": 350,
        "emoji": "💠"
    },
    "XRP": {
        "name": "Ripple", 
        "color": "#23292f",
        "volatility": 0.06,
        "base_price": 0.6,
        "emoji": "⚡"
    },
    "ADA": {
        "name": "Cardano", 
        "color": "#0033ad",
        "volatility": 0.05,
        "base_price": 0.5,
        "emoji": "🃏"
    },
    "DOGE": {
        "name": "Dogecoin", 
        "color": "#c2a633",
        "volatility": 0.08,
        "base_price": 0.15,
        "emoji": "🐕"
    },
    "SOL": {
        "name": "Solana", 
        "color": "#00ffbd",
        "volatility": 0.07,
        "base_price": 100,
        "emoji": "🔆"
    },
    "DOT": {
        "name": "Polkadot", 
        "color": "#e6007a",
        "volatility": 0.06,
        "base_price": 7,
        "emoji": "🔴"
    }
}

# Ордербук (стакан цен) - временное хранение в памяти
order_books = {}

def initialize_order_book(symbol, base_price):
    """Инициализация стакана цен"""
    spread = base_price * 0.02
    
    bids = []
    asks = []
    
    for i in range(5):
        bid_price = base_price * (1 - 0.02 * (i + 1))
        ask_price = base_price * (1 + 0.02 * (i + 1))
        
        bids.append({
            "price": round(bid_price, 4 if base_price < 1 else 2),
            "amount": round(random.uniform(0.1, 5.0), 4),
            "total": round(bid_price * random.uniform(0.1, 5.0), 2)
        })
        
        asks.append({
            "price": round(ask_price, 4 if base_price < 1 else 2),
            "amount": round(random.uniform(0.1, 5.0), 4),
            "total": round(ask_price * random.uniform(0.1, 5.0), 2)
        })
    
    return {"bids": bids, "asks": asks}

def generate_realistic_price(previous_price, volatility, symbol):
    """Генерация реалистичной цены с трендом"""
    change = random.gauss(0, volatility)
    mean_reversion = (CRYPTOS[symbol]["base_price"] - previous_price) * 0.001
    change += mean_reversion
    
    new_price = previous_price * (1 + change)
    new_price = max(new_price, previous_price * 0.3)
    new_price = min(new_price, previous_price * 3.0)
    
    if new_price < 1:
        return round(new_price, 4)
    else:
        return round(new_price, 2)

def update_order_book(symbol, current_price):
    """Обновление стакана цен"""
    if symbol not in order_books:
        order_books[symbol] = initialize_order_book(symbol, current_price)
        return order_books[symbol]
    
    book = order_books[symbol]
    
    for i, bid in enumerate(book["bids"]):
        new_price = current_price * (1 - 0.02 * (i + 1))
        bid["price"] = round(new_price, 4 if current_price < 1 else 2)
        bid["total"] = round(bid["amount"] * new_price, 2)
    
    for i, ask in enumerate(book["asks"]):
        new_price = current_price * (1 + 0.02 * (i + 1))
        ask["price"] = round(new_price, 4 if current_price < 1 else 2)
        ask["total"] = round(ask["amount"] * new_price, 2)
    
    if random.random() < 0.3:
        if len(book["bids"]) > 3 and random.random() < 0.5:
            book["bids"].pop()
        else:
            new_bid_price = current_price * (1 - 0.02 * (len(book["bids"]) + 1))
            book["bids"].append({
                "price": round(new_bid_price, 4 if current_price < 1 else 2),
                "amount": round(random.uniform(0.1, 3.0), 4),
                "total": round(new_bid_price * random.uniform(0.1, 3.0), 2)
            })
    
    if random.random() < 0.3:
        if len(book["asks"]) > 3 and random.random() < 0.5:
            book["asks"].pop()
        else:
            new_ask_price = current_price * (1 + 0.02 * (len(book["asks"]) + 1))
            book["asks"].append({
                "price": round(new_ask_price, 4 if current_price < 1 else 2),
                "amount": round(random.uniform(0.1, 3.0), 4),
                "total": round(new_ask_price * random.uniform(0.1, 3.0), 2)
            })
    
    return book

def create_new_player_data():
    """Создание данных для нового игрока"""
    player_data = {
        "balance": 10000.00,
        "portfolio": {symbol: 0 for symbol in CRYPTOS},
        "portfolio_value": 0,
        "total_value": 10000.00,
        "orders": [],
        "price_history": {},
        "current_prices": {},
        "order_books": {},
        "created_at": datetime.now().isoformat(),
        "last_login": datetime.now().isoformat()
    }
    
    # Инициализируем цены и стаканы
    for symbol, crypto in CRYPTOS.items():
        price = crypto["base_price"] * random.uniform(0.8, 1.2)
        player_data["current_prices"][symbol] = price
        
        # Создаем реалистичную историю цен
        history = [price]
        for _ in range(49):
            history.append(generate_realistic_price(history[-1], crypto["volatility"], symbol))
        player_data["price_history"][symbol] = history
        
        # Инициализируем стакан
        player_data["order_books"][symbol] = initialize_order_book(symbol, price)
    
    return player_data

# CORS headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    players_count = len(game_data.get("players", {}))
    last_save = game_data.get("last_save", "Never")
    return jsonify({
        "status": "healthy", 
        "service": "crypto-exchange",
        "players_count": players_count,
        "last_save": last_save
    })

# Эндпоинт для принудительного сохранения
@app.route('/api/save', methods=['POST'])
def force_save():
    try:
        save_game_data()
        return jsonify({"success": True, "message": "Data saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Эндпоинт для сброса игрока (для тестирования)
@app.route('/api/reset_player/<user_id>', methods=['POST'])
def reset_player(user_id):
    try:
        player_data = create_new_player_data()
        game_data["players"][user_id] = player_data
        save_game_data()
        return jsonify({
            "success": True, 
            "message": f"Player {user_id} reset successfully",
            "player": player_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/player/<user_id>', methods=['GET'])
def get_player_data(user_id):
    try:
        if user_id not in game_data["players"]:
            # Создаем нового игрока
            player_data = create_new_player_data()
            game_data["players"][user_id] = player_data
            save_game_data()  # Сохраняем при создании нового игрока
            print(f"✅ Created new player: {user_id}")
        
        player = game_data["players"][user_id]
        player["last_login"] = datetime.now().isoformat()
        
        # Обновляем цены и стаканы для ВСЕХ криптовалют
        for symbol, crypto in CRYPTOS.items():
            current_price = player["current_prices"][symbol]
            new_price = generate_realistic_price(current_price, crypto["volatility"], symbol)
            
            player["current_prices"][symbol] = new_price
            player["price_history"][symbol].append(new_price)
            if len(player["price_history"][symbol]) > 50:
                player["price_history"][symbol].pop(0)
            
            # Обновляем стакан
            player["order_books"][symbol] = update_order_book(symbol, new_price)
        
        # Пересчитываем стоимость портфеля
        portfolio_value = sum(
            player["portfolio"][symbol] * player["current_prices"][symbol] 
            for symbol in CRYPTOS
        )
        player["portfolio_value"] = round(portfolio_value, 2)
        player["total_value"] = round(player["balance"] + portfolio_value, 2)
        
        return jsonify(player)
        
    except Exception as e:
        print(f"Error in get_player_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/place_order', methods=['POST'])
def place_order():
    try:
        user_id = request.json.get('user_id')
        symbol = request.json.get('symbol')
        order_type = request.json.get('type')
        amount = float(request.json.get('amount', 0))
        price_type = request.json.get('price_type')
        limit_price = float(request.json.get('limit_price', 0))
        
        if not all([user_id, symbol, order_type, amount]):
            return jsonify({"error": "Missing parameters"}), 400
            
        if user_id not in game_data["players"]:
            return jsonify({"error": "Player not found"}), 404
            
        if symbol not in CRYPTOS:
            return jsonify({"error": "Invalid symbol"}), 400
        
        player = game_data["players"][user_id]
        current_price = player["current_prices"][symbol]
        
        if price_type == 'market':
            execution_price = current_price
            total_cost = amount * execution_price
            
            if order_type == 'buy':
                if player["balance"] < total_cost:
                    return jsonify({
                        "success": False,
                        "error": f"Недостаточно средств. Нужно: ${total_cost:.2f}"
                    })
                
                player["balance"] -= total_cost
                player["portfolio"][symbol] += amount
                
            else:
                if player["portfolio"][symbol] < amount:
                    return jsonify({
                        "success": False,
                        "error": f"Недостаточно {symbol} для продажи"
                    })
                
                player["balance"] += total_cost
                player["portfolio"][symbol] -= amount
            
            order = {
                "id": len(player["orders"]) + 1,
                "symbol": symbol,
                "type": order_type,
                "amount": amount,
                "price": execution_price,
                "total": total_cost,
                "status": "filled",
                "timestamp": datetime.now().isoformat()
            }
            player["orders"].append(order)
            
            # Сохраняем после успешной сделки
            save_game_data()
            
            return jsonify({
                "success": True,
                "message": f"{order_type.upper()} {amount} {symbol} @ ${execution_price:.2f}",
                "order": order,
                "player": player
            })
        
        else:
            order = {
                "id": len(player["orders"]) + 1,
                "symbol": symbol,
                "type": order_type,
                "amount": amount,
                "price": limit_price,
                "total": amount * limit_price,
                "status": "pending",
                "timestamp": datetime.now().isoformat()
            }
            player["orders"].append(order)
            
            # Сохраняем лимитный ордер
            save_game_data()
            
            return jsonify({
                "success": True,
                "message": f"Limit order placed: {order_type} {amount} {symbol} @ ${limit_price:.2f}",
                "order": order,
                "player": player
            })
        
    except Exception as e:
        print(f"Error in place_order: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/update_prices', methods=['POST'])
def update_prices():
    try:
        user_id = request.json.get('user_id')
        
        if user_id not in game_data["players"]:
            return jsonify({"error": "Player not found"}), 404
            
        player = game_data["players"][user_id]
        
        for symbol, crypto in CRYPTOS.items():
            current_price = player["current_prices"][symbol]
            new_price = generate_realistic_price(current_price, crypto["volatility"] * 2, symbol)
            
            player["current_prices"][symbol] = new_price
            player["price_history"][symbol].append(new_price)
            if len(player["price_history"][symbol]) > 50:
                player["price_history"][symbol].pop(0)
            
            player["order_books"][symbol] = update_order_book(symbol, new_price)
        
        return jsonify({
            "success": True,
            "message": "Prices updated",
            "player": player
        })
        
    except Exception as e:
        print(f"Error in update_prices: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Эндпоинт для получения статистики
@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        players = game_data.get("players", {})
        total_players = len(players)
        total_balance = sum(player['balance'] for player in players.values())
        total_portfolio_value = sum(player['portfolio_value'] for player in players.values())
        
        return jsonify({
            "total_players": total_players,
            "total_balance": total_balance,
            "total_portfolio_value": total_portfolio_value,
            "total_wealth": total_balance + total_portfolio_value,
            "last_save": game_data.get("last_save", "Never")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Периодическое автосохранение
def auto_save():
    while True:
        time.sleep(300)  # Сохраняем каждые 5 минут
        save_game_data()

# Запускаем автосохранение в отдельном потоке
auto_save_thread = threading.Thread(target=auto_save, daemon=True)
auto_save_thread.start()

if __name__ == '__main__':
    print(f"🚀 Starting Crypto Exchange Pro on port {port}")
    print(f"💾 Data will be saved to: {DATA_FILE}")
    print(f"📊 Current players: {len(game_data.get('players', {}))}")
    app.run(host='0.0.0.0', port=port, debug=False)
