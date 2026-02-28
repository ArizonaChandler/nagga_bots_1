"""Система регистрации на CAPT"""
import logging
from capt_registration.manager import capt_reg_manager
from capt_registration.views import ModerationView, PublicView
from capt_registration.embeds import create_registration_embed

logger = logging.getLogger(__name__)
logger.info("📦 Модуль capt_registration загружен")

__all__ = [
    'capt_reg_manager',
    'ModerationView',
    'PublicView',
    'create_registration_embed'
]