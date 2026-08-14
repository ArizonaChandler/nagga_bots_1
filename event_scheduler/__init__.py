"""Event System - Автоматические оповещения о мероприятиях"""
from event_scheduler.scheduler import setup as setup_scheduler, scheduler
from event_scheduler.views import EventReminderView, EventInfoView
from event_scheduler.modals import ScheduleEventModal
from event_scheduler.settings_view import EventSchedulerSettingsView
from event_scheduler.base import PermanentView

__all__ = [
    'setup_scheduler',
    'scheduler',
    'EventReminderView',
    'EventInfoView',
    'ScheduleEventModal',
    'EventSchedulerSettingsView',
    'PermanentView'
]