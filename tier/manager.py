"""Менеджер для работы с системой TIR"""
import re
import discord
from core.database import db
from core.config import CONFIG

class TierManager:
    """Менеджер TIR (обертка над database.py)"""
    
    def get_settings(self):
        """Получить все настройки из CONFIG"""
        return {
            'tier_submit_channel': CONFIG.get('tier_submit_channel'),
            'tier_applications_channel': CONFIG.get('tier_applications_channel'),
            'tier_log_channel': CONFIG.get('tier_log_channel'),
            'tier_settings_channel': CONFIG.get('tier_settings_channel'),
            'tier_checker_role': CONFIG.get('tier_checker_role'),
            'tier1_role': CONFIG.get('tier1_role'),
            'tier2_role': CONFIG.get('tier2_role'),
            'tier3_role': CONFIG.get('tier3_role'),
        }
    
    def save_setting(self, key: str, value: str, updated_by: str = None):
        """Сохранить настройку"""
        db.set_tier_setting(key, value, updated_by)
        CONFIG[key] = value
    
    def save_tier_requirements(self, tier: str, requirements: str, updated_by: str = None):
        """Сохранить требования для конкретного тира"""
        db.set_tier_requirements(tier, requirements, updated_by)
    
    def get_tier_requirements(self, tier: str) -> str:
        """Получить требования для тира"""
        return db.get_tier_requirements(tier)
    
    def create_application(self, user_id: str, user_name: str, nickname: str,
                          arena_link: str, screenshots: str, additional: str, 
                          target_tier: str) -> tuple:
        """Создать заявку на повышение"""
        return db.create_tier_application(user_id, user_name, nickname, 
                                          arena_link, screenshots, additional, 
                                          target_tier)
    
    def get_pending_applications(self, target_tier: str = None):
        """Получить ожидающие заявки"""
        return db.get_pending_tier_applications(target_tier)
    
    def get_application(self, app_id: int):
        """Получить заявку по ID"""
        return db.get_tier_application(app_id)
    
    def approve_application(self, app_id: int, reviewer_id: str, target_tier: str):
        """Одобрить заявку и выдать роль"""
        return db.approve_tier_application(app_id, reviewer_id, target_tier)
    
    def reject_application(self, app_id: int, reviewer_id: str, reason: str):
        """Отклонить заявку"""
        return db.reject_tier_application(app_id, reviewer_id, reason)
    
    def get_user_current_tier(self, user_id: str, guild) -> str:
        """Определить текущий тир пользователя по ролям"""
        member = guild.get_member(int(user_id))
        if not member:
            return None
        
        tier1_role_id = CONFIG.get('tier1_role')
        tier2_role_id = CONFIG.get('tier2_role')
        tier3_role_id = CONFIG.get('tier3_role')
        
        roles = [str(r.id) for r in member.roles]
        
        if tier3_role_id and tier3_role_id in roles:
            return "tier3"
        elif tier2_role_id and tier2_role_id in roles:
            return "tier2"
        elif tier1_role_id and tier1_role_id in roles:
            return "tier1"
        return None
    
    def get_next_tier(self, current_tier: str) -> str:
        """Определить следующий тир"""
        tiers = ["tier3", "tier2", "tier1"]
        if current_tier in tiers:
            idx = tiers.index(current_tier)
            if idx + 1 < len(tiers):
                return tiers[idx + 1]
        return None

tier_manager = TierManager()