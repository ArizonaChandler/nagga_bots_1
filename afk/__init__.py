"""Система ухода в AFK"""
from afk.manager import afk_manager
from afk.views import AFKPublicView
from afk.settings_view import AFKSettingsView
from afk.initializer import setup as setup_afk
from afk.base import PermanentView

__all__ = [
    'afk_manager',
    'AFKPublicView',
    'AFKSettingsView',
    'setup_afk',
    'PermanentView'
]