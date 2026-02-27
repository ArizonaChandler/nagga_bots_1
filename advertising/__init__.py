"""Auto Advertising Module"""
from advertising.core import setup as setup_advertising, advertiser
from advertising.slash import AdSlashCommands
from advertising.views import AdSettingsView

__all__ = [
    'setup_advertising',
    'advertiser',
    'AdSlashCommands',
    'AdSettingsView'
]