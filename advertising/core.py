"""Auto Advertising Core - Автоматическая рассылка рекламы"""
import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import discord
from core.database import db
from core.config import CONFIG

logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone('Europe/Moscow')

class AutoAdvertiser:
    def __init__(self, bot):
        self.bot = bot
        self.running = True
        self.check_interval = 60  # Проверка каждую минуту
        self.task = None
        self.ad_settings = None
        self.last_sent_time = None
        
    async def start(self):
        """Запуск автоматической рекламы"""
        logger.info("📢 Auto Advertiser запущен")
        self.task = asyncio.create_task(self._run())
    
    async def stop(self):
        """Остановка"""
        self.running = False
        if self.task:
            self.task.cancel()
            logger.info("📢 Auto Advertiser остановлен")
    
    async def _run(self):
        """Основной цикл"""
        while self.running:
            try:
                await self.check_and_send()
            except Exception as e:
                logger.error(f"Ошибка в авто-рекламе: {e}")
            await asyncio.sleep(self.check_interval)
    
    async def check_and_send(self):
        """Проверка и отправка рекламы"""
        now = datetime.now(MSK_TZ)
        
        # Получаем настройки
        self.ad_settings = db.get_active_ad()
        if not self.ad_settings:
            return
        
        # Проверяем, активна ли реклама
        if not self.ad_settings.get('is_active'):
            return
        
        channel_id = self.ad_settings.get('channel_id')
        if not channel_id:
            logger.error("Канал для рекламы не настроен")
            return
        
        # Проверяем время последней отправки
        last_sent = self.ad_settings.get('last_sent')
        if last_sent:
            # Парсим время последней отправки
            if isinstance(last_sent, str):
                last_sent = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                if last_sent.tzinfo is None:
                    last_sent = MSK_TZ.localize(last_sent)
            
            # Вычисляем, когда можно отправлять следующую
            interval = self.ad_settings.get('interval_minutes', 65)
            next_send = last_sent + timedelta(minutes=interval)
            
            # Если ещё не время - пропускаем
            if now < next_send:
                return
        else:
            # Никогда не отправляли - можно отправлять сейчас
            pass
        
        # Проверяем, не в спящем ли мы режиме
        sleep_start = self.ad_settings.get('sleep_start', '02:00')
        sleep_end = self.ad_settings.get('sleep_end', '06:30')
        
        current_time = now.strftime("%H:%M")
        
        # Проверяем, находимся ли в периоде сна
        if self._is_sleep_time(current_time, sleep_start, sleep_end):
            logger.debug(f"Спящий режим {sleep_start}-{sleep_end}, пропускаем")
            return
        
        # Отправляем рекламу
        await self.send_ad(now)
    
    def _is_sleep_time(self, current: str, start: str, end: str) -> bool:
        """Проверка, находится ли текущее время в периоде сна"""
        # Преобразуем в минуты для удобства сравнения
        def to_minutes(time_str):
            h, m = map(int, time_str.split(':'))
            return h * 60 + m
        
        current_min = to_minutes(current)
        start_min = to_minutes(start)
        end_min = to_minutes(end)
        
        if start_min < end_min:
            # Обычный случай: 02:00 - 06:30
            return start_min <= current_min < end_min
        else:
            # Ночной случай: 23:00 - 04:00 (переход через полночь)
            return current_min >= start_min or current_min < end_min
    
    async def send_ad(self, now):
        """Отправка рекламного сообщения"""
        try:
            settings = self.ad_settings
            channel_id = settings.get('channel_id')
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Канал {channel_id} не найден")
                db.log_ad_sent(False, f"Канал {channel_id} не найден")
                return
            
            # Формируем сообщение
            message_text = settings.get('message_text', '')
            image_url = settings.get('image_url')
            
            # Создаём embed или обычное сообщение
            if image_url:
                embed = discord.Embed(description=message_text, color=0x00ff00)
                embed.set_image(url=image_url)
                await channel.send(embed=embed)
            else:
                await channel.send(message_text)
            
            # Обновляем время последней отправки
            db.update_last_sent(settings['id'])
            db.log_ad_sent(True)
            
            logger.info(f"✅ Реклама отправлена в канал {channel_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки рекламы: {e}")
            db.log_ad_sent(False, str(e))

advertiser = None

async def setup(bot):
    global advertiser
    advertiser = AutoAdvertiser(bot)
    await advertiser.start()