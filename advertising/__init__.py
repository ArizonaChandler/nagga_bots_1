"""Auto Advertising Module"""
from advertising.core import setup as setup_advertising, advertiser
from advertising.commands import setup as setup_commands
from advertising.settings_view import AdSettingsView
from advertising.base import PermanentView

__all__ = [
    'setup_advertising',
    'setup_commands',
    'advertiser',
    'AdSettingsView',
    'PermanentView'
]