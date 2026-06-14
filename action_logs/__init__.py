"""Система логирования действий на сервере"""
import logging
from action_logs.manager import action_logs_manager
from action_logs.views import ActionLogsPanelView
from action_logs.settings_view import ActionLogsSettingsView, ActionLogsAdminView
from action_logs.initializer import setup as setup_action_logs

logger = logging.getLogger(__name__)
logger.info("📋 Модуль логов действий загружен")

__all__ = [
    'action_logs_manager',
    'ActionLogsPanelView',
    'ActionLogsSettingsView',
    'ActionLogsAdminView',
    'setup_action_logs'
]