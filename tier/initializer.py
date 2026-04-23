"""Инициализация каналов системы TIR"""
import discord
import logging
from tier.manager import tier_manager
from tier.views import TierInfoView, update_tier_embed
from tier.settings_view import TierSettingsView

logger = logging.getLogger(__name__)


class TierInitializer:
    """Инициализатор каналов системы TIR"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        """Инициализировать все каналы системы TIR"""
        logger.info("🔄 Инициализация системы TIR...")
        
        settings = tier_manager.get_settings()
        
        # 1. Канал с кнопками информации о тирах
        await self._init_info_channel(settings)
        
        # 2. Канал для подачи заявок (только кнопки)
        await self._init_submit_channel(settings)
        
        # 3. Канал настроек
        await self._init_settings_channel()
        
        logger.info("✅ Инициализация системы TIR завершена")
    
    async def _init_info_channel(self, settings):
        """Инициализация канала с информацией о тирах"""
        channel_id = settings.get('tier_info_channel')
        if not channel_id:
            logger.warning("⚠️ Канал информации TIR не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал информации TIR {channel_id} не найден")
            return
        
        # Ищем существующее сообщение
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "🌟 СИСТЕМА TIR" in msg.embeds[0].title:
                    await msg.edit(view=TierInfoView())
                    message_exists = True
                    logger.info(f"✅ Обновлена панель информации TIR в #{channel.name}")
                    break
        
        if not message_exists:
            # Создаём embed с информацией
            tier3_req = tier_manager.get_tier_requirements("tier3") or "Не установлены"
            tier2_req = tier_manager.get_tier_requirements("tier2") or "Не установлены"
            tier1_req = tier_manager.get_tier_requirements("tier1") or "Не установлены"
            
            embed = discord.Embed(
                title="🌟 **СИСТЕМА TIR**",
                description="Повышение уровня в семье",
                color=0xffa500,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="🟤 TIER 3",
                value=f"**Требования:**\n{tier3_req}\n\n**Награда:**\n└ Роль Tier 3",
                inline=False
            )
            
            embed.add_field(
                name="⚪ TIER 2",
                value=f"**Требования:**\n{tier2_req}\n\n**Награда:**\n└ Роль Tier 2\n└ Снятие роли Tier 3",
                inline=False
            )
            
            embed.add_field(
                name="🔴 TIER 1",
                value=f"**Требования:**\n{tier1_req}\n\n**Награда:**\n└ Роль Tier 1\n└ Снятие роли Tier 2",
                inline=False
            )
            
            embed.set_footer(text="Подать заявку можно в канале #заявка-на-tier")
            
            await channel.send(embed=embed, view=TierInfoView())
            logger.info(f"✅ Создана панель информации TIR в #{channel.name}")
        
        # Обновляем embed
        await update_tier_embed(self.bot, channel_id)
    
    async def _init_submit_channel(self, settings):
        """Инициализация канала с кнопкой подачи заявок"""
        channel_id = settings.get('tier_submit_channel')
        if not channel_id:
            logger.warning("⚠️ Канал подачи заявок TIR не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал подачи заявок TIR {channel_id} не найден")
            return
        
        # Ищем существующее сообщение
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "ПОДАЧА ЗАЯВОК НА TIR" in msg.embeds[0].title:
                    message_exists = True
                    logger.info(f"✅ Обновлена панель подачи заявок TIR в #{channel.name}")
                    break
        
        if not message_exists:
            embed = discord.Embed(
                title="🌟 **ПОДАЧА ЗАЯВОК НА TIR**",
                description="Выберите уровень, на который хотите подать заявку:\n\n"
                            "🟤 **Tier 3** — начальный уровень\n"
                            "⚪ **Tier 2** — средний уровень\n"
                            "🔴 **Tier 1** — высший уровень\n\n"
                            "⚠️ Подать заявку можно только на следующий уровень!",
                color=0xffa500
            )
            await channel.send(embed=embed, view=TierInfoView())
            logger.info(f"✅ Создана панель подачи заявок TIR в #{channel.name}")
    
    async def _init_settings_channel(self):
        """Инициализация канала настроек TIR"""
        from core.config import CONFIG
        channel_id = CONFIG.get('tier_settings_channel')
        
        if not channel_id:
            logger.warning("⚠️ Канал настроек TIR не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек TIR {channel_id} не найден")
            return
        
        # Ищем существующее сообщение
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "НАСТРОЙКИ TIR" in msg.embeds[0].title:
                    await msg.edit(view=TierSettingsView())
                    message_exists = True
                    logger.info(f"✅ Обновлена панель настроек TIR в #{channel.name}")
                    break
        
        if not message_exists:
            embed = discord.Embed(
                title="⚙️ **НАСТРОЙКИ TIR**",
                description="Настройка системы повышения уровня",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=TierSettingsView())
            logger.info(f"✅ Создана панель настроек TIR в #{channel.name}")


# Глобальный экземпляр
initializer = None

async def setup(bot):
    """Функция для вызова из bot.py"""
    global initializer
    initializer = TierInitializer(bot)
    await initializer.initialize_all()