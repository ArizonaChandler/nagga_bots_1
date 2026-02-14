"""Event Scheduler - Планировщик автоматических оповещений"""
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import discord
from core.database import db
from core.config import CONFIG
from events.views import EventReminderView

logger = logging.getLogger(__name__)

# Московское время
MSK_TZ = pytz.timezone('Europe/Moscow')

class EventScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.running = True
        self.check_interval = 60
        self.task = None
        self.reminder_sent_time = {}
    
    async def start(self):
        logger.info("🕐 Event Scheduler запущен")
        self.task = asyncio.create_task(self._run())
    
    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            logger.info("🕐 Event Scheduler остановлен")
    
    async def _run(self):
        while self.running:
            try:
                now = datetime.now(MSK_TZ)
                await self.check_events()
                await self.check_timeouts()
                
                if now.hour == 0 and now.minute == 0:
                    db.generate_schedule(days_ahead=14)
                    self.cleanup_old_reminders()
                    
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
            await asyncio.sleep(self.check_interval)
    
    async def check_events(self):
        """Проверка предстоящих мероприятий"""
        now = datetime.now(MSK_TZ)  # aware
        current_time = now.strftime("%H:%M")
        current_date = now.date()
        
        today_events = db.get_today_events()
        
        for event in today_events:
            event_time = event['event_time']
            
            # Парсим время мероприятия
            event_hour, event_minute = map(int, event_time.split(':'))
            
            # Создаем aware datetime для времени мероприятия
            event_datetime = MSK_TZ.localize(datetime(
                current_date.year, 
                current_date.month, 
                current_date.day, 
                event_hour, 
                event_minute
            ))
            
            # Если время мероприятия уже прошло - пропускаем
            if event_datetime < now:
                continue
            
            # Время напоминания (за 1 час)
            reminder_datetime = event_datetime - timedelta(hours=1)
            reminder_str = reminder_datetime.strftime("%H:%M")
            
            # Проверяем, нужно ли отправить напоминание
            if not event['reminder_sent'] and not event['taken_by']:
                # Если текущее время >= времени напоминания
                if now >= reminder_datetime:
                    await self.send_reminder(event, now)
    
    async def check_timeouts(self):
        """Проверка таймаутов (за 10 минут до начала)"""
        now = datetime.now(MSK_TZ)
        current_time = now.time()
        
        for key, sent_time in list(self.reminder_sent_time.items()):
            event_id, event_date = key
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT e.event_time, s.taken_by 
                    FROM events e
                    LEFT JOIN event_schedule s ON e.id = s.event_id AND s.scheduled_date = ?
                    WHERE e.id = ?
                ''', (event_date, event_id))
                result = cursor.fetchone()
                
                if not result:
                    del self.reminder_sent_time[key]
                    continue
                
                event_time_str, taken_by = result
                event_hour, event_minute = map(int, event_time_str.split(':'))
                
                # Создаем datetime для времени мероприятия
                event_datetime = MSK_TZ.localize(datetime(
                    now.year, now.month, now.day,
                    event_hour, event_minute
                ))
                
                # Время отключения кнопки (за 10 минут до)
                timeout_datetime = event_datetime - timedelta(minutes=10)
                
                if now >= timeout_datetime and not taken_by:
                    await self.send_timeout_message(event_id, event_date, event_time_str)
                    del self.reminder_sent_time[key]
                elif taken_by:
                    del self.reminder_sent_time[key]
    
    async def send_reminder(self, event, now):
        """Отправка напоминания"""
        try:
            channel_id = CONFIG.get('alarm_channel_id')
            if not channel_id:
                logger.error("Канал оповещений не настроен")
                return
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Канал {channel_id} не найден")
                return
            
            event_time = event['event_time']
            event_hour, event_minute = map(int, event_time.split(':'))
            
            # Время сбора (за 20 минут)
            meeting_datetime = MSK_TZ.localize(datetime(
                now.year, now.month, now.day,
                event_hour, event_minute
            )) - timedelta(minutes=20)
            meeting_time = meeting_datetime.strftime("%H:%M")
            
            embed = discord.Embed(
                title=f"🔔 НАПОМИНАНИЕ О МЕРОПРИЯТИИ: {event['name']}",
                description=f"Через 1 час начинается мероприятие **{event['name']}**!",
                color=0xffa500
            )
            
            embed.add_field(
                name="⏰ Время начала",
                value=f"**{event_time}** МСК",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Сбор в",
                value=f"**{meeting_time}** МСК",
                inline=True
            )
            
            embed.add_field(
                name="👥 Статус",
                value="❌ Никто не взял",
                inline=False
            )
            
            embed.set_footer(text="Unit Management System by Nagga")
            
            view = EventReminderView(
                event_id=event['id'],
                event_name=event['name'],
                event_time=event_time,
                meeting_time=meeting_time,
                guild=channel.guild
            )
            
            message = await channel.send(embed=embed, view=view)
            view.message = message
            
            today = now.date().isoformat()
            db.mark_reminder_sent(event['id'], today)
            db.log_event_action(event['id'], "reminder_sent")
            
            self.reminder_sent_time[(event['id'], today)] = now.timestamp()
            
            logger.info(f"✅ Напоминание отправлено: {event['name']} в {event_time}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания: {e}")
    
    async def send_timeout_message(self, event_id: int, event_date: str, event_time: str):
        """Сообщение о таймауте"""
        try:
            channel_id = CONFIG.get('alarm_channel_id')
            if not channel_id:
                return
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return
            
            event = db.get_event(event_id)
            if not event:
                return
            
            embed = discord.Embed(
                title=f"⏰ ВРЕМЯ ВЫШЛО: {event['name']}",
                description=f"Мероприятие в **{event_time}** не состоялось - никто не взял его вовремя.",
                color=0xff0000
            )
            
            embed.add_field(
                name="⏰ Время начала",
                value=f"**{event_time}** МСК",
                inline=True
            )
            
            embed.add_field(
                name="📅 Дата",
                value=event_date,
                inline=True
            )
            
            embed.set_footer(text="Unit Management System by Nagga")
            
            await channel.send(embed=embed)
            logger.info(f"⏰ Таймаут МП: {event['name']} на {event_date}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки таймаута: {e}")
    
    def cleanup_old_reminders(self):
        now = datetime.now(MSK_TZ)
        for key in list(self.reminder_sent_time.keys()):
            event_id, event_date = key
            try:
                date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()
                if (now.date() - date_obj).days > 7:
                    del self.reminder_sent_time[key]
            except:
                pass

scheduler = None

async def setup(bot):
    global scheduler
    scheduler = EventScheduler(bot)
    await scheduler.start()