"""Менеджер для работы с системой заявок"""
import re
import discord
from core.database import db
from core.config import CONFIG

class ApplicationManager:
    """Менеджер заявок (обертка над database.py)"""
    
    def get_settings(self):
        """Получить все настройки из CONFIG"""
        return {
            'submit_channel': CONFIG.get('submit_channel'),
            'applications_channel': CONFIG.get('applications_channel'),
            'applications_log_channel': CONFIG.get('applications_log_channel'),
            'applications_recruit_role': CONFIG.get('applications_recruit_role'),
            'applications_member_role': CONFIG.get('applications_member_role'),
        }
    
    def save_setting(self, key: str, value: str, updated_by: str = None):
        """Сохранить настройку"""
        db.set_application_setting(key, value, updated_by)
        CONFIG[key] = value
    
    def create_application(self, user_id: str, user_name: str, nickname: str, 
                          static: str, previous_families: str, prime_time: str, 
                          hours_per_day: str) -> tuple:
        """Создать заявку"""
        return db.create_application(user_id, user_name, nickname, static, 
                                    previous_families, prime_time, hours_per_day)
    
    def get_pending_applications(self):
        """Получить ожидающие заявки"""
        return db.get_pending_applications()
    
    def get_application(self, app_id: int):
        """Получить заявку по ID"""
        return db.get_application(app_id)
    
    def accept_application(self, app_id: int, reviewer_id: str):
        """Принять заявку"""
        return db.accept_application(app_id, reviewer_id)
    
    def reject_application(self, app_id: int, reviewer_id: str, reason: str):
        """Отклонить заявку"""
        return db.reject_application(app_id, reviewer_id, reason)
    
    def set_interviewing(self, app_id: int, reviewer_id: str):
        """Назначить обзвон"""
        return db.set_interviewing(app_id, reviewer_id)

    def reset_user_applications(self, user_id: str, reset_by: str = None):
        """Сбросить все заявки пользователя"""
        return db.reset_user_applications(user_id, reset_by)

    def check_member_in_guild(self, user_id: str, guild) -> bool:
        """Проверить, находится ли пользователь на сервере"""
        member = guild.get_member(int(user_id))
        return member is not None
    
    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С СООБЩЕНИЯМИ =====
    
    def save_application_message(self, application_id: int, channel_id: str, message_id: str, user_id: str):
        """Сохранить ID сообщения с заявкой"""
        return db.save_application_message(application_id, channel_id, message_id, user_id)
    
    def get_all_application_messages(self):
        """Получить все сохранённые сообщения с заявками"""
        return db.get_all_application_messages()
    
    def delete_application_message(self, application_id: int):
        """Удалить запись о сообщении"""
        return db.delete_application_message(application_id)
    
    def get_application_by_message(self, message_id: str):
        """Получить заявку по ID сообщения"""
        return db.get_application_by_message(message_id)

    def delete_interview_channel(self, channel_id: int):
        """Удалить канал обзвона"""
        try:
            return True
        except Exception as e:
            print(f"❌ Ошибка при удалении канала: {e}")
            return False
    
    # ===== НОВЫЕ МЕТОДЫ ДЛЯ ЛИЧНЫХ ПРОФИЛЕЙ =====
    
    async def get_next_category(self, guild, base_name="📁 PROFILES"):
        """Получить следующую доступную категорию (PROFILES, PROFILES 2 и т.д.)"""
        for i in range(1, 10):  # максимум 9 категорий
            name = f"{base_name}" if i == 1 else f"{base_name} {i}"
            category = discord.utils.get(guild.categories, name=name)
            if category and len(category.channels) < 50:  # лимит Discord - 50 каналов
                return category
            elif not category:
                # Создаём новую категорию
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                return await guild.create_category(name, overwrites=overwrites)
        return None
    
    async def create_member_profile(self, guild, member_id: str, nickname: str, static: str):
        """Создать личный профиль для принятого участника (один канал + ветки)"""
        member = guild.get_member(int(member_id))
        if not member:
            return None, "❌ Пользователь не найден на сервере"
        
        # Получаем или создаём категорию
        category = await self.get_next_category(guild, "📁 PROFILES")
        if not category:
            return None, "❌ Не удалось создать/найти категорию для профиля"
        
        # Название канала: ник_статик
        channel_name = f"{nickname[:20]}_{static[:15]}".lower().replace(" ", "_").replace("ё", "e")
        channel_name = re.sub(r'[^a-zа-я0-9_]', '', channel_name)
        
        # Права доступа
        recruit_role_id = CONFIG.get('applications_recruit_role')
        recruit_role = guild.get_role(int(recruit_role_id)) if recruit_role_id else None
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, manage_threads=True)
        }
        
        if recruit_role:
            overwrites[recruit_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Создаём текстовый канал
        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Личный профиль {nickname} | Статик: {static} | ID: {member_id}"
        )
        
        # Отправляем приветственное сообщение
        embed = discord.Embed(
            title="🎉 ДОБРО ПОЖАЛОВАТЬ В СЕМЬЮ!",
            description=f"{member.mention}, **это твой личный чат** в этом Discord-сервере с кураторами.\n\n"
                        f"Здесь ты будешь предоставлять информацию о своей активности в семье, "
                        f"задавать вопросы и общаться с кураторами/рекрутами.\n\n"
                        f"**📌 Ветки канала:**",
            color=0x00ff00
        )
        embed.add_field(name="🎮 РП/МП", value="└ Скриншоты с участием в РП/МП", inline=False)
        embed.add_field(name="🎯 CAPT/MCL", value="└ Откаты CAPT или MCL", inline=False)
        embed.add_field(name="⚔️ АРЕНА", value="└ Скриншоты с арены", inline=False)
        embed.add_field(name="💬 Общение с кураторами", value="└ Вопросы и общение с кураторами", inline=False)
        
        welcome_msg = await channel.send(embed=embed)
        
        # Создаём ветки (threads) ПОД приветственным сообщением
        threads_config = [
            {"name": "🎮-рп-мп", "description": "Скриншоты с участием в РП/МП"},
            {"name": "🎯-capt-mcl", "description": "Откаты CAPT или MCL"},
            {"name": "⚔️-арена", "description": "Скриншоты с арены"},
            {"name": "💬-общение-с-кураторами", "description": "Вопросы и общение с кураторами"}
        ]
        
        for config in threads_config:
            try:
                thread = await welcome_msg.create_thread(
                    name=config["name"],
                    auto_archive_duration=10080,  # 7 дней
                    type=discord.ChannelType.public_thread
                )
                
                # Отправляем описание в ветку
                desc_embed = discord.Embed(
                    description=f"**{config['description']}**\n\n"
                            f"Сюда ты можешь прикреплять скриншоты и информацию по этому направлению.\n"
                            f"Кураторы и рекруты будут проверять и комментировать.",
                    color=0x2b2d31
                )
                await thread.send(embed=desc_embed)
                print(f"✅ Создана ветка: {config['name']}")
            except Exception as e:
                print(f"❌ Ошибка создания ветки {config['name']}: {e}")
        
        return channel, None

app_manager = ApplicationManager()