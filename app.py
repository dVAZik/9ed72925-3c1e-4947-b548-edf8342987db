from flask import Flask, request, jsonify, render_template
import json
import os
from datetime import datetime
import random

app = Flask(__name__)

# Для Render нужно использовать их порт
port = int(os.environ.get("PORT", 5000))

# Упрощенное хранение данных в памяти (без файлов)
game_data = {"players": {}}

# CORS headers для всех ответов
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Главная страница Web App
@app.route('/')
def index():
    return render_template('index.html')

# Health check для Render
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "cosmic-miner"})

# API для получения данных игрока
@app.route('/api/player/<user_id>', methods=['GET'])
def get_player_data(user_id):
    try:
        print(f"📥 Getting data for user: {user_id}")
        
        if user_id not in game_data["players"]:
            # Создаем нового игрока
            player_data = {
                "credits": 100,
                "ship_level": 1,
                "resources": {
                    "iron": 0,
                    "gold": 0, 
                    "crystals": 0
                },
                "total_earned": 0,
                "created_at": datetime.now().isoformat()
            }
            game_data["players"][user_id] = player_data
            print(f"✅ Created new player: {user_id}")
        
        return jsonify(game_data["players"][user_id])
    except Exception as e:
        print(f"❌ Error in get_player_data: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API для добычи ресурсов
@app.route('/api/mine', methods=['POST'])
def mine_resources():
    try:
        user_id = request.json.get('user_id')
        print(f"⛏ Mining request from user: {user_id}")
        
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
            
        if user_id not in game_data["players"]:
            return jsonify({"error": "Player not found"}), 404
        
        player = game_data["players"][user_id]
        
        # Логика добычи ресурсов
        resources_mined = {
            "iron": random.randint(5, 15),
            "gold": random.randint(1, 5),
            "crystals": random.randint(0, 2)
        }
        
        # Добавляем ресурсы игроку
        for resource, amount in resources_mined.items():
            player["resources"][resource] += amount
        
        player["last_action"] = datetime.now().isoformat()
        
        print(f"✅ Mined resources: {resources_mined}")
        
        return jsonify({
            "success": True,
            "resources": resources_mined,
            "player": player
        })
        
    except Exception as e:
        print(f"❌ Error in mine_resources: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API для продажи ресурсов
@app.route('/api/sell', methods=['POST'])
def sell_resources():
    try:
        user_id = request.json.get('user_id')
        resource_type = request.json.get('resource_type')
        
        print(f"🛒 Sell request: {user_id} wants to sell {resource_type}")
        
        if not user_id or not resource_type:
            return jsonify({"error": "Missing parameters"}), 400
            
        if user_id not in game_data["players"]:
            return jsonify({"error": "Player not found"}), 404
            
        player = game_data["players"][user_id]
        
        # Цены на ресурсы
        prices = {
            "iron": 2,
            "gold": 5, 
            "crystals": 15
        }
        
        if resource_type not in prices:
            return jsonify({"error": "Invalid resource type"}), 400
        
        # Проверяем, есть ли ресурсы для продажи
        if player["resources"][resource_type] <= 0:
            return jsonify({
                "success": False, 
                "error": f"No {resource_type} to sell"
            })
        
        # Продаем все ресурсы этого типа
        amount = player["resources"][resource_type]
        income = amount * prices[resource_type]
        
        # Обновляем данные игрока
        player["credits"] += income
        player["resources"][resource_type] = 0
        player["total_earned"] += income
        
        print(f"✅ Sold {amount} {resource_type} for {income} credits")
        
        return jsonify({
            "success": True,
            "sold": amount,
            "income": income,
            "player": player
        })
        
    except Exception as e:
        print(f"❌ Error in sell_resources: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API для улучшения корабля
@app.route('/api/upgrade', methods=['POST'])
def upgrade_ship():
    try:
        user_id = request.json.get('user_id')
        print(f"🛠 Upgrade request from: {user_id}")
        
        if user_id not in game_data["players"]:
            return jsonify({"error": "Player not found"}), 404
            
        player = game_data["players"][user_id]
        
        # Стоимость улучшения = текущий_уровень * 100
        upgrade_cost = player["ship_level"] * 100
        
        if player["credits"] < upgrade_cost:
            return jsonify({
                "success": False,
                "error": f"Not enough credits. Need {upgrade_cost}"
            })
        
        # Списываем деньги и улучшаем корабль
        player["credits"] -= upgrade_cost
        player["ship_level"] += 1
        
        print(f"✅ Ship upgraded to level {player['ship_level']}")
        
        return jsonify({
            "success": True,
            "upgrade_cost": upgrade_cost,
            "new_level": player["ship_level"],
            "player": player
        })
        
    except Exception as e:
        print(f"❌ Error in upgrade_ship: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Обработчики ошибок
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    print(f"🚀 Starting Cosmic Miner on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
