"""Инициализация каналов системы AFK"""
import discord
import logging
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
        
        logger.info("✅ Инициализация системы AFK завершена")
    
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
        
        # Ищем существующее сообщение с кнопками AFK
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "СИСТЕМА AFK" in msg.embeds[0].title:
                    # Обновляем view (кнопки)
                    await msg.edit(view=AFKPublicView(self.bot, channel_id))
                    message_exists = True
                    logger.info(f"✅ Обновлена панель AFK в #{channel.name}")
                    break
        
        # Если сообщения нет - создаём новое
        if not message_exists:
            embed = discord.Embed(
                title="🛌 **СИСТЕМА AFK**",
                description="✨ Никого нет в AFK",
                color=0xffa500
            )
            embed.set_footer(text="Нажмите кнопку, чтобы уйти в AFK")
            await channel.send(embed=embed, view=AFKPublicView(self.bot, channel_id))
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
                if msg.embeds and "НАСТРОЙКИ AFK" in msg.embeds[0].title:
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