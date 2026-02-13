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
        current_date = now.date()
        
        # Получаем мероприятия на сегодня
        today_events = db.get_today_events()
        
        for event in today_events:
            # Проверяем, что мероприятие ещё не началось
            event_time = event['event_time']
            event_dt = datetime.strptime(event_time, "%H:%M").time()
            
            # Если время мероприятия уже прошло сегодня - пропускаем
            if event_dt < now.time():
                continue
            
            # Вычисляем время напоминания (за 1 час до начала)
            reminder_dt = (datetime.combine(current_date, event_dt) - timedelta(hours=1)).time()
            reminder_str = reminder_dt.strftime("%H:%M")
            
            # Если время напоминания пришло и напоминание ещё не отправлено
            if current_time >= reminder_str and not event['reminder_sent'] and not event['taken_by']:
                await self.send_reminder(event, now)
    
    async def check_timeouts(self):
        """Проверка, не истекло ли время взятия МП (за 10 минут до начала)"""
        now = datetime.now(MSK_TZ)
        current_time = now.time()
        
        for key, sent_time in list(self.reminder_sent_time.items()):
            event_id, event_date = key
            
            # Получаем информацию о мероприятии
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
                event_time = datetime.strptime(event_time_str, "%H:%M").time()
                
                # Вычисляем время, за которое нужно отключить кнопку (за 10 минут до начала)
                from datetime import timedelta
                event_dt = datetime.combine(now.date(), event_time)
                timeout_dt = event_dt - timedelta(minutes=10)
                timeout_time = timeout_dt.time()
                
                # Если текущее время >= времени отключения И никто не взял
                if current_time >= timeout_time and not taken_by:
                    await self.send_timeout_message(event_id, event_date, event_time_str)
                    del self.reminder_sent_time[key]
                
                # Если кто-то взял - удаляем из отслеживания
                elif taken_by:
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
    
    async def send_timeout_message(self, event_id: int, event_date: str, event_time: str):
        """Отправка сообщения об истечении времени и отключение кнопки"""
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
            
            # Ищем сообщение с напоминанием в истории канала
            async for message in channel.history(limit=50):
                if message.author == self.bot.user and message.embeds:
                    embed = message.embeds[0]
                    # Проверяем, что это сообщение о нашем мероприятии
                    if embed.title and event['name'] in embed.title:
                        # Отключаем кнопки в старом сообщении
                        for child in message.components:
                            for component in child.children:
                                component.disabled = True
                        
                        # Создаём новое embed с сообщением о таймауте
                        new_embed = discord.Embed(
                            title=f"⏰ ВРЕМЯ ВЫШЛО: {event['name']}",
                            description=f"Мероприятие в **{event_time}** не состоялось - никто не взял его вовремя.",
                            color=0xff0000
                        )
                        
                        new_embed.add_field(
                            name="⏰ Время начала",
                            value=f"**{event_time}** МСК",
                            inline=True
                        )
                        
                        new_embed.add_field(
                            name="📅 Дата",
                            value=event_date,
                            inline=True
                        )
                        
                        new_embed.set_footer(text="Unit Management System by Nagga")
                        
                        # Редактируем сообщение
                        await message.edit(embed=new_embed, view=None)
                        break
            
            logger.info(f"⏰ Таймаут МП: {event['name']} на {event_date} в {event_time}")
            
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