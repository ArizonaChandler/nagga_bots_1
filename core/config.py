"""Модуль конфигурации"""
import os
from dotenv import load_dotenv
from core.database import db

load_dotenv()

SUPER_ADMIN_ID = os.getenv('SUPER_ADMIN_ID', '287670691707355147')

CONFIG = {
    'channel_id': None,
    'capt_channel_id': None,
    'server_id': None,
    'capt_role_id': None,
    'message_1': 'Unit\nPink',
    'message_2': 'Unit\nBlue',
    'user_token_1': os.getenv('DISCORD_USER_TOKEN_1'),
    'user_token_2': os.getenv('DISCORD_USER_TOKEN_2'),
    'super_admin_id': SUPER_ADMIN_ID,
    # НОВОЕ: канал для оповещений
    'alarm_channel_id': None
}

def load_config():
    settings = db.get_all_settings()
    for key, value in settings.items():
        if key in CONFIG:
            if value and value.lower() != 'null':
                CONFIG[key] = value
            else:
                CONFIG[key] = None
    
    colors = db.get_dual_colors()
    CONFIG['message_1'] = f"Unit\n{colors[0]}"
    CONFIG['message_2'] = f"Unit\n{colors[1]}"

def save_config(updated_by: str = None):
    for key, value in CONFIG.items():
        if key not in ['user_token_1', 'user_token_2', 'super_admin_id']:
            db.set_setting(key, str(value) if value is not None else 'null', updated_by)
    
    if 'message_1' in CONFIG and '\n' in CONFIG['message_1']:
        color1 = CONFIG['message_1'].split('\n')[1]
    else:
        color1 = 'Pink'
    
    if 'message_2' in CONFIG and '\n' in CONFIG['message_2']:
        color2 = CONFIG['message_2'].split('\n')[1]
    else:
        color2 = 'Blue'
    
    db.save_dual_colors(color1, color2, updated_by)

load_config()