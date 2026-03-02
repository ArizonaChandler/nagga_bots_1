"""Auto Advertising Core - Простая автоматическая рассылка"""
import asyncio
import logging
import os
import traceback
from datetime import datetime, timedelta
import pytz
import discord
import aiohttp
from core.database import db
from core.config import CONFIG
import json

logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone('Europe/Moscow')

AD_TEXT_FILE = "/home/discordbot/discord-bot/ad_text.txt"
AD_IMAGE_FILE = "/home/discordbot/discord-bot/ad_image.txt"
AD_CHANNEL_FILE = "/home/discordbot/discord-bot/ad_channel.txt"
AD_INTERVAL = 65  # минут

class AutoAdvertiser:
    def __init__(self, bot):
        self.bot = bot
        self.running = True
        self.check_interval = 60
        self.task = None
        self.last_sent_time = None
        self.super_admin_id = CONFIG.get('super_admin_id')
        
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
        await self.initialize_settings_channel(self.bot
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
        except Exception as e:
            print(f"❌ Ошибка чтения файла текста: {e}")
            return "Рекламный текст не установлен"
    
    def get_ad_image(self):
        """Получить URL картинки из файла"""
        try:
            with open(AD_IMAGE_FILE, 'r', encoding='utf-8') as f:
                url = f.read().strip()
                return url if url else None
        except Exception as e:
            print(f"❌ Ошибка чтения файла картинки: {e}")
            return None
    
    def get_ad_channel(self):
        """Получить ID канала из файла"""
        try:
            with open(AD_CHANNEL_FILE, 'r', encoding='utf-8') as f:
                channel_id = f.read().strip()
                return channel_id if channel_id else None
        except Exception as e:
            print(f"❌ Ошибка чтения файла канала: {e}")
            return None
    
    async def notify_admin(self, message):
        """Отправить уведомление супер-админу в ЛС"""
        """if self.super_admin_id:
            try:
                user = await self.bot.fetch_user(int(self.super_admin_id))
                if user:
                    await user.send(f"📢 [AutoAd] {message}")
            except:
                pass"""
        pass
    
    async def _run(self):
        while self.running:
            try:
                await self.check_and_send()
            except Exception as e:
                error_msg = f"Ошибка в авто-рекламе: {e}\n{traceback.format_exc()}"
                logger.error(error_msg)
                print(f"❌ {error_msg}")
                await self.notify_admin(f"❌ Ошибка: {e}")
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
                error_msg = "Канал для рекламы не настроен"
                logger.error(error_msg)
                print(f"❌ {error_msg}")
                await self.notify_admin(f"❌ {error_msg}")
                return
            
            user_token = CONFIG.get('user_token_1')
            if not user_token:
                error_msg = "Пользовательский токен не найден в CONFIG"
                logger.error(error_msg)
                print(f"❌ {error_msg}")
                await self.notify_admin(f"❌ {error_msg}")
                return
            
            ad_text = self.get_ad_text()
            image_url = self.get_ad_image()
            
            print(f"📤 Отправка рекламы в канал {channel_id}")
            print(f"📝 Текст: {ad_text[:50]}...")
            if image_url:
                print(f"🖼️ Картинка: {image_url}")
            
            url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
            headers = {
                "Authorization": user_token,
                "Content-Type": "application/json"
            }
            
            # Формируем данные для отправки
            if image_url:
                data = {
                    "embeds": [{
                        "description": ad_text,
                        "color": 0x00ff00,
                        "image": {"url": image_url}
                    }]
                }
            else:
                data = {"content": ad_text}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    response_text = await resp.text()
                    
                    if resp.status == 200:
                        self.last_sent_time = now
                        success_msg = f"✅ Реклама отправлена в канал {channel_id}"
                        logger.info(success_msg)
                        print(f"✅ {success_msg}")
                        await self.notify_admin(f"✅ Реклама отправлена")
                        
                    elif resp.status == 429:
                        # ⏰ ПОПАЛИ В МЕДЛЕННЫЙ РЕЖИМ!
                        retry_after = 60  # значение по умолчанию
                        
                        # Пробуем получить время ожидания из заголовка
                        if 'Retry-After' in resp.headers:
                            try:
                                retry_after = int(resp.headers['Retry-After'])
                            except:
                                pass
                        
                        # Пробуем получить из JSON
                        try:
                            data = json.loads(response_text)
                            if 'retry_after' in data:
                                retry_after = data['retry_after']
                        except:
                            pass
                        
                        error_msg = f"⏳ Канал в медленном режиме! Нужно подождать {retry_after} сек."
                        logger.error(f"429: {error_msg}")
                        print(f"❌ {error_msg}")
                        
                        # Декодируем сообщение об ошибке
                        try:
                            error_data = json.loads(response_text)
                            discord_msg = error_data.get('message', 'Неизвестная ошибка')
                            print(f"📢 Discord: {discord_msg}")
                        except:
                            pass
                        
                        await self.notify_admin(f"❌ Медленный режим: подожди {retry_after} сек.")
                        
                    else:
                        error_msg = f"❌ Ошибка отправки рекламы: {resp.status}"
                        logger.error(f"{error_msg}\n{response_text}")
                        print(f"❌ {error_msg}")
                        print(f"📢 Ответ: {response_text}")
                        await self.notify_admin(f"❌ Ошибка {resp.status}")
            
        except Exception as e:
            error_msg = f"Ошибка отправки рекламы: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            print(f"❌ {error_msg}")
            await self.notify_admin(f"❌ Ошибка: {e}")
        
    async def initialize_settings_channel(self, bot):
        """Инициализация канала настроек авто-рекламы"""
        settings_channel_id = CONFIG.get('ad_settings_channel')
        if not settings_channel_id:
            return
        
        try:
            channel = bot.get_channel(int(settings_channel_id))
            if not channel:
                logger.error(f"❌ Канал настроек авто-рекламы {settings_channel_id} не найден")
                return
            
            from advertising.settings_view import AdSettingsView
            
            # Очищаем старые сообщения бота
            async for msg in channel.history(limit=20):
                if msg.author == bot.user:
                    await msg.delete()
            
            # Отправляем новое сообщение с кнопками
            embed = discord.Embed(
                title="📢 **ПАНЕЛЬ УПРАВЛЕНИЯ АВТО-РЕКЛАМОЙ**",
                description="Настройка параметров автоматической рекламы",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=AdSettingsView())
            logger.info(f"✅ Канал настроек авто-рекламы инициализирован: #{channel.name}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации канала настроек: {e}")

advertiser = None

async def setup(bot):
    global advertiser
    advertiser = AutoAdvertiser(bot)
    await advertiser.start()