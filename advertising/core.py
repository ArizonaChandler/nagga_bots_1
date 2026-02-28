"""Auto Advertising Core - Простая автоматическая рассылка"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
import pytz
import discord
from core.database import db
from core.config import CONFIG

logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone('Europe/Moscow')

AD_TEXT_FILE = "/home/discordbot/discord-bot/ad_text.txt"
AD_CHANNEL_FILE = "/home/discordbot/discord-bot/ad_channel.txt"
AD_INTERVAL = 65  # минут

class AutoAdvertiser:
    def __init__(self, bot):
        self.bot = bot
        self.running = True
        self.check_interval = 60  # проверка каждую минуту
        self.task = None
        self.last_sent_time = None
        
        # Создаем файлы если их нет
        if not os.path.exists(AD_TEXT_FILE):
            with open(AD_TEXT_FILE, 'w', encoding='utf-8') as f:
                f.write("Рекламный текст не установлен")
        
        if not os.path.exists(AD_CHANNEL_FILE):
            with open(AD_CHANNEL_FILE, 'w', encoding='utf-8') as f:
                f.write("")
        
        print("📢 [AutoAd] Простая авто-реклама инициализирована")
        print(f"📢 [AutoAd] Файл текста: {AD_TEXT_FILE}")
        print(f"📢 [AutoAd] Файл канала: {AD_CHANNEL_FILE}")
    
    async def start(self):
        logger.info("📢 Auto Advertiser запущен")
        self.task = asyncio.create_task(self._run())
    
    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            logger.info("📢 Auto Advertiser остановлен")
    
    def get_ad_text(self):
        """Получить текст рекламы из файла"""
        try:
            with open(AD_TEXT_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except:
            return "Рекламный текст не установлен"
    
    def get_ad_channel(self):
        """Получить ID канала из файла"""
        try:
            with open(AD_CHANNEL_FILE, 'r', encoding='utf-8') as f:
                channel_id = f.read().strip()
                return channel_id if channel_id else None
        except:
            return None
    
    async def _run(self):
        while self.running:
            try:
                await self.check_and_send()
            except Exception as e:
                logger.error(f"Ошибка в авто-рекламе: {e}")
            await asyncio.sleep(self.check_interval)
    
    async def check_and_send(self):
        now = datetime.now(MSK_TZ)
        
        # Получаем канал
        channel_id = self.get_ad_channel()
        if not channel_id:
            return
        
        # Проверяем время последней отправки
        if self.last_sent_time:
            next_send = self.last_sent_time + timedelta(minutes=AD_INTERVAL)
            if now < next_send:
                return
        else:
            # Первая отправка - отправляем сразу
            pass
        
        # Отправляем рекламу
        await self.send_ad(now)
    
    async def send_ad(self, now):
        try:
            channel_id = self.get_ad_channel()
            if not channel_id:
                logger.error("Канал для рекламы не настроен")
                return
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Канал {channel_id} не найден")
                return
            
            ad_text = self.get_ad_text()
            
            # Отправляем обычное сообщение (можно добавить embed если нужно)
            await channel.send(ad_text)
            
            self.last_sent_time = now
            logger.info(f"✅ Реклама отправлена в канал {channel_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки рекламы: {e}")

advertiser = None

async def setup(bot):
    global advertiser
    advertiser = AutoAdvertiser(bot)
    await advertiser.start()