"""Система дней рождения"""
import logging
from birthday.initializer import setup as setup_birthday
from birthday.manager import birthday_manager
from birthday.views import BirthdayPublicView, BirthdayModal, RemoveBirthdayModal

logger = logging.getLogger(__name__)
logger.info("🎂 Модуль дней рождения загружен")

__all__ = [
    'birthday_manager',
    'setup_birthday',
    'BirthdayPublicView',
    'BirthdayModal',
    'RemoveBirthdayModal'
]