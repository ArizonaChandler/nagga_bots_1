"""Менеджер для работы с системой TIER"""
import re
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG


class TierManager:
    """Менеджер TIER (обертка над database.py)"""
    
    def get_settings(self):
        """Получить все настройки из CONFIG"""
        return {
            'tier_submit_channel': CONFIG.get('tier_submit_channel'),
            'tier_applications_channel': CONFIG.get('tier_applications_channel'),
            'tier_log_channel': CONFIG.get('tier_log_channel'),
            'tier_info_channel': CONFIG.get('tier_info_channel'),
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

    def save_application_message(self, application_id: int, channel_id: str, message_id: str, user_id: str):
        """Сохранить ID сообщения с заявкой"""
        return db.save_tier_application_message(application_id, channel_id, message_id, user_id)

    def get_all_application_messages(self):
        """Получить все сохранённые сообщения с заявками"""
        try:
            return db.get_all_tier_application_messages()
        except AttributeError as e:
            print(f"❌ Ошибка доступа к БД: {e}")
            return []

    def delete_application_message(self, application_id: int):
        """Удалить запись о сообщении"""
        return db.delete_tier_application_message(application_id)

    def reset_stuck_applications(self):
        """Сбросить все зависшие заявки (со статусом pending, но без активных сообщений)"""
        return db.reset_stuck_tier_applications()

    # ==================== НОВЫЙ МЕТОД: СОЗДАНИЕ ПРОФИЛЯ TIER ====================
    
    async def create_tier_profile(self, guild: discord.Guild, member: discord.Member, tier: str, nickname: str = None):
        """Создать личный профиль для пользователя при выдаче Tier"""
        
        if not nickname:
            nickname = member.display_name
        
        # Получаем ID категории для профилей Tier
        tier_profiles_category_id = CONFIG.get('tier_profiles_category')
        if not tier_profiles_category_id:
            print("⚠️ Категория для профилей Tier не настроена")
            return None, "Категория для профилей Tier не настроена"
        
        category = guild.get_channel(int(tier_profiles_category_id))
        if not category:
            print(f"❌ Категория {tier_profiles_category_id} не найдена")
            return None, "Категория для профилей Tier не найдена"
        
        # Получаем роль Tier Checker
        checker_role_id = CONFIG.get('tier_checker_role')
        checker_role = guild.get_role(int(checker_role_id)) if checker_role_id else None
        
        # Название канала
        channel_name = f"tier-{nickname[:20].lower().replace(' ', '-')}"
        channel_name = re.sub(r'[^a-zа-я0-9_-]', '', channel_name)
        
        # Эмодзи для уровня
        tier_emojis = {'tier3': '🟤', 'tier2': '⚪', 'tier1': '🔴'}
        
        # Права доступа
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                send_messages_in_threads=True,
                create_public_threads=True
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                manage_threads=True
            )
        }
        
        if checker_role:
            overwrites[checker_role] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                send_messages_in_threads=True
            )
        
        # Создаём канал
        try:
            channel = await guild.create_text_channel(
                f"{tier_emojis.get(tier, '🌟')}-{channel_name}",
                category=category,
                overwrites=overwrites,
                topic=f"Tier профиль | Пользователь: {member.id} | Уровень: {tier} | Получен: {datetime.now().strftime('%d.%m.%Y')}"
            )
        except Exception as e:
            print(f"❌ Ошибка создания канала: {e}")
            return None, f"Ошибка создания канала: {e}"
        
        # Отправляем приветственное сообщение
        tier_names = {'tier3': 'Tier 3 🟤', 'tier2': 'Tier 2 ⚪', 'tier1': 'Tier 1 🔴'}
        next_tier = self.get_next_tier(tier)
        
        embed = discord.Embed(
            title=f"{tier_emojis.get(tier, '🌟')} ПОЗДРАВЛЯЕМ С ПОЛУЧЕНИЕМ {tier_names.get(tier, tier.upper())}!",
            description=f"{member.mention}, **это твой личный Tier профиль**.\n\n"
                        f"Здесь ты можешь:\n"
                        f"└ Получать информацию о требованиях к следующему уровню\n"
                        f"└ Отслеживать свой прогресс\n"
                        f"└ Общаться с кураторами\n\n"
                        f"**Текущий уровень:** {tier_names.get(tier, tier.upper())}\n"
                        f"**Следующий уровень:** {next_tier if next_tier else '🏆 Максимальный уровень!'}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Tier система")
        
        await channel.send(embed=embed)
        
        return channel, None


tier_manager = TierManager()