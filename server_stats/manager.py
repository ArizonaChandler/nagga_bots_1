"""Менеджер для работы со статистикой сервера"""
from core.database import db
from core.config import CONFIG
from datetime import datetime, date
import pytz

MSK_TZ = pytz.timezone('Europe/Moscow')


class StatsManager:
    """Менеджер статистики"""
    
    def get_settings(self):
        """Получить все настройки из CONFIG"""
        return {
            'stats_channel': CONFIG.get('stats_channel'),
            'stats_backup_enabled': CONFIG.get('stats_backup_enabled', True),
        }
    
    def save_setting(self, key: str, value: str, updated_by: str = None):
        """Сохранить настройку"""
        db.set_stats_setting(key, value, updated_by)
        CONFIG[key] = value
    
    def save_daily_stats(self, stats_data: dict):
        """Сохранить дневную статистику в БД"""
        db.save_daily_stats(stats_data)
    
    def get_today_stats(self):
        """Получить статистику за сегодня из БД"""
        today = datetime.now(MSK_TZ).date().isoformat()
        return db.get_stats_for_date(today)
    
    def get_stats_for_date(self, date_str: str):
        """Получить статистику за конкретную дату"""
        return db.get_stats_for_date(date_str)
    
    def increment_stat(self, stat_name: str):
        """Увеличить значение статистики на 1"""
        today_stats = self.get_today_stats()
        
        if not today_stats:
            today_stats = {
                'new_members': 0,
                'new_applications': 0,
                'left_members': 0,
                'accepted_applications': 0,
                'max_voice_online': 0,
                'capt_registrations': 0,
                'date': datetime.now(MSK_TZ).date().isoformat()
            }
        
        if stat_name in today_stats:
            today_stats[stat_name] += 1
        
        self.save_daily_stats(today_stats)
        return today_stats[stat_name]
    
    def update_max_voice(self, current_count: int):
        """Обновить максимальное количество в войсе"""
        today_stats = self.get_today_stats()
        
        if not today_stats:
            today_stats = {
                'new_members': 0,
                'new_applications': 0,
                'left_members': 0,
                'accepted_applications': 0,
                'max_voice_online': 0,
                'capt_registrations': 0,
                'date': datetime.now(MSK_TZ).date().isoformat()
            }
        
        if current_count > today_stats.get('max_voice_online', 0):
            today_stats['max_voice_online'] = current_count
            self.save_daily_stats(today_stats)

stats_manager = StatsManager()