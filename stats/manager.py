"""Менеджер статистики и бекапа"""
import discord
import json
import io
import asyncio
import os
import re
from datetime import datetime, timedelta
from core.database import db
from core.config import CONFIG
from core.utils import is_super_admin


class StatsManager:
    def __init__(self):
        self.bot = None
        self.stats_channel_id = None
        self.backup_enabled = True
        self.backup_time = "00:00"
        self.backup_task = None
        self.daily_stats = {}
        self.hourly_stats = {}
        self.user_stats = {}
        
    def set_bot(self, bot):
        self.bot = bot
        
    async def initialize(self):
        """Инициализация системы статистики"""
        print("📊 [STATS] Инициализация системы статистики...")
        
        self._load_config()
        
        # Запускаем планировщик бекапов, если включён
        if self.backup_enabled:
            await self.start_backup_scheduler()
        
        print("📊 [STATS] Инициализация завершена")
        
    def _load_config(self):
        self.stats_channel_id = CONFIG.get('stats_channel')
        self.backup_enabled = CONFIG.get('stats_backup_enabled') == 'true'
        self.backup_time = CONFIG.get('stats_backup_time', '00:00')
    
    # ==================== ЕЖЕДНЕВНАЯ СТАТИСТИКА ====================
    
    async def collect_daily_stats(self, guild: discord.Guild):
        """Сбор ежедневной статистики"""
        today = datetime.now().date().isoformat()
        
        # Получаем данные из БД
        new_members = db.get_daily_new_members(today)
        left_members = db.get_daily_left_members(today)
        new_applications = db.get_daily_applications(today)
        accepted_applications = db.get_daily_accepted_applications(today)
        capt_registrations = db.get_daily_capt_registrations(today)
        mcl_registrations = db.get_daily_mcl_registrations(today)
        mp_takes = db.get_daily_mp_takes(today)
        
        # Максимальный онлайн в войсе
        max_voice = await self._get_daily_voice_peak(guild)
        
        stats = {
            'date': today,
            'new_members': new_members,
            'left_members': left_members,
            'new_applications': new_applications,
            'accepted_applications': accepted_applications,
            'max_voice_online': max_voice,
            'capt_registrations': capt_registrations,
            'mcl_registrations': mcl_registrations,
            'mp_takes': mp_takes
        }
        
        db.save_daily_stats(stats)
        return stats
    
    async def _get_daily_voice_peak(self, guild: discord.Guild) -> int:
        """Получить максимальный онлайн в войсе за день"""
        peak = 0
        for channel in guild.voice_channels:
            peak = max(peak, len(channel.members))
        return peak
    
    # ==================== ПОЧАСОВАЯ СТАТИСТИКА ====================
    
    async def update_hourly_stats(self, guild: discord.Guild):
        """Обновить почасовую статистику"""
        now = datetime.now()
        hour = now.hour
        today = now.date().isoformat()
        
        messages = db.get_hourly_messages(today, hour)
        voice_users = await self._get_current_voice_users(guild)
        
        db.update_hourly_stats(today, hour, messages, voice_users)
    
    async def _get_current_voice_users(self, guild: discord.Guild) -> int:
        """Получить текущее количество пользователей в войсе"""
        total = 0
        for channel in guild.voice_channels:
            total += len(channel.members)
        return total
    
    # ==================== СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ ====================
    
    async def update_user_stats(self, user_id: int, field: str, delta: int = 1):
        """Обновить статистику пользователя"""
        today = datetime.now().date().isoformat()
        db.update_user_activity(str(user_id), today, field, delta)
    
    async def get_user_stats(self, user_id: int, days: int = 7) -> dict:
        """Получить статистику пользователя за N дней"""
        return db.get_user_activity(str(user_id), days)
    
    async def get_top_users(self, field: str, limit: int = 10, days: int = 30) -> list:
        """Получить топ пользователей по полю"""
        return db.get_top_users(field, limit, days)
    
    # ==================== БЕКАП СЕРВЕРА ====================
    
    async def create_backup(self, guild: discord.Guild, created_by: str = None) -> dict:
        """Создать полный бекап сервера"""
        backup = {
            'timestamp': datetime.now().isoformat(),
            'guild_id': str(guild.id),
            'guild_name': guild.name,
            'guild_icon': str(guild.icon.url) if guild.icon else None,
            'categories': await self._backup_categories(guild),
            'channels': await self._backup_channels(guild),
            'roles': await self._backup_roles(guild),
            'members_roles': await self._backup_members_roles(guild),
            'guild_settings': await self._backup_guild_settings(guild)
        }
        
        # Сохраняем в БД
        backup_json = json.dumps(backup, ensure_ascii=False, default=str)
        backup_id = db.save_server_backup(backup_json, created_by)
        
        return backup
    
    async def _backup_categories(self, guild: discord.Guild) -> list:
        """Бекап категорий"""
        categories = []
        for category in guild.categories:
            categories.append({
                'id': str(category.id),
                'name': category.name,
                'position': category.position,
                'overwrites': self._serialize_overwrites(category.overwrites)
            })
        return categories
    
    async def _backup_channels(self, guild: discord.Guild) -> list:
        """Бекап каналов"""
        channels = []
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                channels.append({
                    'id': str(channel.id),
                    'name': channel.name,
                    'type': 'text',
                    'category_id': str(channel.category_id) if channel.category_id else None,
                    'position': channel.position,
                    'topic': channel.topic,
                    'slowmode_delay': channel.slowmode_delay,
                    'nsfw': channel.nsfw,
                    'overwrites': self._serialize_overwrites(channel.overwrites)
                })
            elif isinstance(channel, discord.VoiceChannel):
                channels.append({
                    'id': str(channel.id),
                    'name': channel.name,
                    'type': 'voice',
                    'category_id': str(channel.category_id) if channel.category_id else None,
                    'position': channel.position,
                    'bitrate': channel.bitrate,
                    'user_limit': channel.user_limit,
                    'overwrites': self._serialize_overwrites(channel.overwrites)
                })
        return channels
    
    async def _backup_roles(self, guild: discord.Guild) -> list:
        """Бекап ролей"""
        roles = []
        for role in sorted(guild.roles, key=lambda x: x.position, reverse=True):
            if role.is_default():
                continue
            roles.append({
                'id': str(role.id),
                'name': role.name,
                'color': role.color.value,
                'hoist': role.hoist,
                'mentionable': role.mentionable,
                'permissions': role.permissions.value,
                'position': role.position
            })
        return roles
    
    async def _backup_members_roles(self, guild: discord.Guild) -> dict:
        """Бекап ролей участников"""
        members_roles = {}
        for member in guild.members:
            role_ids = [str(role.id) for role in member.roles if not role.is_default()]
            if role_ids:
                members_roles[str(member.id)] = role_ids
        return members_roles
    
    async def _backup_guild_settings(self, guild: discord.Guild) -> dict:
        """Бекап настроек сервера"""
        return {
            'verification_level': guild.verification_level.value,
            'default_notifications': guild.default_notifications.value,
            'explicit_content_filter': guild.explicit_content_filter.value,
            'afk_channel_id': str(guild.afk_channel.id) if guild.afk_channel else None,
            'afk_timeout': guild.afk_timeout,
            'system_channel_id': str(guild.system_channel.id) if guild.system_channel else None
        }
    
    def _serialize_overwrites(self, overwrites) -> dict:
        """Сериализация прав доступа"""
        result = {}
        for target, overwrite in overwrites.items():
            target_id = str(target.id)
            target_type = 'role' if isinstance(target, discord.Role) else 'member'
            result[target_id] = {
                'type': target_type,
                'allow': overwrite.pair()[0].value,
                'deny': overwrite.pair()[1].value
            }
        return result
    
    # ==================== ВОССТАНОВЛЕНИЕ СЕРВЕРА ====================
    
    async def restore_server(self, interaction: discord.Interaction, backup_data: dict) -> bool:
        """Восстановить сервер из бекапа"""
        guild = interaction.guild
        
        # 1. Создаём канал для уведомлений
        try:
            restore_channel = await guild.create_text_channel(
                '🔄-восстановление-сервера',
                reason='Восстановление сервера из бекапа'
            )
            await restore_channel.send(
                content='@everyone',
                embed=discord.Embed(
                    title="🔄 НАЧАЛО ВОССТАНОВЛЕНИЯ СЕРВЕРА",
                    description="Сервер восстанавливается из резервной копии.\n"
                                "В процессе восстановления каналы и роли будут пересозданы.\n"
                                "Пожалуйста, ничего не предпринимайте до завершения процесса.",
                    color=0xffa500
                )
            )
        except Exception as e:
            print(f"❌ Ошибка создания канала восстановления: {e}")
            restore_channel = None
        
        # 2. Удаляем существующие каналы и категории (кроме канала восстановления)
        for channel in guild.channels:
            if restore_channel and channel.id == restore_channel.id:
                continue
            try:
                await channel.delete()
            except:
                pass
        
        # 3. Удаляем существующие роли (кроме @everyone)
        for role in guild.roles:
            if role.is_default():
                continue
            try:
                await role.delete()
            except:
                pass
        
        # 4. Восстанавливаем роли (сначала создаём все роли)
        roles_map = {}
        for role_data in backup_data.get('roles', []):
            try:
                new_role = await guild.create_role(
                    name=role_data['name'],
                    color=discord.Color(role_data['color']),
                    hoist=role_data['hoist'],
                    mentionable=role_data['mentionable'],
                    permissions=discord.Permissions(role_data['permissions'])
                )
                roles_map[role_data['id']] = new_role
            except Exception as e:
                print(f"❌ Ошибка создания роли {role_data['name']}: {e}")
        
        # 5. Восстанавливаем категории
        categories_map = {}
        for category_data in backup_data.get('categories', []):
            try:
                new_category = await guild.create_category(
                    name=category_data['name'],
                    position=category_data['position']
                )
                categories_map[category_data['id']] = new_category
            except Exception as e:
                print(f"❌ Ошибка создания категории: {e}")
        
        # 6. Восстанавливаем каналы
        for channel_data in backup_data.get('channels', []):
            try:
                category = categories_map.get(channel_data.get('category_id'))
                if channel_data['type'] == 'text':
                    await guild.create_text_channel(
                        name=channel_data['name'],
                        category=category,
                        position=channel_data['position'],
                        topic=channel_data.get('topic'),
                        slowmode_delay=channel_data.get('slowmode_delay', 0),
                        nsfw=channel_data.get('nsfw', False)
                    )
                elif channel_data['type'] == 'voice':
                    await guild.create_voice_channel(
                        name=channel_data['name'],
                        category=category,
                        position=channel_data['position'],
                        bitrate=channel_data.get('bitrate', 64000),
                        user_limit=channel_data.get('user_limit', 0)
                    )
            except Exception as e:
                print(f"❌ Ошибка создания канала: {e}")
        
        # 7. Восстанавливаем права доступа (после создания всех каналов)
        # TODO: восстановление overwrites
        
        # 8. Отправляем уведомление о завершении
        if restore_channel:
            await restore_channel.send(
                embed=discord.Embed(
                    title="✅ ВОССТАНОВЛЕНИЕ ЗАВЕРШЕНО",
                    description="Сервер успешно восстановлен из резервной копии!\n"
                                "Проверьте каналы и роли.",
                    color=0x00ff00
                )
            )
        
        return True
    
    # ==================== ЗАПУСК БЕКАПА ПО РАСПИСАНИЮ ====================
    
    async def start_backup_scheduler(self):
        """Запуск планировщика бекапов"""
        if self.backup_task:
            self.backup_task.cancel()
        
        self.backup_task = asyncio.create_task(self._backup_loop())
    
    async def _backup_loop(self):
        """Цикл ежедневного бекапа"""
        while True:
            try:
                now = datetime.now()
                target_time = datetime.strptime(self.backup_time, "%H:%M").time()
                target_datetime = datetime.combine(now.date(), target_time)
                
                if now.time() > target_time:
                    target_datetime += timedelta(days=1)
                
                wait_seconds = (target_datetime - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                # Создаём бекап и отправляем супер-админу
                if self.bot and self.backup_enabled:
                    for guild in self.bot.guilds:
                        backup = await self.create_backup(guild, 'system')
                        
                        # Отправляем супер-админу в ЛС
                        super_admin_id = CONFIG.get('super_admin_id')
                        if super_admin_id:
                            try:
                                user = await self.bot.fetch_user(int(super_admin_id))
                                if user:
                                    # Создаём JSON файл бекапа
                                    backup_json = json.dumps(backup, ensure_ascii=False, indent=2)
                                    file = discord.File(
                                        io.BytesIO(backup_json.encode('utf-8')),
                                        filename=f"backup_discord_{guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                                    )
                                    
                                    # Бекап БД
                                    db_backup_path = f"backup_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                                    os.system(f"cp bot_data.db /tmp/{db_backup_path}")
                                    db_file = discord.File(f"/tmp/{db_backup_path}", filename=db_backup_path)
                                    
                                    # Отправляем
                                    await user.send(
                                        content=f"💾 **ЕЖЕДНЕВНЫЙ БЕКАП**\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n📊 Сервер: {guild.name}",
                                        files=[file, db_file]
                                    )
                                    
                                    # Чистим временный файл
                                    os.system(f"rm /tmp/{db_backup_path}")
                                    
                            except Exception as e:
                                print(f"❌ Ошибка отправки бекапа: {e}")
                                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Ошибка в цикле бекапа: {e}")
                await asyncio.sleep(60)
    
    # ==================== ОСТАНОВКА ====================
    
    async def stop(self):
        """Остановка модуля"""
        if self.backup_task:
            self.backup_task.cancel()
        print("📊 [STATS] Остановка системы статистики")


stats_manager = StatsManager()