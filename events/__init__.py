"""Event System - Автоматические оповещения о мероприятиях"""
from events.scheduler import setup as setup_scheduler, scheduler
from events.views import EventReminderView, EventInfoView
from events.modals import ScheduleEventModal
from events.settings_view import EventsSettingsView
from events.base import PermanentView

__all__ = [
    'setup_scheduler',
    'scheduler',
    'EventReminderView',
    'EventInfoView',
    'ScheduleEventModal',
    'EventsSettingsView',
    'PermanentView'
]