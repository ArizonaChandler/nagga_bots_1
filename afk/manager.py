"""Менеджер для работы с системой AFK"""
from core.database import db
from core.config import CONFIG
from datetime import datetime, timedelta
import pytz

MSK_TZ = pytz.timezone('Europe/Moscow')

class AFKManager:
    """Менеджер AFK (обертка над database.py)"""
    
    def get_settings(self):
        """Получить все настройки из CONFIG"""
        return {
            'afk_channel': CONFIG.get('afk_channel'),
            'afk_max_hours': CONFIG.get('afk_max_hours', 24),
            'afk_settings_channel': CONFIG.get('afk_settings_channel'),
        }
    
    def save_setting(self, key: str, value: str, updated_by: str = None):
        """Сохранить настройку"""
        db.set_afk_setting(key, value, updated_by)
        CONFIG[key] = value
    
    def add_afk_user(self, user_id: str, user_name: str, reason: str, hours: int) -> tuple:
        """Добавить пользователя в AFK"""
        return db.add_afk_user(user_id, user_name, reason, hours)
    
    def remove_afk_user(self, user_id: str) -> bool:
        """Удалить пользователя из AFK"""
        return db.remove_afk_user(user_id)
    
    def get_all_afk_users(self):
        """Получить всех AFK пользователей"""
        return db.get_all_afk_users()
    
    def get_afk_user(self, user_id: str):
        """Получить AFK пользователя по ID"""
        return db.get_afk_user(user_id)
    
    def check_expired(self):
        """Проверить и вернуть просроченных AFK пользователей"""
        return db.check_expired_afk_users()

afk_manager = AFKManager()