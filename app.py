from flask import Flask, request, jsonify, render_template
import json
import random
import math
from datetime import datetime, timedelta
import os
import time
import hashlib
import functools
from database import db

app = Flask(__name__)
port = int(os.environ.get("PORT", 5000))

ADMIN_USER_ID = "1175194423"

class AdminConfig:
    def __init__(self):
        self.max_attempts = 3
        self.lock_time = 900
        self.failed_attempts = {}
        
    def get_password_hash(self):
        env_password = os.environ.get("ADMIN_PASSWORD")
        if env_password:
            return self.hash_password(env_password)
        
        default_password = "admin123"
        default_hash = self.hash_password(default_password)
        print(f"⚠️  DEFAULT ADMIN PASSWORD: {default_password}")
        return default_hash
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password):
        return self.hash_password(password) == self.get_password_hash()
    
    def is_locked(self, ip):
        if ip in self.failed_attempts:
            attempts, last_attempt = self.failed_attempts[ip]
            if attempts >= self.max_attempts:
                if time.time() - last_attempt < self.lock_time:
                    return True
                else:
                    del self.failed_attempts[ip]
        return False
    
    def record_attempt(self, ip, success):
        if success:
            if ip in self.failed_attempts:
                del self.failed_attempts[ip]
        else:
            if ip not in self.failed_attempts:
                self.failed_attempts[ip] = [1, time.time()]
            else:
                self.failed_attempts[ip][0] += 1
                self.failed_attempts[ip][1] = time.time()

admin_config = AdminConfig()

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        return request.remote_addr

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
            
            admin_config.record_attempt(client_ip, True)
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return decorated_function

# Усложненная конфигурация криптовалют
CRYPTOS = {
    "BTC": {
        "name": "Bitcoin", 
        "color": "#f7931a",
        "volatility": 0.015,
        "base_price": 45000,
        "emoji": "₿",
        "mining_difficulty": 100,
        "mining_reward": 0.0001
    },
    "ETH": {
        "name": "Ethereum", 
        "color": "#627eea",
        "volatility": 0.018,
        "base_price": 3000,
        "emoji": "🔷",
        "mining_difficulty": 80,
        "mining_reward": 0.001
    },
    "BNB": {
        "name": "Binance Coin", 
        "color": "#f3ba2f",
        "volatility": 0.022,
        "base_price": 350,
        "emoji": "💠",
        "mining_difficulty": 60,
        "mining_reward": 0.01
    },
    "XRP": {
        "name": "Ripple", 
        "color": "#23292f",
        "volatility": 0.025,
        "base_price": 0.6,
        "emoji": "⚡",
        "mining_difficulty": 40,
        "mining_reward": 0.1
    },
    "ADA": {
        "name": "Cardano", 
        "color": "#0033ad",
        "volatility": 0.020,
        "base_price": 0.5,
        "emoji": "🃏",
        "mining_difficulty": 50,
        "mining_reward": 0.05
    },
    "DOGE": {
        "name": "Dogecoin", 
        "color": "#c2a633",
        "volatility": 0.028,
        "base_price": 0.15,
        "emoji": "🐕",
        "mining_difficulty": 30,
        "mining_reward": 1.0
    },
    "SOL": {
        "name": "Solana", 
        "color": "#00ffbd",
        "volatility": 0.024,
        "base_price": 100,
        "emoji": "🔆",
        "mining_difficulty": 45,
        "mining_reward": 0.02
    },
    "DOT": {
        "name": "Polkadot", 
        "color": "#e6007a",
        "volatility": 0.021,
        "base_price": 7,
        "emoji": "🔴",
        "mining_difficulty": 55,
        "mining_reward": 0.03
    }
}

# Конфигурация майнинга
MINING_CONFIG = {
    "base_energy_cost": 10,
    "energy_regeneration_rate": 0.5,
    "max_energy": 100,
    "mining_cooldown": 120,
    "equipment_levels": {
        1: {"name": "Basic GPU", "multiplier": 1.0, "cost": 1000},
        2: {"name": "Advanced GPU", "multiplier": 1.3, "cost": 5000},
        3: {"name": "ASIC Miner", "multiplier": 1.8, "cost": 20000},
        4: {"name": "Mining Farm", "multiplier": 2.5, "cost": 100000},
        5: {"name": "Industrial Farm", "multiplier": 4.0, "cost": 500000}
    }
}

def generate_realistic_price(previous_price, volatility, symbol):
    change = random.gauss(0, volatility)
    mean_reversion = (CRYPTOS[symbol]["base_price"] - previous_price) * 0.0003
    
    change += mean_reversion
    
    new_price = previous_price * (1 + change)
    new_price = max(new_price, previous_price * 0.7)
    new_price = min(new_price, previous_price * 1.5)
    
    if new_price < 1:
        return round(new_price, 4)
    else:
        return round(new_price, 2)

def calculate_trading_fee(amount, price, order_type):
    base_fee = 0.0025
    if order_type == 'market':
        base_fee += 0.0015
    return amount * price * base_fee

def initialize_order_book(symbol, base_price):
    bids = []
    asks = []
    
    spread = 0.015
    
    for i in range(5):
        bid_price = base_price * (1 - spread * (i + 1))
        ask_price = base_price * (1 + spread * (i + 1))
        
        bids.append({
            "price": round(bid_price, 4 if base_price < 1 else 2),
            "amount": round(random.uniform(0.05, 1.5), 4),
            "total": round(bid_price * random.uniform(0.05, 1.5), 2)
        })
        
        asks.append({
            "price": round(ask_price, 4 if base_price < 1 else 2),
            "amount": round(random.uniform(0.05, 1.5), 4),
            "total": round(ask_price * random.uniform(0.05, 1.5), 2)
        })
    
    return {"bids": bids, "asks": asks}

def update_order_book(symbol, current_price):
    return initialize_order_book(symbol, current_price)

def create_new_player_data():
    player_data = {
        "balance": 500.00,
        "portfolio": {symbol: 0 for symbol in CRYPTOS},
        "portfolio_value": 0,
        "total_value": 500.00,
        "orders": [],
        "price_history": {},
        "current_prices": {},
        "order_books": {},
        "created_at": datetime.now().isoformat(),
        "last_login": datetime.now().isoformat(),
        "username": "Trader",
        "mining": {
            "energy": MINING_CONFIG["max_energy"],
            "last_mining_time": datetime.now().isoformat(),
            "equipment_level": 1,
            "total_mined": {symbol: 0 for symbol in CRYPTOS},
            "mining_power": 1.0
        },
        "stats": {
            "total_trades": 0,
            "total_profit": 0,
            "daily_bonus_claimed": False,
            "login_streak": 1,
            "total_mining_rewards": 0
        }
    }
    
    for symbol, crypto in CRYPTOS.items():
        price = crypto["base_price"] * random.uniform(0.95, 1.05)
        player_data["current_prices"][symbol] = price
        
        history = [price]
        for _ in range(49):
            history.append(generate_realistic_price(history[-1], crypto["volatility"], symbol))
        player_data["price_history"][symbol] = history
        
        player_data["order_books"][symbol] = initialize_order_book(symbol, price)
    
    return player_data

class P2PManager:
    def __init__(self):
        self.orders_file = "p2p_orders.json"
        self.orders = self.load_orders()
    
    def load_orders(self):
        try:
            if os.path.exists(self.orders_file):
                with open(self.orders_file, 'r', encoding='utf-8') as f:
                    orders = json.load(f)
                    print(f"✅ Loaded {len(orders)} P2P orders")
                    return orders
        except Exception as e:
            print(f"❌ Error loading P2P orders: {e}")
        return []
    
    def save_orders(self):
        try:
            with open(self.orders_file, 'w', encoding='utf-8') as f:
                json.dump(self.orders, f, indent=2, ensure_ascii=False)
            print(f"💾 P2P orders saved: {len(self.orders)} orders")
        except Exception as e:
            print(f"❌ Error saving P2P orders: {e}")
    
    def create_order(self, user_id, symbol, amount, price, order_type, username="Trader"):
        order_id = len(self.orders) + 1
        order = {
            "id": order_id,
            "user_id": user_id,
            "username": username,
            "symbol": symbol,
            "amount": amount,
            "price": price,
            "total": amount * price,
            "type": order_type,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.orders.append(order)
        self.save_orders()
        return order
    
    def get_active_orders(self, symbol=None):
        active_orders = [order for order in self.orders if order["status"] == "active"]
        if symbol:
            active_orders = [order for order in active_orders if order["symbol"] == symbol]
        return active_orders
    
    def get_user_orders(self, user_id):
        return [order for order in self.orders if order["user_id"] == user_id]
    
    def get_order_by_id(self, order_id):
        for order in self.orders:
            if order["id"] == order_id:
                return order
        return None
    
    def cancel_order(self, order_id, user_id):
        order = self.get_order_by_id(order_id)
        if order and order["user_id"] == user_id and order["status"] == "active":
            order["status"] = "cancelled"
            order["updated_at"] = datetime.now().isoformat()
            self.save_orders()
            return True
        return False
    
    def execute_trade(self, order_id, buyer_id):
        order = self.get_order_by_id(order_id)
        if not order or order["status"] != "active":
            return False, "Order not found or not active"
        
        if order["user_id"] == buyer_id:
            return False, "Cannot trade with yourself"
        
        seller_data = db.get_player_data(order["user_id"])
        buyer_data = db.get_player_data(buyer_id)
        
        if not seller_data or not buyer_data:
            return False, "Player data not found"
        
        symbol = order["symbol"]
        amount = order["amount"]
        price = order["price"]
        total = order["total"]
        
        fee = total * 0.0015
        
        if order["type"] == "sell":
            if seller_data["portfolio"].get(symbol, 0) < amount:
                return False, f"Seller doesn't have enough {symbol}"
            
            if buyer_data["balance"] < total + fee:
                return False, "Buyer doesn't have enough balance"
            
            seller_data["portfolio"][symbol] = seller_data["portfolio"].get(symbol, 0) - amount
            seller_data["balance"] += total - fee
            
            buyer_data["portfolio"][symbol] = buyer_data["portfolio"].get(symbol, 0) + amount
            buyer_data["balance"] -= total
            
        else:
            if buyer_data["portfolio"].get(symbol, 0) < amount:
                return False, f"Buyer doesn't have enough {symbol}"
            
            if seller_data["balance"] < total + fee:
                return False, "Seller doesn't have enough balance"
            
            buyer_data["portfolio"][symbol] = buyer_data["portfolio"].get(symbol, 0) - amount
            buyer_data["balance"] += total - fee
            
            seller_data["portfolio"][symbol] = seller_data["portfolio"].get(symbol, 0) + amount
            seller_data["balance"] -= total
        
        db.save_player(order["user_id"], seller_data)
        db.save_player(buyer_id, buyer_data)
        
        order["status"] = "filled"
        order["updated_at"] = datetime.now().isoformat()
        order["filled_with"] = buyer_id
        self.save_orders()
        
        return True, "Trade executed successfully"

p2p_manager = P2PManager()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/p2p')
def p2p_market():
    return render_template('p2p.html')

@app.route('/mining')
def mining():
    return render_template('mining.html')

@app.route('/health')
def health_check():
    players_count = len(db.get_all_players())
    return jsonify({
        "status": "healthy", 
        "service": "crypto-exchange",
        "players_count": players_count,
        "admin_available": True,
        "p2p_available": True,
        "mining_available": True
    })

# МАЙНИНГ ЭНДПОИНТЫ
@app.route('/api/mining/status', methods=['POST'])
def mining_status():
    try:
        user_id = request.json.get('user_id')
        player = db.get_player_data(user_id)
        
        if not player:
            return jsonify({"success": False, "error": "Player not found"})
        
        last_mining_time = datetime.fromisoformat(player["mining"]["last_mining_time"].replace('Z', '+00:00'))
        time_diff = (datetime.now() - last_mining_time).total_seconds()
        energy_to_regenerate = min(
            time_diff / 60 * MINING_CONFIG["energy_regeneration_rate"],
            MINING_CONFIG["max_energy"] - player["mining"]["energy"]
        )
        
        if energy_to_regenerate > 0:
            player["mining"]["energy"] += energy_to_regenerate
            player["mining"]["last_mining_time"] = datetime.now().isoformat()
            db.save_player(user_id, player)
        
        mining_data = {
            "energy": player["mining"]["energy"],
            "max_energy": MINING_CONFIG["max_energy"],
            "equipment_level": player["mining"]["equipment_level"],
            "mining_power": player["mining"]["mining_power"],
            "total_mined": player["mining"]["total_mined"],
            "can_mine": player["mining"]["energy"] >= MINING_CONFIG["base_energy_cost"],
            "equipment_name": MINING_CONFIG["equipment_levels"][player["mining"]["equipment_level"]]["name"],
            "next_upgrade_cost": MINING_CONFIG["equipment_levels"][player["mining"]["equipment_level"] + 1]["cost"] if player["mining"]["equipment_level"] < len(MINING_CONFIG["equipment_levels"]) else None
        }
        
        return jsonify({
            "success": True,
            "mining": mining_data
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/mining/mine', methods=['POST'])
def mine_crypto():
    try:
        user_id = request.json.get('user_id')
        symbol = request.json.get('symbol')
        
        if symbol not in CRYPTOS:
            return jsonify({"success": False, "error": "Invalid cryptocurrency"})
        
        player = db.get_player_data(user_id)
        if not player:
            return jsonify({"success": False, "error": "Player not found"})
        
        if player["mining"]["energy"] < MINING_CONFIG["base_energy_cost"]:
            return jsonify({"success": False, "error": "Not enough energy"})
        
        last_mining_time = datetime.fromisoformat(player["mining"]["last_mining_time"].replace('Z', '+00:00'))
        time_diff = (datetime.now() - last_mining_time).total_seconds()
        if time_diff < MINING_CONFIG["mining_cooldown"]:
            return jsonify({"success": False, "error": f"Wait {int(MINING_CONFIG['mining_cooldown'] - time_diff)} seconds"})
        
        base_reward = CRYPTOS[symbol]["mining_reward"]
        difficulty = CRYPTOS[symbol]["mining_difficulty"]
        equipment_multiplier = MINING_CONFIG["equipment_levels"][player["mining"]["equipment_level"]]["multiplier"]
        player_multiplier = player["mining"]["mining_power"]
        
        success_chance = min(0.8, (equipment_multiplier * player_multiplier) / difficulty)
        
        if random.random() > success_chance:
            player["mining"]["energy"] -= MINING_CONFIG["base_energy_cost"] // 2
            player["mining"]["last_mining_time"] = datetime.now().isoformat()
            db.save_player(user_id, player)
            return jsonify({"success": False, "error": "Mining failed. Try again!"})
        
        reward = base_reward * equipment_multiplier * player_multiplier * random.uniform(0.7, 1.1)
        reward = round(reward, 6)
        
        player["portfolio"][symbol] = player["portfolio"].get(symbol, 0) + reward
        player["mining"]["energy"] -= MINING_CONFIG["base_energy_cost"]
        player["mining"]["last_mining_time"] = datetime.now().isoformat()
        player["mining"]["total_mined"][symbol] = player["mining"]["total_mined"].get(symbol, 0) + reward
        player["stats"]["total_mining_rewards"] += reward * player["current_prices"][symbol]
        
        db.save_player(user_id, player)
        
        return jsonify({
            "success": True,
            "reward": reward,
            "symbol": symbol,
            "energy_remaining": player["mining"]["energy"],
            "value": reward * player["current_prices"][symbol]
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/mining/upgrade', methods=['POST'])
def upgrade_equipment():
    try:
        user_id = request.json.get('user_id')
        player = db.get_player_data(user_id)
        
        if not player:
            return jsonify({"success": False, "error": "Player not found"})
        
        current_level = player["mining"]["equipment_level"]
        if current_level >= len(MINING_CONFIG["equipment_levels"]):
            return jsonify({"success": False, "error": "Maximum level reached"})
        
        next_level = current_level + 1
        upgrade_cost = MINING_CONFIG["equipment_levels"][next_level]["cost"]
        
        if player["balance"] < upgrade_cost:
            return jsonify({"success": False, "error": "Not enough balance"})
        
        player["balance"] -= upgrade_cost
        player["mining"]["equipment_level"] = next_level
        player["mining"]["mining_power"] = MINING_CONFIG["equipment_levels"][next_level]["multiplier"]
        
        db.save_player(user_id, player)
        
        return jsonify({
            "success": True,
            "message": f"Upgraded to {MINING_CONFIG['equipment_levels'][next_level]['name']}",
            "new_level": next_level,
            "new_power": player["mining"]["mining_power"]
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ЕЖЕДНЕВНЫЙ БОНУС
@app.route('/api/daily_bonus', methods=['POST'])
def claim_daily_bonus():
    try:
        user_id = request.json.get('user_id')
        player = db.get_player_data(user_id)
        
        if not player:
            return jsonify({"success": False, "error": "Player not found"})
        
        today = datetime.now().date().isoformat()
        last_login = datetime.fromisoformat(player["last_login"].replace('Z', '+00:00')).date()
        current_date = datetime.now().date()
        
        if last_login < current_date:
            player["stats"]["daily_bonus_claimed"] = False
        
        if player["stats"]["daily_bonus_claimed"]:
            return jsonify({"success": False, "error": "Daily bonus already claimed"})
        
        streak = player["stats"]["login_streak"]
        bonus_amount = min(50, 5 * streak)
        
        player["balance"] += bonus_amount
        player["stats"]["daily_bonus_claimed"] = True
        player["stats"]["login_streak"] = streak + 1 if last_login == current_date - timedelta(days=1) else 1
        player["last_login"] = datetime.now().isoformat()
        
        db.save_player(user_id, player)
        
        return jsonify({
            "success": True,
            "bonus": bonus_amount,
            "streak": player["stats"]["login_streak"],
            "message": f"Daily bonus claimed! +${bonus_amount}"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ОБНОВЛЕННЫЙ ТОРГОВЫЙ ЭНДПОИНТ
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
            
        player = db.get_player_data(user_id)
        if not player:
            return jsonify({"error": "Player not found"}), 404
            
        if symbol not in CRYPTOS:
            return jsonify({"error": "Invalid symbol"}), 400
        
        current_price = player["current_prices"][symbol]
        
        if price_type == 'market':
            execution_price = current_price
            total_cost = amount * execution_price
            fee = calculate_trading_fee(amount, execution_price, 'market')
            
            if order_type == 'buy':
                if player["balance"] < total_cost + fee:
                    return jsonify({
                        "success": False,
                        "error": f"Недостаточно средств. Нужно: ${total_cost + fee:.2f} (включая комиссию ${fee:.2f})"
                    })
                
                player["balance"] -= total_cost + fee
                player["portfolio"][symbol] += amount
                
            else:
                if player["portfolio"][symbol] < amount:
                    return jsonify({
                        "success": False,
                        "error": f"Недостаточно {symbol} для продажи"
                    })
                
                player["balance"] += total_cost - fee
                player["portfolio"][symbol] -= amount
            
            order = {
                "id": len(player["orders"]) + 1,
                "symbol": symbol,
                "type": order_type,
                "amount": amount,
                "price": execution_price,
                "total": total_cost,
                "fee": fee,
                "status": "filled",
                "timestamp": datetime.now().isoformat()
            }
            player["orders"].append(order)
            player["stats"]["total_trades"] += 1
            
            db.save_player(user_id, player)
            
            return jsonify({
                "success": True,
                "message": f"{order_type.upper()} {amount} {symbol} @ ${execution_price:.2f} (комиссия: ${fee:.2f})",
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
                "fee": calculate_trading_fee(amount, limit_price, 'limit'),
                "status": "pending",
                "timestamp": datetime.now().isoformat()
            }
            player["orders"].append(order)
            
            db.save_player(user_id, player)
            
            return jsonify({
                "success": True,
                "message": f"Limit order placed: {order_type} {amount} {symbol} @ ${limit_price:.2f}",
                "order": order,
                "player": player
            })
        
    except Exception as e:
        print(f"Error in place_order: {str(e)}")
        return jsonify({"error": str(e)}), 500

# P2P ЭНДПОИНТЫ
@app.route('/api/p2p/create_order', methods=['POST'])
def create_p2p_order():
    try:
        data = request.json
        user_id = data.get('user_id')
        symbol = data.get('symbol')
        amount = float(data.get('amount', 0))
        price = float(data.get('price', 0))
        order_type = data.get('type')
        
        if not all([user_id, symbol, amount, price, order_type]):
            return jsonify({"success": False, "error": "Missing parameters"}), 400
        
        if symbol not in CRYPTOS:
            return jsonify({"success": False, "error": "Invalid symbol"}), 400
        
        if amount <= 0 or price <= 0:
            return jsonify({"success": False, "error": "Invalid amount or price"}), 400
        
        if order_type not in ['buy', 'sell']:
            return jsonify({"success": False, "error": "Invalid order type"}), 400
        
        player_data = db.get_player_data(user_id)
        if not player_data:
            return jsonify({"success": False, "error": "Player not found"}), 404
        
        if order_type == 'sell':
            if player_data['portfolio'].get(symbol, 0) < amount:
                return jsonify({"success": False, "error": f"Not enough {symbol} to sell"})
        else:
            total_cost = amount * price
            if player_data['balance'] < total_cost:
                return jsonify({"success": False, "error": "Not enough balance"})
        
        username = player_data.get('username', 'Trader')
        order = p2p_manager.create_order(user_id, symbol, amount, price, order_type, username)
        
        return jsonify({
            "success": True,
            "message": f"P2P {order_type} order created successfully",
            "order": order
        })
        
    except Exception as e:
        print(f"Error in create_p2p_order: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/p2p/orders', methods=['GET'])
def get_p2p_orders():
    try:
        symbol = request.args.get('symbol')
        orders = p2p_manager.get_active_orders(symbol)
        
        return jsonify({
            "success": True,
            "orders": orders,
            "total": len(orders)
        })
        
    except Exception as e:
        print(f"Error in get_p2p_orders: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/p2p/my_orders', methods=['GET'])
def get_my_p2p_orders():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "User ID required"}), 400
        
        orders = p2p_manager.get_user_orders(user_id)
        
        return jsonify({
            "success": True,
            "orders": orders,
            "total": len(orders)
        })
        
    except Exception as e:
        print(f"Error in get_my_p2p_orders: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/p2p/execute_trade', methods=['POST'])
def execute_p2p_trade():
    try:
        data = request.json
        order_id = data.get('order_id')
        buyer_id = data.get('buyer_id')
        
        if not order_id or not buyer_id:
            return jsonify({"success": False, "error": "Missing parameters"}), 400
        
        success, message = p2p_manager.execute_trade(order_id, buyer_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": message
            })
        else:
            return jsonify({
                "success": False,
                "error": message
            })
        
    except Exception as e:
        print(f"Error in execute_p2p_trade: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/p2p/cancel_order', methods=['POST'])
def cancel_p2p_order():
    try:
        data = request.json
        order_id = data.get('order_id')
        user_id = data.get('user_id')
        
        if not order_id or not user_id:
            return jsonify({"success": False, "error": "Missing parameters"}), 400
        
        if p2p_manager.cancel_order(order_id, user_id):
            return jsonify({
                "success": True,
                "message": "Order cancelled successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to cancel order"
            })
        
    except Exception as e:
        print(f"Error in cancel_p2p_order: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

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

@app.route('/api/admin/stats', methods=['POST'])
@require_admin_auth
def admin_stats_route():
    players = db.get_all_players()
    total_players = len(players)
    total_balance = sum(player['balance'] for player in players.values())
    total_portfolio = sum(player['portfolio_value'] for player in players.values())
    total_wealth = total_balance + total_portfolio
    
    crypto_stats = {}
    for symbol in CRYPTOS.keys():
        total_owned = sum(player.get('portfolio', {}).get(symbol, 0) for player in players.values())
        crypto_stats[symbol] = {
            'total_owned': total_owned,
            'players_owning': sum(1 for player in players.values() if player.get('portfolio', {}).get(symbol, 0) > 0)
        }
    
    top_players = sorted(
        [(user_id, player) for user_id, player in players.items()],
        key=lambda x: x[1].get('total_value', 0),
        reverse=True
    )[:10]
    
    stats = {
        "total_players": total_players,
        "total_balance": total_balance,
        "total_portfolio_value": total_portfolio,
        "total_wealth": total_wealth,
        "average_balance": total_balance / total_players if total_players > 0 else 0,
        "crypto_stats": crypto_stats,
        "top_players": [
            {
                "user_id": user_id,
                "username": player.get('username', user_id),
                "total_value": player.get('total_value', 0),
                "balance": player.get('balance', 0)
            }
            for user_id, player in top_players
        ],
        "last_updated": datetime.now().isoformat()
    }
    
    return jsonify({
        "success": True,
        "stats": stats
    })

@app.route('/api/admin/players', methods=['POST'])
@require_admin_auth
def admin_players_route():
    players = db.get_all_players()
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
            "portfolio": player.get('portfolio', {}),
            "mining_level": player.get('mining', {}).get('equipment_level', 1),
            "total_trades": player.get('stats', {}).get('total_trades', 0)
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
    
    player = db.get_player_data(user_id)
    if not player:
        return jsonify({"success": False, "error": "Player not found"})
    
    if action == "reset":
        new_data = create_new_player_data()
        db.save_player(user_id, new_data)
        return jsonify({"success": True, "message": f"Player {user_id} reset successfully"})
    
    elif action == "add_balance":
        amount = float(request.json.get('amount', 0))
        player["balance"] += amount
        player["total_value"] = player["balance"] + player["portfolio_value"]
        db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Added ${amount} to {user_id}"})
    
    elif action == "set_balance":
        amount = float(request.json.get('amount', 0))
        player["balance"] = amount
        player["total_value"] = player["balance"] + player["portfolio_value"]
        db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Set balance to ${amount} for {user_id}"})
    
    elif action == "get_info":
        return jsonify({
            "success": True,
            "player": player
        })
    
    else:
        return jsonify({"success": False, "error": "Unknown action"})

@app.route('/api/admin/player/<user_id>/portfolio', methods=['POST'])
@require_admin_auth
def admin_player_portfolio_route(user_id):
    action = request.json.get('action')
    symbol = request.json.get('symbol')
    amount = float(request.json.get('amount', 0))
    
    player = db.get_player_data(user_id)
    if not player:
        return jsonify({"success": False, "error": "Player not found"})
    
    if symbol not in CRYPTOS:
        return jsonify({"success": False, "error": "Invalid symbol"})
    
    if action == "add":
        player["portfolio"][symbol] = player["portfolio"].get(symbol, 0) + amount
        db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Added {amount} {symbol} to {user_id}"})
    
    elif action == "set":
        player["portfolio"][symbol] = amount
        db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Set {symbol} to {amount} for {user_id}"})
    
    elif action == "remove":
        current_amount = player["portfolio"].get(symbol, 0)
        if amount > current_amount:
            return jsonify({"success": False, "error": f"Not enough {symbol} to remove"})
        player["portfolio"][symbol] = current_amount - amount
        db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Removed {amount} {symbol} from {user_id}"})
    
    else:
        return jsonify({"success": False, "error": "Unknown action"})

@app.route('/api/admin/player/<user_id>/balance', methods=['POST'])
@require_admin_auth
def admin_player_balance_route(user_id):
    action = request.json.get('action')
    amount = float(request.json.get('amount', 0))
    
    player = db.get_player_data(user_id)
    if not player:
        return jsonify({"success": False, "error": "Player not found"})
    
    if action == "add":
        player["balance"] += amount
        player["total_value"] = player["balance"] + player["portfolio_value"]
        db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Added ${amount} to {user_id}"})
    
    elif action == "set":
        player["balance"] = amount
        player["total_value"] = player["balance"] + player["portfolio_value"]
        db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Set balance to ${amount} for {user_id}"})
    
    elif action == "multiply":
        player["balance"] *= amount
        player["total_value"] = player["balance"] + player["portfolio_value"]
        db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Multiplied balance by {amount}x for {user_id}"})
    
    else:
        return jsonify({"success": False, "error": "Unknown action"})

@app.route('/api/admin/player/<user_id>/prices', methods=['POST'])
@require_admin_auth
def admin_player_prices_route(user_id):
    action = request.json.get('action')
    symbol = request.json.get('symbol')
    price = float(request.json.get('price', 0))
    multiplier = float(request.json.get('multiplier', 1))
    
    player = db.get_player_data(user_id)
    if not player:
        return jsonify({"success": False, "error": "Player not found"})
    
    if symbol and symbol not in CRYPTOS:
        return jsonify({"success": False, "error": "Invalid symbol"})
    
    if action == "set_price":
        if not symbol:
            return jsonify({"success": False, "error": "Symbol required"})
        player["current_prices"][symbol] = price
        db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Set {symbol} price to ${price} for {user_id}"})
    
    elif action == "multiply_prices":
        if symbol:
            player["current_prices"][symbol] *= multiplier
            db.save_player(user_id, player)
            return jsonify({"success": True, "message": f"Multiplied {symbol} price by {multiplier}x for {user_id}"})
        else:
            for crypto_symbol in CRYPTOS.keys():
                player["current_prices"][crypto_symbol] *= multiplier
            db.save_player(user_id, player)
            return jsonify({"success": True, "message": f"Multiplied all prices by {multiplier}x for {user_id}"})
    
    elif action == "reset_prices":
        for crypto_symbol, crypto_data in CRYPTOS.items():
            base_price = crypto_data["base_price"]
            player["current_prices"][crypto_symbol] = base_price * random.uniform(0.9, 1.1)
        db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Reset all prices to base values for {user_id}"})
    
    else:
        return jsonify({"success": False, "error": "Unknown action"})

@app.route('/api/admin/bulk_actions', methods=['POST'])
@require_admin_auth
def admin_bulk_actions_route():
    action = request.json.get('action')
    amount = float(request.json.get('amount', 0))
    multiplier = float(request.json.get('multiplier', 1))
    
    players = db.get_all_players()
    
    if action == "add_balance_all":
        for user_id, player in players.items():
            player["balance"] += amount
            player["total_value"] = player["balance"] + player["portfolio_value"]
            db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Added ${amount} to all {len(players)} players"})
    
    elif action == "multiply_balance_all":
        for user_id, player in players.items():
            player["balance"] *= multiplier
            player["total_value"] = player["balance"] + player["portfolio_value"]
            db.save_player(user_id, player)
        return jsonify({"success": True, "message": f"Multiplied balance by {multiplier}x for all {len(players)} players"})
    
    elif action == "reset_all_players":
        for user_id in players.keys():
            new_data = create_new_player_data()
            db.save_player(user_id, new_data)
        return jsonify({"success": True, "message": f"Reset all {len(players)} players"})
    
    else:
        return jsonify({"success": False, "error": "Unknown action"})

@app.route('/api/admin/system', methods=['POST'])
@require_admin_auth
def admin_system_route():
    action = request.json.get('action')
    
    if action == "save":
        db.save_data()
        return jsonify({"success": True, "message": "Data saved successfully"})
    
    elif action == "reload":
        db.__init__()
        return jsonify({"success": True, "message": "Data reloaded successfully"})
    
    elif action == "update_prices_all":
        players = db.get_all_players()
        for user_id, player in players.items():
            for symbol, crypto in CRYPTOS.items():
                current_price = player["current_prices"][symbol]
                new_price = generate_realistic_price(current_price, crypto["volatility"] * 2, symbol)
                
                player["current_prices"][symbol] = new_price
                player["price_history"][symbol].append(new_price)
                if len(player["price_history"][symbol]) > 50:
                    player["price_history"][symbol].pop(0)
                
                player["order_books"][symbol] = update_order_book(symbol, new_price)
            
            db.save_player(user_id, player)
        
        return jsonify({"success": True, "message": "Prices updated for all players"})
    
    else:
        return jsonify({"success": False, "error": "Unknown action"})

@app.route('/api/admin/system/advanced', methods=['POST'])
@require_admin_auth
def admin_system_advanced_route():
    action = request.json.get('action')
    
    if action == "clear_p2p_orders":
        p2p_manager.orders = []
        p2p_manager.save_orders()
        return jsonify({"success": True, "message": "Cleared all P2P orders"})
    
    elif action == "export_data":
        players = db.get_all_players()
        
        export_data = {
            "players": players,
            "p2p_orders": p2p_manager.orders,
            "exported_at": datetime.now().isoformat(),
            "total_players": len(players),
            "total_p2p_orders": len(p2p_manager.orders),
            "system_info": {
                "cryptocurrencies": len(CRYPTOS),
                "admin_user_id": ADMIN_USER_ID,
                "server_time": datetime.now().isoformat()
            }
        }
        return jsonify({"success": True, "data": export_data})
    
    elif action == "get_detailed_stats":
        players = db.get_all_players()
        total_players = len(players)
        
        if total_players == 0:
            return jsonify({"success": True, "stats": {}})
        
        total_balance = sum(player['balance'] for player in players.values())
        total_portfolio = sum(player['portfolio_value'] for player in players.values())
        total_wealth = total_balance + total_portfolio
        
        wealth_values = [player['total_value'] for player in players.values()]
        wealth_values.sort(reverse=True)
        
        top_players = sorted(
            [(user_id, player) for user_id, player in players.items()],
            key=lambda x: x[1].get('total_value', 0),
            reverse=True
        )[:10]
        
        asset_stats = {}
        for symbol in CRYPTOS.keys():
            total_owned = sum(player.get('portfolio', {}).get(symbol, 0) for player in players.values())
            players_owning = sum(1 for player in players.values() if player.get('portfolio', {}).get(symbol, 0) > 0)
            total_value = sum(player.get('portfolio', {}).get(symbol, 0) * player['current_prices'][symbol] for player in players.values())
            
            asset_stats[symbol] = {
                'total_owned': total_owned,
                'players_owning': players_owning,
                'percentage_owners': (players_owning / total_players) * 100,
                'total_value': total_value
            }
        
        detailed_stats = {
            "basic": {
                "total_players": total_players,
                "total_balance": total_balance,
                "total_portfolio_value": total_portfolio,
                "total_wealth": total_wealth,
                "average_balance": total_balance / total_players,
                "average_portfolio": total_portfolio / total_players,
                "average_wealth": total_wealth / total_players
            },
            "wealth_distribution": {
                "richest_player": wealth_values[0] if wealth_values else 0,
                "poorest_player": wealth_values[-1] if wealth_values else 0,
                "median_wealth": wealth_values[len(wealth_values)//2] if wealth_values else 0,
                "top_10_percent_wealth": sum(wealth_values[:max(1, len(wealth_values)//10)]) if wealth_values else 0
            },
            "assets": asset_stats,
            "top_players": [
                {
                    "user_id": user_id,
                    "username": player.get('username', user_id),
                    "total_value": player.get('total_value', 0),
                    "balance": player.get('balance', 0),
                    "portfolio_value": player.get('portfolio_value', 0),
                    "assets_count": len([v for v in player.get('portfolio', {}).values() if v > 0])
                }
                for user_id, player in top_players
            ],
            "p2p_stats": {
                "total_orders": len(p2p_manager.orders),
                "active_orders": len([o for o in p2p_manager.orders if o['status'] == 'active']),
                "filled_orders": len([o for o in p2p_manager.orders if o['status'] == 'filled']),
                "cancelled_orders": len([o for o in p2p_manager.orders if o['status'] == 'cancelled'])
            },
            "mining_stats": {
                "total_mining_rewards": sum(player.get('stats', {}).get('total_mining_rewards', 0) for player in players.values()),
                "average_mining_level": sum(player.get('mining', {}).get('equipment_level', 1) for player in players.values()) / total_players,
                "players_mining": sum(1 for player in players.values() if sum(player.get('mining', {}).get('total_mined', {}).values()) > 0)
            }
        }
        
        return jsonify({"success": True, "stats": detailed_stats})
    
    elif action == "generate_test_data":
        test_players_count = 10
        created_count = 0
        
        for i in range(test_players_count):
            user_id = f"test_player_{i+1}"
            if user_id not in db.get_all_players():
                player_data = create_new_player_data()
                for symbol in CRYPTOS:
                    if random.random() > 0.7:
                        player_data["portfolio"][symbol] = round(random.uniform(0.1, 5.0), 4)
                player_data["username"] = f"TestPlayer{i+1}"
                db.save_player(user_id, player_data)
                created_count += 1
        
        return jsonify({"success": True, "message": f"Created {created_count} test players"})
    
    elif action == "fix_player_data":
        players = db.get_all_players()
        fixed_count = 0
        
        for user_id, player in players.items():
            needs_fix = False
            
            if "portfolio" not in player:
                player["portfolio"] = {symbol: 0 for symbol in CRYPTOS}
                needs_fix = True
            
            if "current_prices" not in player:
                player["current_prices"] = {}
                for symbol, crypto in CRYPTOS.items():
                    player["current_prices"][symbol] = crypto["base_price"] * random.uniform(0.9, 1.1)
                needs_fix = True
            
            if "portfolio_value" not in player:
                player["portfolio_value"] = 0
                needs_fix = True
            
            if "total_value" not in player:
                player["total_value"] = player.get("balance", 500) + player["portfolio_value"]
                needs_fix = True
            
            if "mining" not in player:
                player["mining"] = {
                    "energy": MINING_CONFIG["max_energy"],
                    "last_mining_time": datetime.now().isoformat(),
                    "equipment_level": 1,
                    "total_mined": {symbol: 0 for symbol in CRYPTOS},
                    "mining_power": 1.0
                }
                needs_fix = True
            
            if "stats" not in player:
                player["stats"] = {
                    "total_trades": 0,
                    "total_profit": 0,
                    "daily_bonus_claimed": False,
                    "login_streak": 1,
                    "total_mining_rewards": 0
                }
                needs_fix = True
            
            if needs_fix:
                db.save_player(user_id, player)
                fixed_count += 1
        
        return jsonify({"success": True, "message": f"Fixed data for {fixed_count} players"})
    
    elif action == "get_system_health":
        players = db.get_all_players()
        total_players = len(players)
        
        corrupted_players = 0
        for user_id, player in players.items():
            if not all(key in player for key in ["balance", "portfolio", "total_value"]):
                corrupted_players += 1
        
        health_status = {
            "total_players": total_players,
            "corrupted_players": corrupted_players,
            "p2p_orders_total": len(p2p_manager.orders),
            "p2p_orders_active": len([o for o in p2p_manager.orders if o['status'] == 'active']),
            "database_size": sum(len(str(player)) for player in players.values()),
            "system_uptime": int(time.time() - app_start_time),
            "health_score": 100 - (corrupted_players / max(1, total_players)) * 100
        }
        
        return jsonify({"success": True, "health": health_status})
    
    elif action == "cleanup_old_data":
        cutoff_date = datetime.now() - timedelta(days=30)
        removed_count = 0
        
        players = db.get_all_players()
        for user_id, player in players.items():
            last_login = player.get('last_login')
            if last_login:
                try:
                    login_date = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                    if login_date < cutoff_date:
                        del db.players[user_id]
                        removed_count += 1
                except:
                    pass
        
        if removed_count > 0:
            db.save_data()
        
        return jsonify({"success": True, "message": f"Removed {removed_count} inactive players"})
    
    elif action == "backup_database":
        backup_data = {
            "players": db.get_all_players(),
            "p2p_orders": p2p_manager.orders,
            "backup_created": datetime.now().isoformat(),
            "backup_version": "1.0"
        }
        
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            return jsonify({"success": True, "message": f"Backup created: {backup_filename}", "filename": backup_filename})
        except Exception as e:
            return jsonify({"success": False, "error": f"Backup failed: {str(e)}"})
    
    elif action == "simulate_market_crash":
        players = db.get_all_players()
        affected_players = 0
        
        for user_id, player in players.items():
            for symbol in CRYPTOS:
                player["current_prices"][symbol] *= 0.5
            
            portfolio_value = sum(
                player["portfolio"][symbol] * player["current_prices"][symbol] 
                for symbol in CRYPTOS
            )
            player["portfolio_value"] = round(portfolio_value, 2)
            player["total_value"] = round(player["balance"] + portfolio_value, 2)
            
            db.save_player(user_id, player)
            affected_players += 1
        
        return jsonify({"success": True, "message": f"Simulated market crash for {affected_players} players"})
    
    elif action == "simulate_market_boom":
        players = db.get_all_players()
        affected_players = 0
        
        for user_id, player in players.items():
            for symbol in CRYPTOS:
                player["current_prices"][symbol] *= 2.0
            
            portfolio_value = sum(
                player["portfolio"][symbol] * player["current_prices"][symbol] 
                for symbol in CRYPTOS
            )
            player["portfolio_value"] = round(portfolio_value, 2)
            player["total_value"] = round(player["balance"] + portfolio_value, 2)
            
            db.save_player(user_id, player)
            affected_players += 1
        
        return jsonify({"success": True, "message": f"Simulated market boom for {affected_players} players"})
    
    elif action == "reset_economy":
        players = db.get_all_players()
        reset_count = 0
        
        for user_id in players.keys():
            new_data = create_new_player_data()
            db.save_player(user_id, new_data)
            reset_count += 1
        
        p2p_manager.orders = []
        p2p_manager.save_orders()
        
        return jsonify({"success": True, "message": f"Complete economy reset for {reset_count} players"})
    
    elif action == "adjust_trading_fees":
        global TRADING_FEE
        TRADING_FEE = float(request.json.get('fee', 0.0025))
        return jsonify({"success": True, "message": f"Trading fee set to {TRADING_FEE*100}%"})
    
    elif action == "adjust_mining_difficulty":
        symbol = request.json.get('symbol')
        new_difficulty = float(request.json.get('difficulty'))
        
        if symbol and symbol in CRYPTOS:
            CRYPTOS[symbol]["mining_difficulty"] = new_difficulty
            return jsonify({"success": True, "message": f"Mining difficulty for {symbol} set to {new_difficulty}"})
        else:
            for crypto in CRYPTOS.values():
                crypto["mining_difficulty"] = new_difficulty
            return jsonify({"success": True, "message": f"All mining difficulties set to {new_difficulty}"})
    
    elif action == "get_economy_stats":
        players = db.get_all_players()
        
        economy_stats = {
            "total_players": len(players),
            "total_wealth": sum(p["total_value"] for p in players.values()),
            "average_balance": sum(p["balance"] for p in players.values()) / len(players),
            "mining_activity": sum(sum(p["mining"]["total_mined"].values()) for p in players.values()),
            "total_trades": sum(p["stats"]["total_trades"] for p in players.values()),
            "wealth_distribution": {
                "top_10%": sorted([p["total_value"] for p in players.values()], reverse=True)[:max(1, len(players)//10)],
                "bottom_10%": sorted([p["total_value"] for p in players.values()])[:max(1, len(players)//10)]
            }
        }
        
        return jsonify({"success": True, "economy_stats": economy_stats})
    
    else:
        return jsonify({"success": False, "error": "Unknown action"})

# ОСНОВНЫЕ ЭНДПОИНТЫ ИГРЫ
@app.route('/api/player/<user_id>', methods=['GET'])
def get_player_data(user_id):
    try:
        player_data = db.get_player_data(user_id)
        
        if not player_data:
            player_data = create_new_player_data()
            db.save_player(user_id, player_data)
            print(f"✅ Created new player: {user_id}")
        else:
            print(f"✅ Loaded player: {user_id}")
        
        player_data["last_login"] = datetime.now().isoformat()
        
        for symbol, crypto in CRYPTOS.items():
            current_price = player_data["current_prices"][symbol]
            new_price = generate_realistic_price(current_price, crypto["volatility"], symbol)
            
            player_data["current_prices"][symbol] = new_price
            player_data["price_history"][symbol].append(new_price)
            if len(player_data["price_history"][symbol]) > 50:
                player_data["price_history"][symbol].pop(0)
            
            player_data["order_books"][symbol] = update_order_book(symbol, new_price)
        
        portfolio_value = sum(
            player_data["portfolio"][symbol] * player_data["current_prices"][symbol] 
            for symbol in CRYPTOS
        )
        player_data["portfolio_value"] = round(portfolio_value, 2)
        player_data["total_value"] = round(player_data["balance"] + portfolio_value, 2)
        
        db.save_player(user_id, player_data)
        
        return jsonify(player_data)
        
    except Exception as e:
        print(f"Error in get_player_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/update_prices', methods=['POST'])
def update_prices():
    try:
        user_id = request.json.get('user_id')
        
        player = db.get_player_data(user_id)
        if not player:
            return jsonify({"error": "Player not found"}), 404
            
        for symbol, crypto in CRYPTOS.items():
            current_price = player["current_prices"][symbol]
            new_price = generate_realistic_price(current_price, crypto["volatility"] * 2, symbol)
            
            player["current_prices"][symbol] = new_price
            player["price_history"][symbol].append(new_price)
            if len(player["price_history"][symbol]) > 50:
                player["price_history"][symbol].pop(0)
            
            player["order_books"][symbol] = update_order_book(symbol, new_price)
        
        db.save_player(user_id, player)
        
        return jsonify({
            "success": True,
            "message": "Prices updated",
            "player": player
        })
        
    except Exception as e:
        print(f"Error in update_prices: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/check_admin', methods=['POST'])
def check_admin():
    try:
        user_id = request.json.get('user_id')
        is_admin = user_id == ADMIN_USER_ID
        
        return jsonify({
            "success": True,
            "is_admin": is_admin
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

app_start_time = time.time()

if __name__ == '__main__':
    print(f"🚀 Starting Crypto Exchange Pro on port {port}")
    print(f"📊 Current players: {len(db.get_all_players())}")
    print(f"🔐 Admin panel: /admin")
    print(f"🤝 P2P Market: /p2p")
    print(f"⛏️ Mining: /mining")
    print(f"🔒 Admin user ID: {ADMIN_USER_ID}")
    app.run(host='0.0.0.0', port=port, debug=False)
