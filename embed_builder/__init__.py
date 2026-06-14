"""Система создания embed сообщений"""
import logging
from embed_builder.manager import embed_builder_manager
from embed_builder.views import EmbedBuilderPanelView
from embed_builder.settings_view import EmbedBuilderSettingsView
from embed_builder.initializer import setup as setup_embed_builder

logger = logging.getLogger(__name__)
logger.info("📦 Модуль создания embed загружен")

__all__ = [
    'embed_builder_manager',
    'EmbedBuilderPanelView',
    'EmbedBuilderSettingsView',
    'setup_embed_builder'
]