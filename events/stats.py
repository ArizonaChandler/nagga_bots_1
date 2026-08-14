"""Статистика мероприятий — еженедельные отчёты"""
import asyncio
import discord
from datetime import datetime, timedelta
from core.database import db
from core.config import CONFIG


class EventStats:
    
    def __init__(self, bot):
        self.bot = bot
        self.task = None
    
    async def start(self):
        """Запустить еженедельный отчёт"""
        self.task = asyncio.create_task(self._weekly_report_loop())
        print("📊 [EVENTS] Еженедельная статистика запущена")
    
    async def stop(self):
        if self.task:
            self.task.cancel()
    
    async def _weekly_report_loop(self):
        """Цикл еженедельных отчётов"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            now = datetime.now()
            # В воскресенье в 23:59
            days_until_sunday = (6 - now.weekday()) % 7
            next_sunday = now + timedelta(days=days_until_sunday)
            next_sunday = next_sunday.replace(hour=23, minute=59, second=0)
            
            wait_seconds = (next_sunday - now).total_seconds()
            if wait_seconds < 0:
                wait_seconds += 7 * 24 * 60 * 60
            
            await asyncio.sleep(wait_seconds)
            
            await self._send_weekly_report()
    
    async def _send_weekly_report(self):
        """Отправить еженедельный отчёт"""
        settings = self.get_settings()
        channel_id = settings.get('events_moderation_channel')
        if not channel_id:
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            return
        
        # Статистика за неделю
        stats = db.get_event_organizer_stats(7)
        
        embed = discord.Embed(
            title="📊 **ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ МЕРОПРИЯТИЙ**",
            description=f"За период: {datetime.now().strftime('%d.%m.%Y')}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        if stats:
            text = ""
            for i, stat in enumerate(stats[:10], 1):
                text += f"{i}. <@{stat['user_id']}> — **{stat['count']}** МП\n"
            embed.add_field(name="🏆 Топ организаторов", value=text, inline=False)
        else:
            embed.add_field(name="🏆 Топ организаторов", value="За неделю не было мероприятий", inline=False)
        
        total_sessions = len(db.get_all_event_sessions())
        embed.add_field(name="📋 Всего сессий за неделю", value=f"**{len(stats)}**", inline=True)
        
        await channel.send(content="@everyone", embed=embed)
    
    def get_settings(self):
        return {
            'events_moderation_channel': CONFIG.get('events_moderation_channel'),
        }


event_stats = None