import json
import os
from datetime import datetime

class Database:
    def __init__(self):
        self.data_file = "players_data.json"
        self.players = self.load_data()
    
    def load_data(self):
        """Загрузка данных из файла"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"✅ Loaded {len(data)} players from file")
                    return data
        except Exception as e:
            print(f"❌ Error loading data: {e}")
        return {}
    
    def save_data(self):
        """Сохранение данных в файл"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.players, f, indent=2, ensure_ascii=False)
            print(f"💾 Data saved: {len(self.players)} players")
        except Exception as e:
            print(f"❌ Error saving data: {e}")
    
    def get_player(self, user_id):
        """Получить игрока по ID"""
        return self.players.get(user_id)
    
    def create_player(self, user_id, player_data):
        """Создать нового игрока"""
        self.players[user_id] = player_data
        self.save_data()
        return player_data
    
    def update_player(self, user_id, player_data):
        """Обновить данные игрока"""
        if user_id in self.players:
            # Сохраняем некоторые старые данные если они нужны
            old_player = self.players[user_id]
            player_data.setdefault('created_at', old_player.get('created_at', datetime.now().isoformat()))
            player_data.setdefault('username', old_player.get('username', 'Trader'))
            
            self.players[user_id] = player_data
            self.save_data()
        return player_data
    
    def save_player(self, user_id, player_data):
        """Сохранить или обновить игрока"""
        if user_id in self.players:
            return self.update_player(user_id, player_data)
        else:
            return self.create_player(user_id, player_data)
    
    def get_all_players(self):
        """Получить всех игроков"""
        return self.players
    
    def get_player_data(self, user_id):
        """Получить данные игрока в формате словаря"""
        return self.players.get(user_id)

# Глобальный экземпляр базы данных
db = Database()
