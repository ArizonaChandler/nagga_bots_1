"""Инициализация системы создания embed"""
import logging
import discord
from core.database import db
from embed_builder.settings_view import EmbedBuilderSettingsView
from embed_builder.manager import embed_builder_manager

logger = logging.getLogger(__name__)


class EmbedBuilderInitializer:
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        logger.info("🔄 Инициализация системы создания embed...")
        print("📦 [EMBED_BUILDER] Инициализация...")
        
        # Устанавливаем бота в менеджер
        embed_builder_manager.set_bot(self.bot)
        
        self.settings_channel_id = db.get_setting('embed_builder_settings_channel')
        
        if self.settings_channel_id and self.settings_channel_id != 'null':
            await self._init_settings_channel()
        
        logger.info("✅ Инициализация системы создания embed завершена")
        print("📦 [EMBED_BUILDER] Инициализация завершена")
    
    async def _init_settings_channel(self):
        try:
            channel = self.bot.get_channel(int(self.settings_channel_id))
            if not channel:
                logger.error(f"❌ Канал настроек {self.settings_channel_id} не найден")
                return
        except (ValueError, TypeError):
            logger.error(f"❌ Неверный ID канала настроек: {self.settings_channel_id}")
            return
        
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.delete()
        
        embed = discord.Embed(
            title="📦 **СОЗДАНИЕ EMBED**",
            description="Настройка системы создания embed сообщений",
            color=0x00ff00
        )
        await channel.send(embed=embed, view=EmbedBuilderSettingsView())
        print(f"📦 [EMBED_BUILDER] Создана панель настроек в #{channel.name}")
    
    async def stop(self):
        print("📦 [EMBED_BUILDER] Остановка системы")


initializer = None

async def setup(bot):
    global initializer
    initializer = EmbedBuilderInitializer(bot)
    await initializer.initialize_all()
    return initializer