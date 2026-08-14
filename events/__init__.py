"""Система мероприятий (ручное создание, сбор участников, статистика)"""
import logging
from events.manager import events_manager
from events.views import EventsModerationView, EventsParticipantView
from events.settings_view import EventsSettingsView
from events.initializer import setup as setup_events

logger = logging.getLogger(__name__)
logger.info("🎯 Модуль мероприятий загружен")

__all__ = [
    'events_manager',
    'EventsModerationView',
    'EventsParticipantView',
    'EventsSettingsView',
    'setup_events'
]