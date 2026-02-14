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
        try:
            now = datetime.now(MSK_TZ)
            current_date = now.date()
            
            today_events = db.get_today_events()
            
            for event in today_events:
                try:
                    event_time = event['event_time']
                    
                    # Парсим время мероприятия
                    event_hour, event_minute = map(int, event_time.split(':'))
                    
                    # Создаем datetime для времени мероприятия (ВСЕГДА через MSK_TZ)
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
                    
                    # Проверяем, нужно ли отправить напоминание
                    if not event['reminder_sent'] and not event['taken_by']:
                        if now >= reminder_datetime:
                            await self.send_reminder(event, now)
                            
                except Exception as e:
                    logger.error(f"Ошибка обработки события {event.get('id')}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Ошибка в check_events: {e}")
    
    async def check_timeouts(self):
        """Проверка таймаутов (за 10 минут до начала)"""
        try:
            now = datetime.now(MSK_TZ)
            
            for key, sent_time in list(self.reminder_sent_time.items()):
                try:
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
                            
                except Exception as e:
                    logger.error(f"Ошибка обработки таймаута для ключа {key}: {e}")
                    # В случае ошибки удаляем ключ, чтобы не зацикливаться
                    if key in self.reminder_sent_time:
                        del self.reminder_sent_time[key]
                        
        except Exception as e:
            logger.error(f"Ошибка в check_timeouts: {e}")
    
    async def send_reminder(self, event, now):
        """Отправка напоминания"""
        try:
            # ПРИНУДИТЕЛЬНО делаем now offset-aware если он еще нет
            if now.tzinfo is None:
                now = MSK_TZ.localize(now)
            
            channel_id = CONFIG.get('alarm_channel_id')
            if not channel_id:
                logger.error("Канал оповещений не настроен")
                return
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Канал {channel_id} не найден")
                return
            
            event_time = event['event_time']
            
            # Время сбора (за 20 минут) - простая арифметика со строками
            event_hour, event_min = map(int, event_time.split(':'))
            meeting_hour = event_hour
            meeting_min = event_min - 20
            
            if meeting_min < 0:
                meeting_hour -= 1
                meeting_min += 60
            
            if meeting_hour < 0:
                meeting_hour = 23
            
            meeting_time = f"{meeting_hour:02d}:{meeting_min:02d}"
            
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
            
            from events.views import EventReminderView
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
            # Добавим детальную информацию
            import traceback
            traceback.print_exc()
    
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
        """Очистка старых записей"""
        try:
            now = datetime.now(MSK_TZ)
            for key in list(self.reminder_sent_time.keys()):
                try:
                    event_id, event_date = key
                    date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()
                    if (now.date() - date_obj).days > 7:
                        del self.reminder_sent_time[key]
                except:
                    # Если не можем обработать ключ - удаляем его
                    if key in self.reminder_sent_time:
                        del self.reminder_sent_time[key]
        except Exception as e:
            logger.error(f"Ошибка в cleanup_old_reminders: {e}")

scheduler = None

async def setup(bot):
    global scheduler
    scheduler = EventScheduler(bot)
    await scheduler.start()