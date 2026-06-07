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