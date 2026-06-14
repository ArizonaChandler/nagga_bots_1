"""Система временных голосовых комнат"""
import logging
from temp_voice.manager import temp_voice_manager
from temp_voice.views import TempVoicePublicView, TempVoiceManageView
from temp_voice.settings_view import TempVoiceSettingsView
from temp_voice.initializer import setup as setup_temp_voice

logger = logging.getLogger(__name__)
logger.info("🎤 Модуль временных комнат загружен")

__all__ = [
    'temp_voice_manager',
    'TempVoicePublicView',
    'TempVoiceManageView',
    'TempVoiceSettingsView',
    'setup_temp_voice'
]