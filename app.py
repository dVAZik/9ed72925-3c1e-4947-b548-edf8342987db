from flask import Flask, request, jsonify, render_template
import json
import random
import math
from datetime import datetime, timedelta
import os
import atexit
import threading
import time
import hashlib
import functools

app = Flask(__name__)
port = int(os.environ.get("PORT", 5000))

# Безопасная конфигурация администратора
class AdminConfig:
    def __init__(self):
        self.config_file = "admin_config.json"
        self.max_attempts = 3
        self.lock_time = 900  # 15 минут блокировки
        self.failed_attempts = {}
        
    def get_password_hash(self):
        """Получение хеша пароля из переменных окружения"""
        env_password = os.environ.get("ADMIN_PASSWORD")
        if env_password:
            print("🔐 Using admin password from environment variable")
            return self.hash_password(env_password)
        
        # Резервный вариант - случайный пароль
        default_password = "change_me_" + str(random.randint(10000, 99999))
        default_hash = self.hash_password(default_password)
        print(f"⚠️  GENERATED DEFAULT ADMIN PASSWORD: {default_password}")
        print("⚠️  Set ADMIN_PASSWORD environment variable in Render dashboard!")
        return default_hash
    
    def hash_password(self, password):
        """Хеширование пароля"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password):
        """Проверка пароля"""
        return self.hash_password(password) == self.get_password_hash()
    
    def change_password(self, new_password):
        """Смена пароля (только через переменные окружения)"""
        return False, "Password can only be changed via ADMIN_PASSWORD environment variable in Render dashboard"
    
    def is_locked(self, ip):
        """Проверка блокировки IP"""
        if ip in self.failed_attempts:
            attempts, last_attempt = self.failed_attempts[ip]
            if attempts >= self.max_attempts:
                if time.time() - last_attempt < self.lock_time:
                    return True
                else:
                    # Сброс после времени блокировки
                    del self.failed_attempts[ip]
        return False
    
    def record_attempt(self, ip, success):
        """Запись попытки входа"""
        if success:
            if ip in self.failed_attempts:
                del self.failed_attempts[ip]
        else:
            if ip not in self.failed_attempts:
                self.failed_attempts[ip] = [1, time.time()]
            else:
                self.failed_attempts[ip][0] += 1
                self.failed_attempts[ip][1] = time.time()

# Инициализация системы безопасности
admin_config = AdminConfig()

def get_client_ip():
    """Получение IP клиента"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        return request.remote_addr

# Декоратор для защиты админ эндпоинтов
def require_admin_auth(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            client_ip = get_client_ip()
            
            if admin_config.is_locked(client_ip):
                return jsonify({
                    "success": False, 
                    "error": "Too many failed attempts. Try again in 15 minutes."
                })
            
            password = request.json.get('password')
            if not password or not admin_config.verify_password(password):
                admin_config.record_attempt(client_ip, False)
                remaining = admin_config.max_attempts - admin_config.failed_attempts.get(client_ip, [0])[0]
                return jsonify({
                    "success": False, 
                    "error": f"Invalid password. {remaining} attempts remaining"
                })
            
            # Успешная аутентификация
            admin_config.record_attempt(client_ip, True)
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return decorated_function

# Файл для хранения данных игры
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
    return {"players": {}, "last_save": datetime.now().isoformat(), "system_stats": {}}

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

# Обновляем системную статистику
def update_system_stats():
    players = game_data.get("players", {})
    total_players = len(players)
    
    if total_players > 0:
        total_balance = sum(player.get('balance', 0) for player in players.values())
        total_portfolio = sum(player.get('portfolio_value', 0) for player in players.values())
        total_wealth = total_balance + total_portfolio
        
        # Топ игроков по балансу
        top_players = sorted(
            [(user_id, player) for user_id, player in players.items()],
            key=lambda x: x[1].get('total_value', 0),
            reverse=True
        )[:5]
        
        # Статистика по криптовалютам
        crypto_stats = {}
        for symbol in CRYPTOS.keys():
            total_owned = sum(player.get('portfolio', {}).get(symbol, 0) for player in players.values())
            crypto_stats[symbol] = {
                'total_owned': total_owned,
                'players_owning': sum(1 for player in players.values() if player.get('portfolio', {}).get(symbol, 0) > 0)
            }
        
        game_data["system_stats"] = {
            "total_players": total_players,
            "total_balance": total_balance,
            "total_portfolio_value": total_portfolio,
            "total_wealth": total_wealth,
            "average_balance": total_balance / total_players if total_players > 0 else 0,
            "top_players": [
                {
                    "user_id": user_id,
                    "username": player.get('username', user_id),
                    "total_value": player.get('total_value', 0),
                    "balance": player.get('balance', 0)
                }
                for user_id, player in top_players
            ],
            "crypto_stats": crypto_stats,
            "last_updated": datetime.now().isoformat()
        }
    else:
        game_data["system_stats"] = {
            "total_players": 0,
            "total_balance": 0,
            "total_portfolio_value": 0,
            "total_wealth": 0,
            "average_balance": 0,
            "top_players": [],
            "crypto_stats": {},
            "last_updated": datetime.now().isoformat()
        }

# Обновляем статистику при старте
update_system_stats()

# Криптовалюты
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

# Ордербук (стакан цен)
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
        "last_login": datetime.now().isoformat(),
        "username": "Trader"
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

# Основные маршруты
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/health')
def health_check():
    players_count = len(game_data.get("players", {}))
    last_save = game_data.get("last_save", "Never")
    return jsonify({
        "status": "healthy", 
        "service": "crypto-exchange",
        "players_count": players_count,
        "last_save": last_save,
        "admin_available": True
    })

# АДМИН ЭНДПОИНТЫ

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    client_ip = get_client_ip()
    
    if admin_config.is_locked(client_ip):
        return jsonify({
            "success": False, 
            "error": "Too many failed attempts. Try again in 15 minutes."
        })
    
    password = request.json.get('password')
    if admin_config.verify_password(password):
        admin_config.record_attempt(client_ip, True)
        return jsonify({"success": True, "message": "Login successful"})
    else:
        admin_config.record_attempt(client_ip, False)
        remaining = admin_config.max_attempts - admin_config.failed_attempts.get(client_ip, [0])[0]
        return jsonify({
            "success": False, 
            "error": f"Invalid password. {remaining} attempts remaining"
        })

@app.route('/api/admin/change_password', methods=['POST'])
@require_admin_auth
def admin_change_password_route():
    return jsonify({
        "success": False, 
        "error": "Password can only be changed via ADMIN_PASSWORD environment variable in Render dashboard"
    })

@app.route('/api/admin/stats', methods=['POST'])
@require_admin_auth
def admin_stats_route():
    update_system_stats()
    return jsonify({
        "success": True,
        "stats": game_data["system_stats"],
        "last_save": game_data.get("last_save", "Never")
    })

@app.route('/api/admin/players', methods=['POST'])
@require_admin_auth
def admin_players_route():
    players = game_data.get("players", {})
    players_list = []
    
    for user_id, player in players.items():
        players_list.append({
            "user_id": user_id,
            "username": player.get('username', 'Unknown'),
            "balance": player.get('balance', 0),
            "portfolio_value": player.get('portfolio_value', 0),
            "total_value": player.get('total_value', 0),
            "created_at": player.get('created_at', 'Unknown'),
            "last_login": player.get('last_login', 'Never'),
            "orders_count": len(player.get('orders', [])),
            "portfolio": player.get('portfolio', {})
        })
    
    return jsonify({
        "success": True,
        "players": players_list,
        "total_count": len(players_list)
    })

@app.route('/api/admin/player/<user_id>', methods=['POST'])
@require_admin_auth
def admin_player_manage_route(user_id):
    action = request.json.get('action')
    
    if user_id not in game_data["players"]:
        return jsonify({"success": False, "error": "Player not found"})
    
    player = game_data["players"][user_id]
    
    if action == "reset":
        new_data = create_new_player_data()
        game_data["players"][user_id] = new_data
        save_game_data()
        return jsonify({"success": True, "message": f"Player {user_id} reset successfully"})
    
    elif action == "add_balance":
        amount = float(request.json.get('amount', 0))
        player["balance"] += amount
        player["total_value"] = player["balance"] + player["portfolio_value"]
        save_game_data()
        return jsonify({"success": True, "message": f"Added ${amount} to {user_id}"})
    
    elif action == "set_balance":
        amount = float(request.json.get('amount', 0))
        player["balance"] = amount
        player["total_value"] = player["balance"] + player["portfolio_value"]
        save_game_data()
        return jsonify({"success": True, "message": f"Set balance to ${amount} for {user_id}"})
    
    elif action == "get_info":
        return jsonify({
            "success": True,
            "player": player
        })
    
    else:
        return jsonify({"success": False, "error": "Unknown action"})

@app.route('/api/admin/system', methods=['POST'])
@require_admin_auth
def admin_system_route():
    action = request.json.get('action')
    
    if action == "save":
        save_game_data()
        return jsonify({"success": True, "message": "Data saved successfully"})
    
    elif action == "reload":
        global game_data
        game_data = load_game_data()
        update_system_stats()
        return jsonify({"success": True, "message": "Data reloaded successfully"})
    
    elif action == "update_prices_all":
        for user_id, player in game_data["players"].items():
            for symbol, crypto in CRYPTOS.items():
                current_price = player["current_prices"][symbol]
                new_price = generate_realistic_price(current_price, crypto["volatility"] * 2, symbol)
                
                player["current_prices"][symbol] = new_price
                player["price_history"][symbol].append(new_price)
                if len(player["price_history"][symbol]) > 50:
                    player["price_history"][symbol].pop(0)
                
                player["order_books"][symbol] = update_order_book(symbol, new_price)
        
        save_game_data()
        return jsonify({"success": True, "message": "Prices updated for all players"})
    
    else:
        return jsonify({"success": False, "error": "Unknown action"})

# ИГРОВЫЕ ЭНДПОИНТЫ

@app.route('/api/save', methods=['POST'])
def force_save():
    try:
        save_game_data()
        return jsonify({"success": True, "message": "Data saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            player_data = create_new_player_data()
            game_data["players"][user_id] = player_data
            save_game_data()
            print(f"✅ Created new player: {user_id}")
        
        player = game_data["players"][user_id]
        player["last_login"] = datetime.now().isoformat()
        
        for symbol, crypto in CRYPTOS.items():
            current_price = player["current_prices"][symbol]
            new_price = generate_realistic_price(current_price, crypto["volatility"], symbol)
            
            player["current_prices"][symbol] = new_price
            player["price_history"][symbol].append(new_price)
            if len(player["price_history"][symbol]) > 50:
                player["price_history"][symbol].pop(0)
            
            player["order_books"][symbol] = update_order_book(symbol, new_price)
        
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

# Автосохранение
def auto_save():
    while True:
        time.sleep(300)
        save_game_data()

auto_save_thread = threading.Thread(target=auto_save, daemon=True)
auto_save_thread.start()

if __name__ == '__main__':
    print(f"🚀 Starting Crypto Exchange Pro on port {port}")
    print(f"💾 Data file: {DATA_FILE}")
    print(f"📊 Current players: {len(game_data.get('players', {}))}")
    print(f"🔐 Admin panel: /admin")
    print(f"🔒 Admin password: Set via ADMIN_PASSWORD environment variable")
    app.run(host='0.0.0.0', port=port, debug=False)
