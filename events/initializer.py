"""Инициализация каналов системы мероприятий"""
import discord
import logging
from datetime import datetime
from core.database import db
from core.config import CONFIG
from events.manager import events_manager
from events.settings_view import EventsSettingsView
from events.modals import CreateEventModal
from events.stats import EventStats
from events.views import EventsParticipantView, EventsModerationView  # ← добавлен импорт

logger = logging.getLogger(__name__)


class EventsInitializer:
    
    def __init__(self, bot):
        self.bot = bot
        self.stats = None
    
    async def initialize_all(self):
        logger.info("🔄 Инициализация системы мероприятий...")
        print("🎯 [EVENTS] Инициализация системы мероприятий...")
        
        events_manager.set_bot(self.bot)
        
        self.moderation_channel_id = db.get_setting('events_moderation_channel')
        self.participant_channel_id = db.get_setting('events_participant_channel')
        self.log_channel_id = db.get_setting('events_log_channel')
        self.settings_channel_id = db.get_setting('events_settings_channel')
        
        if self.settings_channel_id == 'null' or self.settings_channel_id is None:
            self.settings_channel_id = None
        
        if self.participant_channel_id:
            await self._init_participant_channel()
        
        if self.settings_channel_id:
            await self._init_settings_channel()
        
        await self._restore_sessions()
        
        self.stats = EventStats(self.bot)
        await self.stats.start()
        print("📊 [EVENTS] Еженедельная статистика запущена")
        
        logger.info("✅ Инициализация системы мероприятий завершена")
        print("🎯 [EVENTS] Инициализация завершена")
    
    async def _init_participant_channel(self):
        try:
            channel = self.bot.get_channel(int(self.participant_channel_id))
            if not channel:
                logger.error(f"❌ Канал сбора участников {self.participant_channel_id} не найден")
                return
        except (ValueError, TypeError):
            logger.error(f"❌ Неверный ID канала сбора: {self.participant_channel_id}")
            return
        
        print(f"🎯 [EVENTS] Канал сбора участников готов: #{channel.name}")
    
    async def _init_settings_channel(self):
        try:
            if not self.settings_channel_id:
                return
            channel = self.bot.get_channel(int(self.settings_channel_id))
            if not channel:
                logger.error(f"❌ Канал настроек {self.settings_channel_id} не найден")
                return
        except (ValueError, TypeError):
            logger.error(f"❌ Неверный ID канала настроек: {self.settings_channel_id}")
            return
        
        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКА МЕРОПРИЯТИЙ**",
            description="Настройка системы мероприятий",
            color=0x00ff00
        )
        
        view = EventsSettingsView()
        
        found = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "НАСТРОЙКА МЕРОПРИЯТИЙ" in msg.embeds[0].title:
                    await msg.edit(embed=embed, view=view)
                    found = True
                    print(f"🎯 [EVENTS] Обновлена панель настроек в #{channel.name}")
                    break
        
        if not found:
            await channel.send(embed=embed, view=view)
            print(f"🎯 [EVENTS] Создана панель настроек в #{channel.name}")
    
    async def _restore_sessions(self):
        sessions = db.get_active_event_sessions()
        
        if not sessions:
            return
        
        print(f"🎯 [EVENTS] Восстановление {len(sessions)} активных сессий...")
        
        participant_channel_id = db.get_setting('events_participant_channel')
        if not participant_channel_id or participant_channel_id == 'null':
            print("⚠️ [EVENTS] Канал участников не настроен, пропускаем восстановление")
            return
        
        try:
            channel = self.bot.get_channel(int(participant_channel_id))
            if not channel:
                print(f"⚠️ [EVENTS] Канал {participant_channel_id} не найден")
                return
        except (ValueError, TypeError):
            print(f"⚠️ [EVENTS] Неверный ID канала: {participant_channel_id}")
            return
        
        for session in sessions:
            session_id = session['id']
            participants = db.get_event_participants(session_id)
            collect_time = session.get('collect_time', 20)
            
            events_manager.active_sessions[session_id] = session
            events_manager.participants[session_id] = [p['user_id'] for p in participants]
            
            if session.get('message_id'):
                try:
                    msg = await channel.fetch_message(int(session['message_id']))
                    
                    view = EventsParticipantView(session_id, collect_time)
                    view.set_message(msg)
                    view.remaining_minutes = collect_time
                    
                    content = self._build_participants_content(session, participants, collect_time)
                    await msg.edit(content=content, view=view)
                    
                    print(f"🎯 [EVENTS] Восстановлена сессия #{session_id}, участников: {len(participants)}")
                except discord.NotFound:
                    print(f"⚠️ [EVENTS] Сообщение сессии #{session_id} не найдено")
                except Exception as e:
                    print(f"⚠️ [EVENTS] Ошибка восстановления #{session_id}: {e}")
    
    def _build_participants_content(self, session: dict, participants: list, collect_time: int) -> str:
        event_name = session.get('event_name', 'Мероприятие')
        meeting_place = session.get('meeting_place', 'Не указано')
        
        content = (
            f"@everyone\n"
            f"**ВНИМАНИЕ, СБОР!**\n\n"
            f"Собирает: <@{session['creator_id']}> на **{event_name}**\n"
            f"📍 Место сбора: {meeting_place}\n"
            f"⏱️ Осталось времени: **{collect_time} мин.**\n"
        )
        if session.get('additional_info'):
            content += f"📝 {session['additional_info']}\n"
        
        if participants:
            content += f"\n**Участники ({len(participants)}):**\n"
            for p in participants:
                content += f"└ <@{p['user_id']}>\n"
        else:
            content += f"\n**Участники (0):**\n"
            content += "└ *Пока никого нет*"
        
        return content
    
    async def stop(self):
        if self.stats:
            await self.stats.stop()
        await events_manager.stop()
        print("🎯 [EVENTS] Система остановлена")


initializer = None

async def setup(bot):
    global initializer
    initializer = EventsInitializer(bot)
    await initializer.initialize_all()
    return initializer