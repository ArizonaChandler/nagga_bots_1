"""Модуль конфигурации"""
import os
import json
from dotenv import load_dotenv

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
    'capt_log_channel': None,
    'ad_settings_channel': None,
    'events_settings_channel': None,
    'applications_settings_channel': None,
    'application_custom_fields': [],
    'submit_text': "Нажмите кнопку ниже, чтобы подать заявку",
    'submit_image': None,
    'welcome_message': None,
    'welcome_channel': None,
    'welcome_image': None,
    'family_name': 'Семья',
    'afk_channel': None,
    'afk_max_hours': 24,
    'afk_settings_channel': None,
    'afk_log_channel': None,
    'tier_submit_channel': None,
    'tier_applications_channel': None,
    'tier_log_channel': None,
    'tier_info_channel': None,
    'tier_settings_channel': None,
    'tier_checker_role': None,
    'tier1_role': None,
    'tier2_role': None,
    'tier3_role': None,
    'stats_channel': None,
    'stats_backup_enabled': True,
    'stats_settings_channel': None,
    'vacation_public_channel': None,
    'vacation_applications_channel': None,
    'vacation_log_channel': None,
    'vacation_settings_channel': None,
    'vacation_approve_roles': [],
    'vacation_role': None,
    'vacation_max_days': 30,
    'games_rules_channel': None,
    'games_lobby_channel': None,
    'games_log_channel': None,
    'games_settings_channel': None,
    'games_category_id': None,
    'birthday_channel': None,
    'birthday_greeting_channel': None,
    'birthday_settings_channel': None,
    'birthday_enabled': '1',
    'mcl_reg_main_channel': None,
    'mcl_reg_reserve_channel': None,
    'mcl_error_channel': None,
    'mcl_role_id': None,
    'mcl_settings_channel': None,
    'mcl_announcement_channel': None,
    'global_settings_channel': None,
    
    # ========== НОВАЯ СИСТЕМА ЭКОНОМИКИ ==========
    # Каналы
    'economy_channel': None,           # Канал с панелью магазина
    'economy_admin_channel': None,     # Канал с админ-панелью
    'economy_settings_channel': None,  # Канал настроек экономики
    
    # Настройки начисления баллов
    'eco_voice_points': '1',           # Баллов за минуту в голосовом канале
    'eco_voice_max_per_day': '100',    # Максимум баллов в день за войс
    'eco_capt_main_points': '50',      # Баллов за CAPT (основной)
    'eco_capt_reserve_points': '25',   # Баллов за CAPT (резерв)
    'eco_mcl_main_points': '75',       # Баллов за MCL/ВЗМ (основной)
    'eco_mcl_reserve_points': '35',    # Баллов за MCL/ВЗМ (резерв)
    'eco_event_points': '30',          # Баллов за взятие МП
    'eco_application_points': '100',   # Баллов за принятие заявки
    'eco_tier3_points': '50',          # Баллов за повышение до Tier 3
    'eco_tier2_points': '100',         # Баллов за повышение до Tier 2
    'eco_tier1_points': '200',         # Баллов за повышение до Tier 1
    
    # Ежедневный бонус
    'eco_daily_bonus': '25',           # Базовая награда
    'eco_daily_increment': '5',        # Прирост за 2 дня серии
    'eco_daily_limit': '30',           # Лимит серии (дней)
}

def load_config():
    from core.database import db
    settings = db.get_all_settings()
    for key, value in settings.items():
        if key in CONFIG:
            if value and value.lower() != 'null':
                if key in ['alarm_channels', 'announce_channels', 'reminder_roles', 'announce_roles', 'vacation_approve_roles']:
                    try:
                        CONFIG[key] = json.loads(value) if value else []
                    except:
                        CONFIG[key] = [value] if value else []
                else:
                    CONFIG[key] = value
            else:
                if key in ['alarm_channels', 'announce_channels', 'reminder_roles', 'announce_roles', 'vacation_approve_roles']:
                    CONFIG[key] = []
                else:
                    CONFIG[key] = None
        else:
            # Добавляем новые ключи экономики в CONFIG
            if key in ['economy_channel', 'economy_admin_channel', 'economy_settings_channel',
                       'eco_voice_points', 'eco_voice_max_per_day',
                       'eco_capt_main_points', 'eco_capt_reserve_points',
                       'eco_mcl_main_points', 'eco_mcl_reserve_points',
                       'eco_event_points', 'eco_application_points',
                       'eco_tier3_points', 'eco_tier2_points', 'eco_tier1_points',
                       'eco_daily_bonus', 'eco_daily_increment', 'eco_daily_limit']:
                CONFIG[key] = value if value and value.lower() != 'null' else None
    
    db.load_application_settings()
    db.load_tier_settings()
    db.load_stats_settings()
    db.load_vacation_settings()

def save_config(updated_by: str = None):
    from core.database import db
    for key, value in CONFIG.items():
        if key not in ['user_token_1', 'user_token_2', 'super_admin_id']:
            if key in ['alarm_channels', 'announce_channels', 'reminder_roles', 'announce_roles', 'vacation_approve_roles']:
                db.set_setting(key, json.dumps(value) if value else '[]', updated_by)
            else:
                db.set_setting(key, str(value) if value is not None else 'null', updated_by)