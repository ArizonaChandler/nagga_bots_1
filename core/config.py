"""Модуль конфигурации"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

SUPER_ADMIN_ID = os.getenv('SUPER_ADMIN_ID', '287670691707355147')

CONFIG = {
    # ===== ОСНОВНЫЕ НАСТРОЙКИ =====
    'channel_id': None,
    'server_id': None,
    'super_admin_id': SUPER_ADMIN_ID,
    'family_name': 'Семья',
    'global_settings_channel': None,
    
    # ===== ТОКЕНЫ =====
    'user_token_1': os.getenv('DISCORD_USER_TOKEN_1'),
    'user_token_2': os.getenv('DISCORD_USER_TOKEN_2'),
    
    # ===== CAPT СИСТЕМА =====
    'capt_channel_id': None,
    'capt_role_id': None,
    'capt_reg_main_channel': None,
    'capt_reg_reserve_channel': None,
    'capt_alert_channel': None,
    'capt_settings_channel': None,
    'capt_log_channel': None,
    
    # ===== MCL СИСТЕМА =====
    'mcl_reg_main_channel': None,
    'mcl_reg_reserve_channel': None,
    'mcl_error_channel': None,
    'mcl_role_id': None,
    'mcl_settings_channel': None,
    'mcl_announcement_channel': None,
    'mcl_log_channel': None,
    
    # ===== СИСТЕМА ЗАЯВОК =====
    'submit_channel': None,
    'submit_text': "Нажмите кнопку ниже, чтобы подать заявку",
    'submit_image': None,
    'applications_channel': None,
    'applications_log_channel': None,
    'applications_recruit_role': None,
    'applications_member_role': None,
    'applications_settings_channel': None,
    'applications_create_profiles': 'true',
    'application_custom_fields': [],
    
    # ===== ПРИВЕТСТВИЕ =====
    'welcome_message': None,
    'welcome_channel': None,
    'welcome_image': None,
    
    # ===== СИСТЕМА МЕРОПРИЯТИЙ =====
    'alarm_channels': [],
    'announce_channels': [],
    'reminder_roles': [],
    'announce_roles': [],
    'events_settings_channel': None,
    
    # ===== AFK СИСТЕМА =====
    'afk_channel': None,
    'afk_max_hours': 24,
    'afk_settings_channel': None,
    'afk_log_channel': None,
    
    # ===== TIER СИСТЕМА =====
    'tier_submit_channel': None,
    'tier_applications_channel': None,
    'tier_log_channel': None,
    'tier_info_channel': None,
    'tier_settings_channel': None,
    'tier_checker_role': None,
    'tier1_role': None,
    'tier2_role': None,
    'tier3_role': None,
    'tier_delete_profile': 'false',
    'tier_create_profile': 'false',
    'tier_profiles_category': None,
    
    # ===== СИСТЕМА ОТПУСКОВ =====
    'vacation_public_channel': None,
    'vacation_applications_channel': None,
    'vacation_log_channel': None,
    'vacation_settings_channel': None,
    'vacation_approve_roles': [],
    'vacation_role': None,
    'vacation_max_days': 30,
    
    # ===== СИСТЕМА ИГР =====
    'games_rules_channel': None,
    'games_lobby_channel': None,
    'games_log_channel': None,
    'games_settings_channel': None,
    'games_category_id': None,
    
    # ===== СИСТЕМА ДНЕЙ РОЖДЕНИЯ =====
    'birthday_channel': None,
    'birthday_greeting_channel': None,
    'birthday_settings_channel': None,
    'birthday_enabled': '1',
    
    # ===== АВТО-РЕКЛАМА =====
    'ad_settings_channel': None,
    
    # ===== ЭКОНОМИКА =====
    'economy_channel': None,
    'economy_admin_channel': None,
    'economy_settings_channel': None,
    'economy_logs_channel': None,
    
    # Настройки начисления баллов
    'eco_voice_points': '1',
    'eco_voice_max_per_day': '100',
    'eco_capt_main_points': '50',
    'eco_capt_reserve_points': '25',
    'eco_mcl_main_points': '75',
    'eco_mcl_reserve_points': '35',
    'eco_event_points': '30',
    'eco_application_points': '100',
    'eco_tier3_points': '50',
    'eco_tier2_points': '100',
    'eco_tier1_points': '200',
    
    # Ежедневный бонус
    'eco_daily_bonus': '25',
    'eco_daily_increment': '5',
    'eco_daily_limit': '30',
    
    # ===== РАСШИРЕННАЯ СТАТИСТИКА =====
    'stats_channel': None,
    'stats_settings_channel': None,
    'stats_backup_enabled': 'true',
    'stats_backup_time': '00:00',
    
    # ===== ВРЕМЕННЫЕ КОМНАТЫ =====
    'temp_voice_category': None,
    'temp_voice_public_channel': None,
    'temp_voice_log_channel': None,
    'temp_voice_settings_channel': None,
    'temp_voice_default_slots': 2,
    'temp_voice_max_slots': 10,
    'temp_voice_delete_delay': 60,

    # ===== ЛОГИРОВАНИЕ DISCORD =====
    'action_logs_channel': None,
    'action_logs_settings_channel': None,
    'action_logs_enabled_events': [],

    # ===== СОЗДАНИЕ EMBED =====
    'embed_builder_channel': None,
    'embed_builder_settings_channel': None,
}


def load_config():
    from core.database import db
    settings = db.get_all_settings()
    
    for key, value in settings.items():
        if key in CONFIG:
            if value and value.lower() != 'null':
                # Обработка JSON-массивов
                if key in ['alarm_channels', 'announce_channels', 'reminder_roles', 
                           'announce_roles', 'vacation_approve_roles', 'application_custom_fields']:
                    try:
                        CONFIG[key] = json.loads(value) if value else []
                    except:
                        CONFIG[key] = [value] if value else []
                else:
                    CONFIG[key] = value
            else:
                if key in ['alarm_channels', 'announce_channels', 'reminder_roles', 
                          'announce_roles', 'vacation_approve_roles', 'application_custom_fields']:
                    CONFIG[key] = []
                else:
                    CONFIG[key] = None
        else:
            # Добавляем новые ключи в CONFIG при миграции
            if key in ['economy_channel', 'economy_admin_channel', 'economy_settings_channel',
                       'eco_voice_points', 'eco_voice_max_per_day',
                       'eco_capt_main_points', 'eco_capt_reserve_points',
                       'eco_mcl_main_points', 'eco_mcl_reserve_points',
                       'eco_event_points', 'eco_application_points',
                       'eco_tier3_points', 'eco_tier2_points', 'eco_tier1_points',
                       'eco_daily_bonus', 'eco_daily_increment', 'eco_daily_limit',
                       'stats_channel', 'stats_settings_channel', 'stats_backup_enabled', 'stats_backup_time',
                       'temp_voice_category', 'temp_voice_public_channel', 'temp_voice_log_channel',
                       'temp_voice_settings_channel', 'temp_voice_default_slots', 
                       'temp_voice_max_slots', 'temp_voice_delete_delay']:
                CONFIG[key] = value if value and value.lower() != 'null' else None
    
    # Загружаем настройки модулей
    db.load_application_settings()
    db.load_tier_settings()
    db.load_vacation_settings()


def save_config(updated_by: str = None):
    from core.database import db
    for key, value in CONFIG.items():
        # Пропускаем токены, они не сохраняются в БД
        if key in ['user_token_1', 'user_token_2', 'super_admin_id']:
            continue
        
        # Обработка JSON-массивов
        if key in ['alarm_channels', 'announce_channels', 'reminder_roles', 
                   'announce_roles', 'vacation_approve_roles', 'application_custom_fields']:
            db.set_setting(key, json.dumps(value) if value else '[]', updated_by)
        else:
            db.set_setting(key, str(value) if value is not None else 'null', updated_by)