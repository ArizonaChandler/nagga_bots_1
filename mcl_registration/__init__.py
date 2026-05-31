"""Система регистрации на MCL/ВЗМ"""
import logging
from mcl_registration.manager import mcl_manager
from mcl_registration.views import ModerationView, PublicView
from mcl_registration.embeds import create_registration_embed
from mcl_registration.settings import MCLSettingsView

logger = logging.getLogger(__name__)
logger.info("🎯 Модуль MCL загружен")

__all__ = [
    'mcl_manager',
    'ModerationView',
    'PublicView',
    'create_registration_embed'
]