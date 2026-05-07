"""Глобальный экземпляр collector для доступа из любых модулей"""
from server_stats.stat_collector import StatsCollector

# Глобальная переменная
collector = None

def set_collector(bot):
    """Установить глобальный collector"""
    global collector
    collector = StatsCollector(bot)
    return collector

def get_collector():
    """Получить глобальный collector"""
    return collector