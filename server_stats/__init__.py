"""Система статистики сервера"""
from server_stats.manager import stats_manager
from server_stats.settings_view import StatsSettingsView
from server_stats.stat_collector import setup as setup_stats_collector
from server_stats.initializer import setup as setup_stats
from server_stats.base import PermanentView

__all__ = [
    'stats_manager',
    'StatsSettingsView',
    'setup_stats_collector',
    'setup_stats',
    'PermanentView'
]