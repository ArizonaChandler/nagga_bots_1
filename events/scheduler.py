"""Event Scheduler - Планировщик автоматических оповещений"""
import asyncio
import logging
import traceback
from datetime import datetime, timedelta
import pytz
import discord
from core.database import db
from core.config import CONFIG
from events.views import EventReminderView

# Существующий логгер для консоли
logger = logging.getLogger(__name__)

# НОВЫЙ файловый логгер
file_logger = logging.getLogger('events_scheduler')
file_logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('event_scheduler.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
file_logger.addHandler(fh)

# Московское время
MSK_TZ = pytz.timezone('Europe/Moscow')

class EventScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.running = True
        self.check_interval = 60
        self.task = None
        self.reminder_sent_time = {}
        file_logger.debug("EventScheduler инициализирован")
    
    async def start(self):
        file_logger.info("🕐 Event Scheduler запущен")
        logger.info("🕐 Event Scheduler запущен")
        self.task = asyncio.create_task(self._run())
    
    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            file_logger.info("🕐 Event Scheduler остановлен")
            logger.info("🕐 Event Scheduler остановлен")
    
    async def _run(self):
        file_logger.debug("Запуск основного цикла")
        while self.running:
            try:
                now = datetime.now(MSK_TZ)
                file_logger.debug(f"Проверка событий в {now}")
                
                await self.check_events()
                await self.check_timeouts()
                
                if now.hour == 0 and now.minute == 0:
                    file_logger.info("Генерация расписания на 14 дней")
                    db.generate_schedule(days_ahead=14)
                    self.cleanup_old_reminders()
                    
            except Exception as e:
                file_logger.error(f"Ошибка в планировщике: {e}")
                file_logger.error(traceback.format_exc())
                logger.error(f"Ошибка в планировщике: {e}")
            await asyncio.sleep(self.check_interval)
    
    async def check_events(self):
        """Проверка предстоящих мероприятий"""
        file_logger.debug("="*50)
        file_logger.debug("check_events START")
        
        try:
            now = datetime.now(MSK_TZ)
            current_time_str = now.strftime("%H:%M")
            current_date = now.date()
            
            file_logger.debug(f"Текущее время: {now}")
            file_logger.debug(f"current_time_str: {current_time_str}")
            file_logger.debug(f"current_date: {current_date}")
            
            today_events = db.get_today_events()
            file_logger.debug(f"Найдено мероприятий на сегодня: {len(today_events)}")
            
            for event in today_events:
                try:
                    file_logger.debug(f"--- Обработка события ID: {event['id']} ---")
                    file_logger.debug(f"Название: {event['name']}")
                    file_logger.debug(f"Время: {event['event_time']}")
                    file_logger.debug(f"reminder_sent: {event['reminder_sent']}")
                    file_logger.debug(f"taken_by: {event['taken_by']}")
                    
                    # Если уже взяли - пропускаем
                    if event['taken_by']:
                        file_logger.debug("Мероприятие уже взято, пропускаем")
                        continue
                    
                    event_time = event['event_time']
                    
                    # Вычисляем время напоминания (за 1 час ДО)
                    event_hour, event_min = map(int, event_time.split(':'))
                    reminder_hour = event_hour - 1
                    reminder_min = event_min
                    
                    # Обработка перехода через полночь
                    if reminder_hour < 0:
                        reminder_hour = 23
                    
                    reminder_time = f"{reminder_hour:02d}:{reminder_min:02d}"
                    file_logger.debug(f"Время напоминания: {reminder_time}")
                    
                    # Проверяем, что текущее время РАВНО времени напоминания
                    # И напоминание ещё не отправлено
                    file_logger.debug(f"Сравнение: {current_time_str} == {reminder_time}?")
                    if current_time_str == reminder_time and not event['reminder_sent']:
                        file_logger.info(f"✅ ПОРА отправлять напоминание для {event['name']} в {event_time}")
                        await self.send_reminder(event, now)
                    else:
                        file_logger.debug("Условия не выполнены")
                        
                except Exception as e:
                    file_logger.error(f"Ошибка обработки события {event.get('id')}: {e}")
                    file_logger.error(traceback.format_exc())
                    continue
                    
        except Exception as e:
            file_logger.error(f"Ошибка в check_events: {e}")
            file_logger.error(traceback.format_exc())
    
    async def check_timeouts(self):
        """Проверка таймаутов (за 10 минут до начала)"""
        file_logger.debug("="*50)
        file_logger.debug("check_timeouts START")
        
        try:
            now = datetime.now(MSK_TZ)
            current_time_str = now.strftime("%H:%M")
            file_logger.debug(f"Текущее время для таймаутов: {current_time_str}")
            file_logger.debug(f"Отслеживается напоминаний: {len(self.reminder_sent_time)}")
            
            for key, sent_time in list(self.reminder_sent_time.items()):
                try:
                    event_id, event_date = key
                    file_logger.debug(f"Проверка таймаута для event_id={event_id}, date={event_date}")
                    
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
                            file_logger.debug(f"Мероприятие {event_id} не найдено, удаляем из отслеживания")
                            del self.reminder_sent_time[key]
                            continue
                        
                        event_time_str, taken_by = result
                        file_logger.debug(f"Время мероприятия: {event_time_str}, taken_by: {taken_by}")
                        
                        # Если уже взяли - удаляем из отслеживания
                        if taken_by:
                            file_logger.debug(f"Мероприятие уже взято пользователем {taken_by}, удаляем из отслеживания")
                            del self.reminder_sent_time[key]
                            continue
                        
                        # Время отключения кнопки (за 10 минут до)
                        event_hour, event_min = map(int, event_time_str.split(':'))
                        timeout_hour = event_hour
                        timeout_min = event_min - 10
                        
                        if timeout_min < 0:
                            timeout_hour -= 1
                            timeout_min += 60
                        
                        if timeout_hour < 0:
                            timeout_hour = 23
                        
                        timeout_time = f"{timeout_hour:02d}:{timeout_min:02d}"
                        file_logger.debug(f"Время таймаута: {timeout_time}")
                        
                        # Если наступило время таймаута
                        file_logger.debug(f"Сравнение: {current_time_str} >= {timeout_time}?")
                        if current_time_str >= timeout_time:
                            file_logger.info(f"⏰ ТАЙМАУТ для мероприятия {event_id} в {event_time_str}")
                            await self.send_timeout_message(event_id, event_date, event_time_str)
                            del self.reminder_sent_time[key]
                            
                except Exception as e:
                    file_logger.error(f"Ошибка обработки таймаута для ключа {key}: {e}")
                    file_logger.error(traceback.format_exc())
                    if key in self.reminder_sent_time:
                        del self.reminder_sent_time[key]
                        
        except Exception as e:
            file_logger.error(f"Ошибка в check_timeouts: {e}")
            file_logger.error(traceback.format_exc())
    
    async def send_reminder(self, event, now):
        """Отправка напоминания во все настроенные каналы"""
        file_logger.debug("="*50)
        file_logger.debug("send_reminder START")
        
        try:
            channel_ids = CONFIG.get('alarm_channels', [])
            if not channel_ids:
                file_logger.error("Каналы напоминаний не настроены")
                return
            
            event_time = event['event_time']
            
            # Время сбора (за 20 минут)
            event_hour, event_min = map(int, event_time.split(':'))
            meeting_hour = event_hour
            meeting_min = event_min - 20
            
            if meeting_min < 0:
                meeting_hour -= 1
                meeting_min += 60
            
            if meeting_hour < 0:
                meeting_hour = 23
            
            meeting_time = f"{meeting_hour:02d}:{meeting_min:02d}"
            
            # Создаём embed
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
            
            # Получаем роли для упоминания
            reminder_roles = CONFIG.get('reminder_roles', [])
            role_mentions = []
            for role_id in reminder_roles:
                role = self.bot.get_guild(int(CONFIG['server_id'])).get_role(int(role_id))
                if role:
                    role_mentions.append(role.mention)
            
            # Отправляем во все каналы
            from events.views import EventReminderView
            sent_count = 0
            
            for channel_id in channel_ids:
                try:
                    channel = self.bot.get_channel(int(channel_id))
                    if not channel:
                        file_logger.warning(f"Канал {channel_id} не найден")
                        continue
                    
                    # Создаём view для каждого канала
                    view = EventReminderView(
                        event_id=event['id'],
                        event_name=event['name'],
                        event_time=event_time,
                        meeting_time=meeting_time,
                        guild=channel.guild,
                        reminder_channels=channel_ids  # Передаём список всех каналов
                    )
                    
                    # Отправляем с упоминанием ролей
                    content = ' '.join(role_mentions) if role_mentions else None
                    message = await channel.send(content=content, embed=embed, view=view)
                    view.add_message(message, channel_id)
                    
                    sent_count += 1
                    file_logger.debug(f"Отправлено в канал {channel_id}")
                    
                except Exception as e:
                    file_logger.error(f"Ошибка отправки в канал {channel_id}: {e}")
            
            if sent_count > 0:
                today = now.date().isoformat()
                db.mark_reminder_sent(event['id'], today)
                db.log_event_action(event['id'], "reminder_sent")
                
                file_logger.info(f"✅ Напоминание отправлено в {sent_count} каналов: {event['name']} в {event_time}")
            
        except Exception as e:
            file_logger.error(f"Ошибка отправки напоминания: {e}")
    
    async def send_timeout_message(self, event_id: int, event_date: str, event_time: str):
        """Сообщение о таймауте"""
        file_logger.debug("="*50)
        file_logger.debug("send_timeout_message START")
        file_logger.debug(f"event_id: {event_id}, event_date: {event_date}, event_time: {event_time}")
        
        try:
            channel_id = CONFIG.get('alarm_channel_id')
            if not channel_id:
                file_logger.error("Канал оповещений не настроен")
                return
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                file_logger.error(f"Канал {channel_id} не найден")
                return
            
            event = db.get_event(event_id)
            if not event:
                file_logger.error(f"Мероприятие {event_id} не найдено")
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
            file_logger.info(f"⏰ Таймаут МП: {event['name']} на {event_date}")
            logger.info(f"⏰ Таймаут МП: {event['name']} на {event_date}")
            
        except Exception as e:
            file_logger.error(f"Ошибка отправки таймаута: {e}")
            file_logger.error(traceback.format_exc())
    
    def cleanup_old_reminders(self):
        """Очистка старых записей"""
        file_logger.debug("cleanup_old_reminders START")
        
        try:
            now = datetime.now(MSK_TZ)
            file_logger.debug(f"Текущая дата: {now.date()}")
            file_logger.debug(f"Записей до очистки: {len(self.reminder_sent_time)}")
            
            for key in list(self.reminder_sent_time.keys()):
                try:
                    event_id, event_date = key
                    date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()
                    days_diff = (now.date() - date_obj).days
                    file_logger.debug(f"Ключ {key}: дней разницы {days_diff}")
                    
                    if days_diff > 7:
                        file_logger.debug(f"Удаляем старую запись: {key}")
                        del self.reminder_sent_time[key]
                except Exception as e:
                    file_logger.error(f"Ошибка обработки ключа {key}: {e}")
                    if key in self.reminder_sent_time:
                        del self.reminder_sent_time[key]
            
            file_logger.debug(f"Записей после очистки: {len(self.reminder_sent_time)}")
            
        except Exception as e:
            file_logger.error(f"Ошибка в cleanup_old_reminders: {e}")
            file_logger.error(traceback.format_exc())

scheduler = None

async def setup(bot):
    global scheduler
    scheduler = EventScheduler(bot)
    await scheduler.start()