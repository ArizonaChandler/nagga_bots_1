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
    'capt_role_id': None,           # Уже есть
    'message_1': 'Unit\nPink',
    'message_2': 'Unit\nBlue',
    'user_token_1': os.getenv('DISCORD_USER_TOKEN_1'),
    'user_token_2': os.getenv('DISCORD_USER_TOKEN_2'),
    'super_admin_id': SUPER_ADMIN_ID,
    'alarm_channels': [],           # списки каналов для напоминаний
    'announce_channels': [],         # списки каналов для оповещений
    'reminder_roles': [],            # списки ролей для упоминания в напоминаниях
    'announce_roles': [],            # списки ролей для упоминания в оповещениях
    'capt_reg_main_channel': None,   # канал для модерации CAPT регистрации
    'capt_reg_reserve_channel': None, # канал для всех пользователей
    'capt_alert_channel': None,      # канал для оповещений @everyone
    'capt_settings_channel': None,  # Канал для настроек CAPT
    'ad_settings_channel': None,  # Канал для настроек авто-рекламы
    'events_settings_channel': None,  # Канал для настроек мероприятий
    'applications_channel': None,
    'applications_log_channel': None,
    'applications_recruit_role': None,
    'applications_member_role': None,
    'applications_settings_channel': None,
}

db = Database()

def load_config():
    settings = db.get_all_settings()
    for key, value in settings.items():
        if key in CONFIG:
            if value and value.lower() != 'null':
                # Для списков - парсим JSON
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
            # Если ключа нет в CONFIG, но он есть в БД - добавляем
            if key in ['capt_reg_main_channel', 'capt_reg_reserve_channel', 'capt_alert_channel', 
                    'capt_role_id', 'capt_settings_channel', 'ad_settings_channel', 
                    'events_settings_channel']:
                CONFIG[key] = value if value and value.lower() != 'null' else None
    
    # Загружаем настройки системы заявок
    db.load_application_settings()

    colors = db.get_dual_colors()
    CONFIG['message_1'] = f"Unit\n{colors[0]}"
    CONFIG['message_2'] = f"Unit\n{colors[1]}"

def save_config(updated_by: str = None):
    for key, value in CONFIG.items():
        if key not in ['user_token_1', 'user_token_2', 'super_admin_id']:
            # Для списков - сохраняем как JSON
            if key in ['alarm_channels', 'announce_channels', 'reminder_roles', 'announce_roles']:
                db.set_setting(key, json.dumps(value) if value else '[]', updated_by)
            else:
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