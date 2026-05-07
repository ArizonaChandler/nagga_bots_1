"""Система отпусков"""
from vacation.manager import vacation_manager
from vacation.views import VacationPublicView, VacationModerationView
from vacation.settings_view import VacationSettingsView
from vacation.initializer import setup as setup_vacation
from vacation.base import PermanentView

__all__ = [
    'vacation_manager',
    'VacationPublicView',
    'VacationModerationView',
    'VacationSettingsView',
    'setup_vacation',
    'PermanentView'
]