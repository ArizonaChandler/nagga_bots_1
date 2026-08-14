"""Менеджер мероприятий — сессии, участники, таймеры"""
import asyncio
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG


class EventsManager:
    
    def __init__(self):
        self.bot = None
        self.active_sessions = {}
        self.session_tasks = {}
        self.participants = {}
    
    def set_bot(self, bot):
        self.bot = bot
    
    def get_settings(self):
        return {
            'events_moderation_channel': CONFIG.get('events_moderation_channel'),
            'events_participant_channel': CONFIG.get('events_participant_channel'),
            'events_log_channel': CONFIG.get('events_log_channel'),
            'events_settings_channel': CONFIG.get('events_settings_channel'),
            'events_default_collect_time': int(CONFIG.get('events_default_collect_time', 20)),
        }
    
    def save_setting(self, key: str, value: str, updated_by: str = None):
        db.set_setting(key, value, updated_by)
        CONFIG[key] = value
    
    def create_session(self, creator_id: str, collect_time: int,
                       channel_id: str, message_id: str, event_time: str,
                       event_name: str = None, meeting_place: str = None,
                       additional_info: str = None) -> int:
        """Создать сессию мероприятия (без шаблона)"""
        session_id = db.create_event_session(
            creator_id=creator_id,
            collect_time=collect_time,
            channel_id=channel_id,
            message_id=message_id,
            event_time=event_time,
            event_name=event_name,
            meeting_place=meeting_place,
            additional_info=additional_info
        )
        return session_id
    
    def get_session(self, session_id: int) -> dict:
        return db.get_event_session(session_id)
    
    def get_active_sessions(self) -> list:
        return db.get_active_event_sessions()
    
    def end_session(self, session_id: int):
        db.end_event_session(session_id)
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.session_tasks:
            self.session_tasks[session_id].cancel()
            del self.session_tasks[session_id]
        if session_id in self.participants:
            del self.participants[session_id]
    
    def add_participant(self, session_id: int, user_id: str, user_name: str) -> bool:
        if session_id not in self.participants:
            self.participants[session_id] = []
        if user_id in self.participants[session_id]:
            return False
        self.participants[session_id].append(user_id)
        db.add_event_participant(session_id, user_id, user_name)
        return True
    
    def remove_participant(self, session_id: int, user_id: str) -> bool:
        if session_id not in self.participants:
            return False
        if user_id not in self.participants[session_id]:
            return False
        self.participants[session_id].remove(user_id)
        db.remove_event_participant(session_id, user_id)
        return True
    
    def get_participants(self, session_id: int) -> list:
        return db.get_event_participants(session_id)
    
    def get_participant_stats(self, user_id: str, days: int = 30) -> list:
        return db.get_user_event_participations(user_id, days)
    
    def get_organizer_stats(self, days: int = 7) -> list:
        return db.get_event_organizer_stats(days)
    
    async def start_collect_timer(self, session_id: int, collect_time: int,
                                   participant_channel_id: str, message_id: str):
        
        async def timer_task():
            await asyncio.sleep(collect_time * 60)
            
            session = self.get_session(session_id)
            if not session or session['status'] != 'active':
                return
            
            channel = self.bot.get_channel(int(participant_channel_id))
            if channel:
                try:
                    msg = await channel.fetch_message(int(message_id))
                    for child in msg.components[0].children:
                        child.disabled = True
                    await msg.edit(view=msg.components[0])
                except:
                    pass
            
            participants = self.get_participants(session_id)
            db.finalize_event_participants(session_id, participants)
            self.end_session(session_id)
            
            await self.log_action(
                session_id,
                f"⏰ Сбор завершён. Участников: {len(participants)}"
            )
        
        task = asyncio.create_task(timer_task())
        self.session_tasks[session_id] = task
    
    async def log_action(self, session_id: int, message: str):
        settings = self.get_settings()
        log_channel_id = settings.get('events_log_channel')
        if not log_channel_id:
            return
        
        channel = self.bot.get_channel(int(log_channel_id))
        if not channel:
            return
        
        embed = discord.Embed(
            title="🎯 МЕРОПРИЯТИЕ",
            description=message,
            color=0x00bfff,
            timestamp=datetime.now()
        )
        await channel.send(embed=embed)
    
    async def stop(self):
        for task in self.session_tasks.values():
            task.cancel()
        self.session_tasks.clear()
        self.active_sessions.clear()
        self.participants.clear()


events_manager = EventsManager()