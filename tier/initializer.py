"""Инициализация каналов системы TIER"""
import discord
import logging
from datetime import datetime
from tier.manager import tier_manager
from tier.views import TierSubmitView, update_tier_embed
from tier.settings_view import TierSettingsView

logger = logging.getLogger(__name__)


class TierInitializer:
    """Инициализатор каналов системы TIER"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        """Инициализировать все каналы системы TIER"""
        logger.info("🔄 Инициализация системы TIER...")
        
        settings = tier_manager.get_settings()
        
        # 1. Канал с информацией о тирах (только embed, без кнопок)
        await self._init_info_channel(settings)
        
        # 2. Канал для подачи заявок (только одна кнопка)
        await self._init_submit_channel(settings)
        
        # 3. Канал настроек
        await self._init_settings_channel()
        
        logger.info("✅ Инициализация системы TIER завершена")
    
    async def _init_info_channel(self, settings):
        """Инициализация канала с информацией о тирах (только embed)"""
        channel_id = settings.get('tier_info_channel')
        if not channel_id:
            logger.warning("⚠️ Канал информации TIER не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал информации TIER {channel_id} не найден")
            return
        
        # Очищаем старые сообщения бота в этом канале
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.delete()
        
        # Отправляем только embed (без кнопок)
        await update_tier_embed(self.bot, channel_id)
        logger.info(f"✅ Создан embed информации TIER в #{channel.name}")
    
    async def _init_submit_channel(self, settings):
        """Инициализация канала с кнопкой подачи заявок (одна кнопка)"""
        channel_id = settings.get('tier_submit_channel')
        if not channel_id:
            logger.warning("⚠️ Канал подачи заявок TIER не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал подачи заявок TIER {channel_id} не найден")
            return
        
        from tier.views import TierSubmitView
        
        # Ищем существующее сообщение
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "ПОДАЧА ЗАЯВОК НА TIER" in msg.embeds[0].title:
                    await msg.edit(view=TierSubmitView())
                    message_exists = True
                    logger.info(f"✅ Обновлена панель подачи заявок TIER в #{channel.name}")
                    break
        
        if not message_exists:
            # Ссылка на канал с информацией
            info_channel_id = settings.get('tier_info_channel')
            info_channel_mention = f"<#{info_channel_id}>" if info_channel_id else "#tier-info"
            
            embed = discord.Embed(
                title="🌟 **ПОДАЧА ЗАЯВОК НА TIER**",
                description=f"Перед подачей заявки ознакомьтесь с требованиями в канале {info_channel_mention}\n\n"
                            f"**Как это работает:**\n"
                            f"└ Система автоматически определит ваш текущий уровень\n"
                            f"└ Вы подаёте заявку на следующий уровень\n"
                            f"└ Заявку рассмотрит Tier Checker\n\n"
                            f"**Уровни:**\n"
                            f"└ 🟤 **Tier 3** → начальный уровень\n"
                            f"└ ⚪ **Tier 2** → средний уровень\n"
                            f"└ 🔴 **Tier 1** → высший уровень",
                color=0xffa500
            )
            await channel.send(embed=embed, view=TierSubmitView())
            logger.info(f"✅ Создана панель подачи заявок TIER в #{channel.name}")
    
    async def _init_settings_channel(self):
        """Инициализация канала настроек TIER"""
        from core.config import CONFIG
        channel_id = CONFIG.get('tier_settings_channel')
        
        if not channel_id:
            logger.warning("⚠️ Канал настроек TIER не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек TIER {channel_id} не найден")
            return
        
        from tier.settings_view import TierSettingsView
        
        # Ищем существующее сообщение
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "НАСТРОЙКИ TIER" in msg.embeds[0].title:
                    await msg.edit(view=TierSettingsView())
                    message_exists = True
                    logger.info(f"✅ Обновлена панель настроек TIER в #{channel.name}")
                    break
        
        if not message_exists:
            embed = discord.Embed(
                title="⚙️ **НАСТРОЙКИ TIER**",
                description="Настройка системы повышения уровня",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=TierSettingsView())
            logger.info(f"✅ Создана панель настроек TIER в #{channel.name}")


# Глобальный экземпляр
initializer = None

async def setup(bot):
    """Функция для вызова из bot.py"""
    global initializer
    initializer = TierInitializer(bot)
    await initializer.initialize_all()