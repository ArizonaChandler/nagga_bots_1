"""Система логирования действий на сервере"""
import logging
from action_logs.manager import action_logs_manager
from action_logs.views import ActionLogsPanelView, ActionLogsAdminView
from action_logs.settings_view import ActionLogsSettingsView
from action_logs.initializer import setup as setup_action_logs

logger = logging.getLogger(__name__)
logger.info("📋 Модуль логов действий загружен")

__all__ = [
    'action_logs_manager',
    'ActionLogsPanelView',
    'ActionLogsAdminView',
    'ActionLogsSettingsView',
    'setup_action_logs'
]