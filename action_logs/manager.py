"""Менеджер логов действий"""
from datetime import datetime
from core.database import db
from core.config import CONFIG


class ActionLogsManager:
    
    def __init__(self):
        self.bot = None
    
    def set_bot(self, bot):
        self.bot = bot
    
    def get_settings(self):
        return {
            'action_logs_channel': CONFIG.get('action_logs_channel'),
            'action_logs_settings_channel': CONFIG.get('action_logs_settings_channel'),
            'action_logs_enabled_events': CONFIG.get('action_logs_enabled_events', []),
        }
    
    def save_setting(self, key: str, value, updated_by: str = None):
        db.set_setting(key, str(value), updated_by)
        CONFIG[key] = value
    
    def is_event_enabled(self, event_type: str) -> bool:
        """Проверить, включено ли логирование события"""
        enabled = self.get_settings().get('action_logs_enabled_events', [])
        if not enabled:
            return True
        return event_type in enabled
    
    async def log(self, guild_id: str, event_type: str, user_id: str, 
                  target_id: str = None, details: str = None,
                  before: str = None, after: str = None):
        """Записать лог и отправить в канал"""
        
        print(f"📋 [ACTION_LOGS] log() вызван: event_type={event_type}, user_id={user_id}")
        
        if not self.is_event_enabled(event_type):
            print(f"📋 [ACTION_LOGS] Событие {event_type} отключено в настройках")
            return
        
        # Сохраняем в БД
        db.save_action_log(guild_id, event_type, user_id, target_id, details, before, after)
        print(f"📋 [ACTION_LOGS] Лог сохранён в БД")
        
        # Отправляем в канал
        await self._send_to_channel(guild_id, event_type, user_id, target_id, details, before, after)
    
    async def _send_to_channel(self, guild_id: str, event_type: str, user_id: str,
                                target_id: str = None, details: str = None,
                                before: str = None, after: str = None):
        """Отправить лог в канал"""
        settings = self.get_settings()
        channel_id = settings.get('action_logs_channel')
        
        print(f"📋 [ACTION_LOGS] _send_to_channel: channel_id={channel_id}")
        
        if not channel_id or not self.bot:
            print(f"📋 [ACTION_LOGS] Канал логов не настроен: channel_id={channel_id}, bot={self.bot is not None}")
            return
        
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            print(f"📋 [ACTION_LOGS] Гильдия {guild_id} не найдена")
            return
        
        channel = guild.get_channel(int(channel_id))
        if not channel:
            print(f"📋 [ACTION_LOGS] Канал {channel_id} не найден в гильдии {guild.name}")
            return
        
        print(f"📋 [ACTION_LOGS] Канал найден: #{channel.name}, отправляем лог...")
        
        # Цвета для событий
        colors = {
            'voice_join': 0x00ff00,
            'voice_leave': 0xff0000,
            'voice_move': 0xffa500,
            'message_edit': 0xffa500,
            'message_delete': 0xff0000,
            'channel_create': 0x00ff00,
            'channel_delete': 0xff0000,
            'channel_update': 0xffa500,
            'role_grant': 0x00ff00,
            'role_revoke': 0xff0000,
            'role_create': 0x00ff00,
            'role_delete': 0xff0000,
            'member_join': 0x00ff00,
            'member_leave': 0xff0000,
            'member_update': 0xffa500,
        }
        
        event_names = {
            'voice_join': '🎙️ ПОДКЛЮЧЕНИЕ К ГОЛОСОВОМУ КАНАЛУ',
            'voice_leave': '🎙️ ОТКЛЮЧЕНИЕ ОТ ГОЛОСОВОГО КАНАЛА',
            'voice_move': '🎙️ ПЕРЕМЕЩЕНИЕ В ГОЛОСОВОМ КАНАЛЕ',
            'message_edit': '✏️ РЕДАКТИРОВАНИЕ СООБЩЕНИЯ',
            'message_delete': '🗑️ УДАЛЕНИЕ СООБЩЕНИЯ',
            'channel_create': '📝 СОЗДАНИЕ КАНАЛА',
            'channel_delete': '📝 УДАЛЕНИЕ КАНАЛА',
            'channel_update': '📝 ИЗМЕНЕНИЕ КАНАЛА',
            'role_grant': '🎭 ВЫДАЧА РОЛИ',
            'role_revoke': '🎭 СНЯТИЕ РОЛИ',
            'role_create': '🎭 СОЗДАНИЕ РОЛИ',
            'role_delete': '🎭 УДАЛЕНИЕ РОЛИ',
            'member_join': '👤 ПРИСОЕДИНЕНИЕ К СЕРВЕРУ',
            'member_leave': '👤 ПОКИДАНИЕ СЕРВЕРА',
            'member_update': '👤 ИЗМЕНЕНИЕ ПРОФИЛЯ',
        }
        
        embed = discord.Embed(
            title=event_names.get(event_type, event_type),
            color=colors.get(event_type, 0x7289da),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Пользователь", value=f"<@{user_id}>", inline=True)
        
        if target_id:
            embed.add_field(name="🎯 Цель", value=f"<@{target_id}>", inline=True)
        
        if before:
            embed.add_field(name="📝 Было", value=before[:1000], inline=False)
        
        if after:
            embed.add_field(name="📝 Стало", value=after[:1000], inline=False)
        
        if details:
            embed.add_field(name="📋 Детали", value=details[:1000], inline=False)
        
        embed.set_footer(text=f"ID: {user_id}")
        
        await channel.send(embed=embed)
        print(f"📋 [ACTION_LOGS] ✅ Лог отправлен в канал #{channel.name}")
    
    def get_logs(self, guild_id: str, limit: int = 100, offset: int = 0,
                 user_id: str = None, event_type: str = None, days: int = None) -> list:
        return db.get_action_logs(limit, offset, user_id, event_type, guild_id, days)
    
    def get_event_types(self, guild_id: str) -> list:
        return db.get_unique_action_log_events(guild_id)
    
    def get_stats(self, guild_id: str, days: int = 30) -> dict:
        return db.get_action_logs_stats(guild_id, days)


action_logs_manager = ActionLogsManager()