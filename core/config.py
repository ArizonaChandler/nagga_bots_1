"""Модуль конфигурации"""
import os
import json
from dotenv import load_dotenv
from core.database import Database

load_dotenv()

SUPER_ADMIN_ID = os.getenv('SUPER_ADMIN_ID', '287670691707355147')

CONFIG = {
    'channel_id': None,
    'capt_channel_id': None,
    'server_id': None,
    'capt_role_id': None,
    'user_token_1': os.getenv('DISCORD_USER_TOKEN_1'),
    'user_token_2': os.getenv('DISCORD_USER_TOKEN_2'),
    'super_admin_id': SUPER_ADMIN_ID,
    'alarm_channels': [],
    'announce_channels': [],
    'reminder_roles': [],
    'announce_roles': [],
    'capt_reg_main_channel': None,
    'capt_reg_reserve_channel': None,
    'capt_alert_channel': None,
    'capt_settings_channel': None,
    'ad_settings_channel': None,
    'events_settings_channel': None,
    'applications_settings_channel': None,
    'family_name': 'Семья',
    'afk_channel': None,
    'afk_max_hours': 24,
    'afk_settings_channel': None,
}

# Создаём экземпляр БД
db = Database()

def load_config():
    settings = db.get_all_settings()
    for key, value in settings.items():
        if key in CONFIG:
            if value and value.lower() != 'null':
                if key in ['alarm_channels', 'announce_channels', 'reminder_roles', 'announce_roles']:
                    try:
                        CONFIG[key] = json.loads(value) if value else []
                    except:
                        CONFIG[key] = [value] if value else []
                else:
                    CONFIG[key] = value
            else:
                if key in ['alarm_channels', 'announce_channels', 'reminder_roles', 'announce_roles']:
                    CONFIG[key] = []
                else:
                    CONFIG[key] = None
        else:
            if key in ['capt_reg_main_channel', 'capt_reg_reserve_channel', 'capt_alert_channel', 
                       'capt_role_id', 'capt_settings_channel', 'ad_settings_channel', 
                       'events_settings_channel', 'applications_settings_channel', 'family_name']:
                CONFIG[key] = value if value and value.lower() != 'null' else None
    
    # Загружаем настройки заявок
    db.load_application_settings()

def save_config(updated_by: str = None):
    for key, value in CONFIG.items():
        if key not in ['user_token_1', 'user_token_2', 'super_admin_id']:
            if key in ['alarm_channels', 'announce_channels', 'reminder_roles', 'announce_roles']:
                db.set_setting(key, json.dumps(value) if value else '[]', updated_by)
            else:
                db.set_setting(key, str(value) if value is not None else 'null', updated_by)

load_config()