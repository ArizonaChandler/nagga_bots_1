"""Экономическая система и магазин баллов"""
import logging
from economy.manager import economy_manager
from economy.views import EconomyPanelView, AdminEconomyView
from economy.settings import EconomySettingsView

logger = logging.getLogger(__name__)
logger.info("💰 Модуль экономики загружен")

__all__ = [
    'economy_manager',
    'EconomyPanelView',
    'AdminEconomyView',
    'EconomySettingsView'
]


def set_bot_for_views(bot):
    """Передать бота во view для обновления embed"""
    EconomyPanelView.bot = bot