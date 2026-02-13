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
        # Словарь для отслеживания времени отправки напоминаний
        self.reminder_sent_time = {}  # {(event_id, date): timestamp}
    
    async def start(self):
        """Запуск планировщика"""
        logger.info("🕐 Event Scheduler запущен")
        self.task = asyncio.create_task(self._run())
    
    async def stop(self):
        """Остановка планировщика"""
        self.running = False
        if self.task:
            self.task.cancel()
            logger.info("🕐 Event Scheduler остановлен")
    
    async def _run(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                now = datetime.now(MSK_TZ)
                await self.check_events()
                await self.check_timeouts()
                
                # Генерируем расписание раз в день в 00:00
                if now.hour == 0 and now.minute == 0:
                    db.generate_schedule(days_ahead=14)
                    self.cleanup_old_reminders()
                    
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
            await asyncio.sleep(self.check_interval)
    
    async def check_events(self):
        """Проверка предстоящих мероприятий"""
        now = datetime.now(MSK_TZ)
        current_time = now.strftime("%H:%M")

        # Получаем мероприятия на сегодня
        today_events = db.get_today_events()

        for event in today_events:
            # Проверяем, нужно ли отправить напоминание (за 1 час)
            event_time = event['event_time']
            
            # Вычисляем время напоминания
            event_dt = datetime.strptime(event_time, "%H:%M")
            reminder_dt = (event_dt - timedelta(hours=1)).strftime("%H:%M")
            
            # Если время напоминания пришло (или прошло, но напоминание не отправлено)
            if current_time >= reminder_dt and not event['reminder_sent'] and not event['taken_by']:
                await self.send_reminder(event, now)
    
    async def check_timeouts(self):
        """Проверка, не истекло ли время взятия МП (40 минут)"""
        now = datetime.now(MSK_TZ)
        current_time = now.timestamp()
        
        for key, sent_time in list(self.reminder_sent_time.items()):
            event_id, event_date = key
            
            # Если прошло 40 минут (2400 секунд)
            if current_time - sent_time > 2400:
                # Проверяем, не взял ли кто-то МП
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT taken_by FROM event_schedule 
                        WHERE event_id = ? AND scheduled_date = ?
                    ''', (event_id, event_date))
                    result = cursor.fetchone()
                
                # Если никто не взял
                if not result or not result[0]:
                    await self.send_timeout_message(event_id, event_date)
                
                # Удаляем из отслеживания
                del self.reminder_sent_time[key]
    
    async def send_reminder(self, event, now):
        """Отправка напоминания о мероприятии"""
        try:
            channel_id = CONFIG.get('alarm_channel_id')
            if not channel_id:
                logger.error("Канал оповещений не настроен")
                return
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Канал {channel_id} не найден")
                return
            
            # Форматируем время
            event_time = event['event_time']
            
            # Вычисляем время сбора (за 20 минут до начала)
            event_dt = datetime.strptime(event_time, "%H:%M")
            meeting_time = (event_dt - timedelta(minutes=20)).strftime("%H:%M")
            
            # Создаём embed с напоминанием
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
            
            # Отправляем с кнопкой взятия
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
            
            # Отмечаем что напоминание отправлено
            today = now.date().isoformat()
            db.mark_reminder_sent(event['id'], today)
            db.log_event_action(event['id'], "reminder_sent")
            
            # Сохраняем время отправки для отслеживания таймаута
            self.reminder_sent_time[(event['id'], today)] = now.timestamp()
            
            logger.info(f"✅ Напоминание отправлено: {event['name']} в {event_time}, сбор в {meeting_time}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания: {e}")
    
    async def send_timeout_message(self, event_id: int, event_date: str):
        """Отправка сообщения об истечении времени"""
        try:
            channel_id = CONFIG.get('alarm_channel_id')
            if not channel_id:
                return
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return
            
            # Получаем информацию о мероприятии
            event = db.get_event(event_id)
            if not event:
                return
            
            embed = discord.Embed(
                title=f"⏰ ВРЕМЯ ВЫШЛО: {event['name']}",
                description=f"Никто не взял мероприятие в течение 40 минут после напоминания.",
                color=0xff0000
            )
            
            embed.add_field(
                name="⏰ Время начала",
                value=f"**{event['event_time']}** МСК",
                inline=True
            )
            
            embed.add_field(
                name="📅 Дата",
                value=event_date,
                inline=True
            )
            
            embed.set_footer(text="Мероприятие отменяется, если никто не возьмёт")
            
            await channel.send(embed=embed)
            
            logger.info(f"⚠️ Таймаут МП: {event['name']} на {event_date}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о таймауте: {e}")
    
    def cleanup_old_reminders(self):
        """Очистка старых записей о напоминаниях"""
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
    """Инициализация планировщика"""
    global scheduler
    scheduler = EventScheduler(bot)
    await scheduler.start()