"""Система заявок в семью"""
from applications.manager import app_manager
from applications.views import ApplicationPublicView, ApplicationModerationView
from applications.settings_view import ApplicationsCombinedPanel
from applications.base import PermanentView

__all__ = [
    'app_manager',
    'ApplicationPublicView',
    'ApplicationModerationView',
    'ApplicationsCombinedPanel',
    'PermanentView'
]