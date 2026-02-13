"""Event System - Автоматические оповещения о мероприятиях"""
from events.scheduler import setup as setup_scheduler, scheduler
from events.views import EventReminderView, EventInfoView
from events.modals import ScheduleEventModal

__all__ = [
    'setup_scheduler',
    'scheduler',
    'EventReminderView',
    'EventInfoView',
    'ScheduleEventModal'
]