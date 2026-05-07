"""Инициализация каналов системы отпусков"""
import asyncio
import discord
import logging
from datetime import datetime, timedelta
import pytz
from vacation.manager import vacation_manager
from vacation.views import VacationPublicView, update_vacation_embed
from vacation.settings_view import VacationSettingsView

logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone('Europe/Moscow')


class VacationInitializer:
    """Инициализатор каналов системы отпусков"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        """Инициализировать все каналы системы отпусков"""
        logger.info("🔄 Инициализация системы отпусков...")
        
        settings = vacation_manager.get_settings()
        
        # 1. Публичный канал с кнопками
        await self._init_public_channel(settings)
        
        # 2. Канал настроек
        await self._init_settings_channel()
        
        # 3. Запускаем проверку просроченных отпусков
        await self.start_expiry_checker()
        
        logger.info("✅ Инициализация системы отпусков завершена")
    
    async def start_expiry_checker(self):
        """Запустить фоновую задачу для проверки просроченных отпусков"""
        self.bot.loop.create_task(self._check_expired_vacations())
        logger.info("✅ Запущен автоматический проверщик просроченных отпусков")
    
    async def _check_expired_vacations(self):
        """Фоновая задача: проверять каждый день в 00:00"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            now = datetime.now(MSK_TZ)
            
            # Вычисляем время до следующей полуночи (00:00 следующего дня)
            tomorrow = now + timedelta(days=1)
            next_midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
            next_midnight = MSK_TZ.localize(next_midnight)
            seconds_to_wait = (next_midnight - now).total_seconds()
            
            if seconds_to_wait > 0:
                await asyncio.sleep(seconds_to_wait)
            
            try:
                expired = vacation_manager.check_expired_vacations()
                
                if expired:
                    logger.info(f"⏰ Найдено просроченных отпусков: {len(expired)}")
                    settings = vacation_manager.get_settings()
                    
                    # Обновляем embed
                    channel_id = settings.get('vacation_public_channel')
                    if channel_id:
                        await update_vacation_embed(self.bot, channel_id)
                    
                    # Отправляем логи и ЛС
                    log_channel_id = settings.get('vacation_log_channel')
                    if log_channel_id:
                        log_channel = self.bot.get_channel(int(log_channel_id))
                        if log_channel:
                            for user_id, user_name in expired:
                                embed = discord.Embed(
                                    title="⏰ ОТПУСК ЗАКОНЧИЛСЯ",
                                    description=f"У пользователя **{user_name}** закончился отпуск",
                                    color=0xffa500,
                                    timestamp=datetime.now(MSK_TZ)
                                )
                                await log_channel.send(embed=embed)
                                
                                # Отправляем ЛС
                                try:
                                    user = await self.bot.fetch_user(int(user_id))
                                    if user:
                                        await user.send("✅ Ваш отпуск закончился! Добро пожалобратно!")
                                except:
                                    pass
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в проверке отпусков: {e}")
                await asyncio.sleep(60)
    
    async def _init_public_channel(self, settings):
        """Инициализация публичного канала с кнопками"""
        channel_id = settings.get('vacation_public_channel')
        if not channel_id:
            logger.warning("⚠️ Публичный канал отпуска не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Публичный канал {channel_id} не найден")
            return
        
        from vacation.views import VacationPublicView, update_vacation_embed
        
        # Ищем существующее сообщение с кнопками
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                # Проверяем, есть ли в сообщении наша кнопка
                if msg.components and len(msg.components) > 0:
                    for component in msg.components:
                        for button in component.children:
                            if button.custom_id in ["vacation_go", "vacation_back"]:
                                # Нашли наше сообщение, обновляем view
                                await msg.edit(view=VacationPublicView())
                                message_exists = True
                                logger.info(f"✅ Обновлена панель отпусков в #{channel.name}")
                                break
                        if message_exists:
                            break
                if message_exists:
                    break
        
        # Если сообщения нет - создаём новое
        if not message_exists:
            embed = discord.Embed(
                title="🏖️ **СИСТЕМА ОТПУСКОВ**",
                description="✨ Никого нет в отпуске",
                color=0x00ff00
            )
            embed.set_footer(text="Нажмите кнопку, чтобы подать заявку")
            await channel.send(embed=embed, view=VacationPublicView())
            logger.info(f"✅ Создана панель отпусков в #{channel.name}")
        
        # Обновляем embed со списком отпускников
        await update_vacation_embed(self.bot, channel_id)
    
    async def _init_settings_channel(self):
        """Инициализация канала настроек отпусков"""
        from core.config import CONFIG
        channel_id = CONFIG.get('vacation_settings_channel')
        
        if not channel_id:
            logger.warning("⚠️ Канал настроек отпусков не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек {channel_id} не найден")
            return
        
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "НАСТРОЙКИ ОТПУСКОВ" in msg.embeds[0].title:
                    await msg.edit(view=VacationSettingsView())
                    message_exists = True
                    logger.info(f"✅ Обновлена панель настроек отпусков в #{channel.name}")
                    break
        
        if not message_exists:
            embed = discord.Embed(
                title="⚙️ **НАСТРОЙКИ ОТПУСКОВ**",
                description="Настройка системы отпусков",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=VacationSettingsView())
            logger.info(f"✅ Создана панель настроек отпусков в #{channel.name}")


# Глобальный экземпляр
initializer = None

async def setup(bot):
    """Функция для вызова из bot.py"""
    global initializer
    initializer = VacationInitializer(bot)
    await initializer.initialize_all()