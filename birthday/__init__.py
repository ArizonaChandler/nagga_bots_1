"""Система дней рождения"""
import logging
from birthday.initializer import setup as setup_birthday
from birthday.manager import birthday_manager

logger = logging.getLogger(__name__)
logger.info("🎂 Модуль дней рождения загружен")

__all__ = [
    'birthday_manager',
    'setup_birthday'
]