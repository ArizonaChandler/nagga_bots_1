"""Инициализация каналов системы статистики"""
import discord
import logging
from server_stats.manager import stats_manager
from server_stats.settings_view import StatsSettingsView

logger = logging.getLogger(__name__)


class StatsInitializer:
    """Инициализатор каналов системы статистики"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        """Инициализировать каналы системы статистики"""
        logger.info("📊 Инициализация системы статистики...")
        
        # Канал настроек
        await self._init_settings_channel()
        
        logger.info("✅ Инициализация системы статистики завершена")
    
    async def _init_settings_channel(self):
        """Инициализация канала настроек статистики"""
        from core.config import CONFIG
        channel_id = CONFIG.get('stats_settings_channel')
        
        if not channel_id:
            logger.warning("⚠️ Канал настроек статистики не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек статистики {channel_id} не найден")
            return
        
        # Ищем существующее сообщение с панелью настроек
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "НАСТРОЙКИ СТАТИСТИКИ" in msg.embeds[0].title:
                    # Обновляем view (кнопки)
                    await msg.edit(view=StatsSettingsView())
                    message_exists = True
                    logger.info(f"✅ Обновлена панель настроек статистики в #{channel.name}")
                    break
        
        # Если сообщения нет - создаём новое
        if not message_exists:
            embed = discord.Embed(
                title="📊 **НАСТРОЙКИ СТАТИСТИКИ**",
                description="Настройка системы статистики сервера",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=StatsSettingsView())
            logger.info(f"✅ Создана панель настроек статистики в #{channel.name}")


# Глобальный экземпляр
initializer = None

async def setup(bot):
    """Функция для вызова из bot.py"""
    global initializer
    initializer = StatsInitializer(bot)
    await initializer.initialize_all()