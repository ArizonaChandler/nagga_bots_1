"""Расширенная статистика и бекап сервера"""
import logging
from stats.manager import stats_manager
from stats.views import StatsPanelView, BackupPanelView
from stats.settings import StatsSettingsView

logger = logging.getLogger(__name__)
logger.info("📊 Модуль расширенной статистики загружен")

__all__ = [
    'stats_manager',
    'StatsPanelView',
    'BackupPanelView',
    'StatsSettingsView'
]