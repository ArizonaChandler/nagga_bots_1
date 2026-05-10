"""Система игр Discord"""
import logging
from games.initializer import setup as setup_games
from games.manager import game_manager

logger = logging.getLogger(__name__)
logger.info("🎮 Модуль игр загружен")

__all__ = [
    'game_manager',
    'setup_games'
]