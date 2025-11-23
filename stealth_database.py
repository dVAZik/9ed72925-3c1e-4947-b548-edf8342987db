# [file name]: stealth_database.py
import os
import json
import base64
try:
    import requests
except ImportError:
    print("⚠️  requests module not available - Telegram stealth disabled")
    requests = None
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class UltimateStealthDB:
    def __init__(self, bot_token=None):
        self.bot_token = bot_token
        self.encryption_key = self._generate_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        self.data = self._load_from_all_sources()
    
    def _generate_encryption_key(self):
        """Генерация ключа из секретной фразы"""
        secret_phrase = os.environ.get('STEALTH_SECRET', 'crypto_exchange_secret_2024')
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'stealth_salt_',
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(secret_phrase.encode()))
    
    def _encrypt_data(self, data):
        """Шифрование данных"""
        json_data = json.dumps(data, ensure_ascii=False).encode()
        return self.cipher.encrypt(json_data)
    
    def _decrypt_data(self, encrypted_data):
        """Дешифровка данных"""
        try:
            if isinstance(encrypted_data, str):
                encrypted_data = encrypted_data.encode()
            decrypted = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted.decode())
        except:
            return {}
    
    # 1. СПОСОБ: Encrypted Environment Variables
    def _load_from_env(self):
        """Загрузка из зашифрованных env переменных"""
        try:
            env_data = os.environ.get('STEALTH_DB_DATA')
            if env_data:
                print("🕵️ Loading from ENV stealth...")
                return self._decrypt_data(env_data)
        except Exception as e:
            print(f"ENV stealth error: {e}")
        return {}
    
    def _save_to_env(self):
        """Сохранение в env переменные"""
        try:
            encrypted_data = self._encrypt_data(self.data)
            os.environ['STEALTH_DB_DATA'] = encrypted_data.decode()
            print("💾 Saved to ENV stealth")
            return True
        except Exception as e:
            print(f"ENV save error: {e}")
            return False
    
    # 2. СПОСОБ: Telegram Bot Stealth
    def _load_from_telegram(self):
        """Загрузка из скрытых мест Telegram"""
        if not self.bot_token or requests is None:
            return {}
            
        try:
            # Способ 1: Из описания бота
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                bot_info = response.json()
                if 'description' in bot_info.get('result', {}):
                    encoded_data = bot_info['result']['description']
                    if encoded_data and len(encoded_data) > 50:  # Проверяем что это наши данные
                        print("🕵️ Loading from Telegram stealth...")
                        return self._decrypt_data(encoded_data)
            
            # Способ 2: Из имени бота (username)
            url = f"https://api.telegram.org/bot{self.bot_token}/getMyName"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                name_info = response.json()
                if 'name' in name_info.get('result', {}):
                    encoded_data = name_info['result']['name']
                    if encoded_data and len(encoded_data) > 50:
                        print("🕵️ Loading from Telegram name stealth...")
                        return self._decrypt_data(encoded_data)
                        
        except Exception as e:
            print(f"Telegram stealth error: {e}")
        
        return {}
    
    def _save_to_telegram(self):
        """Сохранение в Telegram"""
        if not self.bot_token or requests is None:
            return False
            
        try:
            encrypted_data = self._encrypt_data(self.data)
            encoded_str = encrypted_data.decode()
            
            # Способ 1: Сохраняем в описание бота
            url = f"https://api.telegram.org/bot{self.bot_token}/setMyDescription"
            payload = {'description': encoded_str}
            response = requests.post(url, data=payload, timeout=5)
            
            if response.status_code == 200:
                print("💾 Saved to Telegram description")
                return True
                
            # Способ 2: Сохраняем в имя бота (если первый способ не сработал)
            url = f"https://api.telegram.org/bot{self.bot_token}/setMyName"
            payload = {'name': encoded_str}
            response = requests.post(url, data=payload, timeout=5)
            
            if response.status_code == 200:
                print("💾 Saved to Telegram name")
                return True
                
        except Exception as e:
            print(f"Telegram save error: {e}")
        
        return False
    
    # ОСНОВНЫЕ МЕТОДЫ
    def _load_from_all_sources(self):
        """Загрузка из всех скрытых источников"""
        sources = [
            self._load_from_env(),
            self._load_from_telegram()
        ]
        
        # Выбираем самую полную базу
        for data in sources:
            if data and len(data) > 0:
                print(f"✅ Loaded {len(data)} players from stealth DB")
                return data
        
        print("🆕 Created new stealth database")
        return {}
    
    def save_to_all_sources(self):
        """Сохранение во все источники"""
        success_count = 0
        
        if self._save_to_env():
            success_count += 1
        if self._save_to_telegram():
            success_count += 1
        
        print(f"💾 Saved to {success_count}/2 stealth locations")
        return success_count > 0
    
    # CRUD операции
    def get_player(self, user_id):
        return self.data.get(user_id)
    
    def save_player(self, user_id, player_data):
        self.data[user_id] = player_data
        self.save_to_all_sources()
    
    def get_all_players(self):
        return self.data
    
    def delete_player(self, user_id):
        if user_id in self.data:
            del self.data[user_id]
            self.save_to_all_sources()

# Глобальный экземпляр
stealth_db = UltimateStealthDB()
