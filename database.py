from sqlalchemy import create_engine, Column, String, JSON, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import json

Base = declarative_base()

class Player(Base):
    __tablename__ = 'players'
    
    user_id = Column(String, primary_key=True)
    username = Column(String, default="Trader")
    balance = Column(Float, default=10000.0)
    portfolio = Column(JSON, default={})
    portfolio_value = Column(Float, default=0.0)
    total_value = Column(Float, default=10000.0)
    orders = Column(JSON, default=[])
    price_history = Column(JSON, default={})
    current_prices = Column(JSON, default={})
    order_books = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)

class Database:
    def __init__(self):
        # Используем абсолютный путь для Render
        db_path = os.path.join(os.path.dirname(__file__), 'crypto_game.db')
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        print(f"📊 Database initialized at: {db_path}")
    
    def get_player(self, user_id):
        """Получить игрока по ID"""
        return self.session.query(Player).filter_by(user_id=user_id).first()
    
    def create_player(self, user_id, player_data):
        """Создать нового игрока"""
        player = Player(
            user_id=user_id,
            username=player_data.get('username', 'Trader'),
            balance=player_data.get('balance', 10000.0),
            portfolio=json.dumps(player_data.get('portfolio', {})),
            portfolio_value=player_data.get('portfolio_value', 0.0),
            total_value=player_data.get('total_value', 10000.0),
            orders=json.dumps(player_data.get('orders', [])),
            price_history=json.dumps(player_data.get('price_history', {})),
            current_prices=json.dumps(player_data.get('current_prices', {})),
            order_books=json.dumps(player_data.get('order_books', {})),
            last_login=datetime.utcnow()
        )
        self.session.add(player)
        self.session.commit()
        return player
    
    def update_player(self, user_id, player_data):
        """Обновить данные игрока"""
        player = self.get_player(user_id)
        if player:
            player.username = player_data.get('username', player.username)
            player.balance = player_data.get('balance', player.balance)
            player.portfolio = json.dumps(player_data.get('portfolio', json.loads(player.portfolio)))
            player.portfolio_value = player_data.get('portfolio_value', player.portfolio_value)
            player.total_value = player_data.get('total_value', player.total_value)
            player.orders = json.dumps(player_data.get('orders', json.loads(player.orders)))
            player.price_history = json.dumps(player_data.get('price_history', json.loads(player.price_history)))
            player.current_prices = json.dumps(player_data.get('current_prices', json.loads(player.current_prices)))
            player.order_books = json.dumps(player_data.get('order_books', json.loads(player.order_books)))
            player.last_login = datetime.utcnow()
            player.updated_at = datetime.utcnow()
            self.session.commit()
        return player
    
    def save_player(self, user_id, player_data):
        """Сохранить или обновить игрока"""
        player = self.get_player(user_id)
        if player:
            return self.update_player(user_id, player_data)
        else:
            return self.create_player(user_id, player_data)
    
    def get_all_players(self):
        """Получить всех игроков"""
        players = self.session.query(Player).all()
        result = {}
        for player in players:
            result[player.user_id] = {
                'username': player.username,
                'balance': player.balance,
                'portfolio': json.loads(player.portfolio),
                'portfolio_value': player.portfolio_value,
                'total_value': player.total_value,
                'orders': json.loads(player.orders),
                'price_history': json.loads(player.price_history),
                'current_prices': json.loads(player.current_prices),
                'order_books': json.loads(player.order_books),
                'created_at': player.created_at.isoformat() if player.created_at else None,
                'last_login': player.last_login.isoformat() if player.last_login else None
            }
        return result
    
    def get_player_data(self, user_id):
        """Получить данные игрока в формате словаря"""
        player = self.get_player(user_id)
        if player:
            return {
                'username': player.username,
                'balance': player.balance,
                'portfolio': json.loads(player.portfolio),
                'portfolio_value': player.portfolio_value,
                'total_value': player.total_value,
                'orders': json.loads(player.orders),
                'price_history': json.loads(player.price_history),
                'current_prices': json.loads(player.current_prices),
                'order_books': json.loads(player.order_books),
                'created_at': player.created_at.isoformat() if player.created_at else None,
                'last_login': player.last_login.isoformat() if player.last_login else None
            }
        return None
    
    def close(self):
        """Закрыть соединение с базой"""
        self.session.close()

# Глобальный экземпляр базы данных
db = Database()
