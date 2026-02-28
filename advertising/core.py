"""Auto Advertising Core - Простая автоматическая рассылка"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
import pytz
import discord
import aiohttp
from core.database import db
from core.config import CONFIG

logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone('Europe/Moscow')

AD_TEXT_FILE = "/home/discordbot/discord-bot/ad_text.txt"
AD_IMAGE_FILE = "/home/discordbot/discord-bot/ad_image.txt"  # новый файл для URL картинки
AD_CHANNEL_FILE = "/home/discordbot/discord-bot/ad_channel.txt"
AD_INTERVAL = 65  # минут

class AutoAdvertiser:
    def __init__(self, bot):
        self.bot = bot
        self.running = True
        self.check_interval = 60
        self.task = None
        self.last_sent_time = None
        
        # Создаем файлы если их нет
        if not os.path.exists(AD_TEXT_FILE):
            with open(AD_TEXT_FILE, 'w', encoding='utf-8') as f:
                f.write("Рекламный текст не установлен")
        
        if not os.path.exists(AD_IMAGE_FILE):
            with open(AD_IMAGE_FILE, 'w', encoding='utf-8') as f:
                f.write("")
        
        if not os.path.exists(AD_CHANNEL_FILE):
            with open(AD_CHANNEL_FILE, 'w', encoding='utf-8') as f:
                f.write("")
        
        print("📢 [AutoAd] Простая авто-реклама инициализирована")
        print(f"📢 [AutoAd] Файл текста: {AD_TEXT_FILE}")
        print(f"📢 [AutoAd] Файл картинки: {AD_IMAGE_FILE}")
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
    
    def get_ad_image(self):
        """Получить URL картинки из файла"""
        try:
            with open(AD_IMAGE_FILE, 'r', encoding='utf-8') as f:
                url = f.read().strip()
                return url if url else None
        except:
            return None
    
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
        
        channel_id = self.get_ad_channel()
        if not channel_id:
            return
        
        if self.last_sent_time:
            next_send = self.last_sent_time + timedelta(minutes=AD_INTERVAL)
            if now < next_send:
                return
        
        await self.send_ad(now)
    
    async def send_ad(self, now):
        try:
            channel_id = self.get_ad_channel()
            if not channel_id:
                logger.error("Канал для рекламы не настроен")
                return
            
            user_token = CONFIG.get('user_token_1')
            if not user_token:
                logger.error("Пользовательский токен не найден в CONFIG")
                return
            
            ad_text = self.get_ad_text()
            image_url = self.get_ad_image()
            
            url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
            headers = {
                "Authorization": user_token,
                "Content-Type": "application/json"
            }
            
            # Формируем данные для отправки
            if image_url:
                # Если есть картинка, отправляем embed
                data = {
                    "embeds": [{
                        "description": ad_text,
                        "color": 0x00ff00,  # зеленый цвет
                        "image": {"url": image_url}
                    }]
                }
            else:
                # Если картинки нет, просто текст
                data = {"content": ad_text}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    if resp.status == 200:
                        self.last_sent_time = now
                        logger.info(f"✅ Реклама отправлена в канал {channel_id}")
                        print(f"✅ Реклама отправлена в канал {channel_id}")
                    else:
                        error_text = await resp.text()
                        logger.error(f"❌ Ошибка отправки рекламы: {resp.status} - {error_text}")
                        print(f"❌ Ошибка отправки: {resp.status}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки рекламы: {e}")
            print(f"❌ Ошибка: {e}")

advertiser = None

async def setup(bot):
    global advertiser
    advertiser = AutoAdvertiser(bot)
    await advertiser.start()