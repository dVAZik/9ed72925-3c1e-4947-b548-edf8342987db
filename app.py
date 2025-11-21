from flask import Flask, request, jsonify, render_template
import json
import os
from datetime import datetime

app = Flask(__name__)

# Для Render нужно использовать их порт
port = int(os.environ.get("PORT", 5000))

DATA_FILE = "game_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"players": {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Главная страница Web App
@app.route('/')
def index():
    return render_template('index.html')

# API для игры
@app.route('/api/player/<user_id>', methods=['GET'])
def get_player_data(user_id):
    data = load_data()
    player = data["players"].get(user_id)
    
    if not player:
        # Создаем нового игрока
        player = {
            "credits": 100,
            "ship_level": 1,
            "resources": {"iron": 0, "gold": 0, "crystals": 0},
            "total_earned": 0,
            "created_at": datetime.now().isoformat()
        }
        data["players"][user_id] = player
        save_data(data)
    
    return jsonify(player)

@app.route('/api/mine', methods=['POST'])
def mine_resources():
    try:
        user_id = request.json.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
            
        data = load_data()
        
        if user_id not in data["players"]:
            return jsonify({"error": "Player not found"}), 404
        
        player = data["players"][user_id]
        
        import random
        resources = {
            "iron": random.randint(5, 15),
            "gold": random.randint(1, 5),
            "crystals": random.randint(0, 2)
        }
        
        for resource, amount in resources.items():
            player["resources"][resource] += amount
        
        player["last_action"] = datetime.now().isoformat()
        save_data(data)
        
        return jsonify({
            "success": True,
            "resources": resources,
            "player": player
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sell', methods=['POST'])
def sell_resources():
    try:
        user_id = request.json.get('user_id')
        resource_type = request.json.get('resource_type')
        
        if not user_id or not resource_type:
            return jsonify({"error": "Missing parameters"}), 400
            
        data = load_data()
        
        if user_id not in data["players"]:
            return jsonify({"error": "Player not found"}), 404
            
        player = data["players"][user_id]
        
        prices = {"iron": 2, "gold": 5, "crystals": 15}
        
        if resource_type not in prices:
            return jsonify({"error": "Invalid resource type"}), 400
        
        if player["resources"][resource_type] > 0:
            amount = player["resources"][resource_type]
            income = amount * prices[resource_type]
            
            player["credits"] += income
            player["resources"][resource_type] = 0
            player["total_earned"] += income
            
            save_data(data)
            
            return jsonify({
                "success": True,
                "sold": amount,
                "income": income,
                "player": player
            })
        
        return jsonify({"success": False, "error": "No resources to sell"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=False)