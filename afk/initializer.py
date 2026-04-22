"""Инициализация каналов системы AFK"""
import asyncio
import discord
import logging
from datetime import datetime
from afk.manager import afk_manager
from afk.views import AFKPublicView
from afk.settings_view import AFKSettingsView

logger = logging.getLogger(__name__)


class AFKInitializer:
    """Инициализатор каналов системы AFK"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        """Инициализировать все каналы системы AFK"""
        logger.info("🔄 Инициализация системы AFK...")
        
        settings = afk_manager.get_settings()
        
        # 1. Канал с кнопками AFK
        await self._init_afk_channel(settings)
        
        # 2. Канал настроек
        await self._init_settings_channel()
        
        # 3. Запускаем фоновую проверку просроченных AFK
        await self.start_expiry_checker()
        
        logger.info("✅ Инициализация системы AFK завершена")
    
    async def start_expiry_checker(self):
        """Запустить фоновую задачу для проверки просроченных AFK"""
        self.bot.loop.create_task(self._check_expired_afk())
        logger.info("✅ Запущен автоматический проверщик просроченного AFK")
    
    async def _check_expired_afk(self):
        """Фоновая задача: проверять каждые 60 секунд"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # Проверяем просроченных пользователей
                expired = afk_manager.check_expired()
                
                if expired:
                    logger.info(f"⏰ Найдено просроченных AFK: {len(expired)}")
                    
                    # Обновляем embed в канале AFK
                    settings = afk_manager.get_settings()
                    channel_id = settings.get('afk_channel')
                    if channel_id:
                        from afk.views import update_afk_embed
                        await update_afk_embed(self.bot, channel_id)
                    
                    # Отправляем логи в канал логов
                    log_channel_id = settings.get('afk_log_channel')
                    if log_channel_id:
                        log_channel = self.bot.get_channel(int(log_channel_id))
                        if log_channel:
                            for user_id, user_name in expired:
                                embed = discord.Embed(
                                    title="⏰ AFK ИСТЕКЛО",
                                    description=f"Пользователь **{user_name}** (<@{user_id}>) автоматически вышел из AFK",
                                    color=0xffa500,
                                    timestamp=datetime.now()
                                )
                                await log_channel.send(embed=embed)
                                await asyncio.sleep(0.5)
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в проверке AFK: {e}")
                await asyncio.sleep(60)
    
    async def _init_afk_channel(self, settings):
        """Инициализация канала с кнопками AFK"""
        channel_id = settings.get('afk_channel')
        if not channel_id:
            logger.warning("⚠️ Канал AFK не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал AFK {channel_id} не найден")
            return
        
        from afk.views import AFKPublicView, update_afk_embed
        from datetime import datetime
        import pytz
        
        MSK_TZ = pytz.timezone('Europe/Moscow')
        max_hours = int(settings.get('afk_max_hours', 24))
        
        # Ищем существующее сообщение с кнопками AFK (по наличию кнопок)
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                if msg.components and len(msg.components) > 0:
                    for component in msg.components:
                        for button in component.children:
                            if button.custom_id in ["afk_go", "afk_back"]:
                                await msg.edit(view=AFKPublicView(self.bot, channel_id, max_hours))
                                message_exists = True
                                logger.info(f"✅ Обновлена панель AFK в #{channel.name}")
                                break
                        if message_exists:
                            break
                if message_exists:
                    break
        
        # Если сообщения нет - создаём новое
        if not message_exists:
            embed = discord.Embed(
                title="🛌 **СИСТЕМА AFK**",
                description="✨ **Никого нет в AFK**\n\nНажмите кнопку ниже, чтобы уйти в AFK",
                color=0x2b2d31,
                timestamp=datetime.now(MSK_TZ)
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1302858797087854592.png?size=96")
            embed.set_footer(text="• Статус: Активен •", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
            await channel.send(embed=embed, view=AFKPublicView(self.bot, channel_id, max_hours))
            logger.info(f"✅ Создана панель AFK в #{channel.name}")
        
        # Обновляем embed со списком пользователей (если есть)
        await update_afk_embed(self.bot, channel_id)
    
    async def _init_settings_channel(self):
        """Инициализация канала настроек AFK"""
        from core.config import CONFIG
        channel_id = CONFIG.get('afk_settings_channel')
        
        if not channel_id:
            logger.warning("⚠️ Канал настроек AFK не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек AFK {channel_id} не найден")
            return
        
        # Ищем существующее сообщение
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "⚙️ **НАСТРОЙКИ AFK**" in msg.embeds[0].title:
                    await msg.edit(view=AFKSettingsView())
                    message_exists = True
                    logger.info(f"✅ Обновлена панель настроек AFK в #{channel.name}")
                    break
        
        if not message_exists:
            embed = discord.Embed(
                title="⚙️ **НАСТРОЙКИ AFK**",
                description="Настройка системы ухода в AFK",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=AFKSettingsView())
            logger.info(f"✅ Создана панель настроек AFK в #{channel.name}")


# Глобальный экземпляр
initializer = None

async def setup(bot):
    """Функция для вызова из bot.py"""
    global initializer
    initializer = AFKInitializer(bot)
    await initializer.initialize_all()