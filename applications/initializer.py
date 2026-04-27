"""Инициализация каналов системы заявок"""
import discord
import logging
from applications.manager import app_manager
from applications.views import ApplicationPublicView
from applications.settings_view import ApplicationsCombinedPanel

logger = logging.getLogger(__name__)


async def update_submit_channel(bot):
    """Обновить сообщение в канале подачи заявок"""
    settings = app_manager.get_settings()
    channel_id = settings.get('submit_channel')
    
    if not channel_id:
        return
    
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    
    # Получаем настройки
    submit_text = settings.get('submit_text') or "Нажмите кнопку ниже, чтобы подать заявку"
    submit_image = settings.get('submit_image')
    
    # Создаём embed
    embed = discord.Embed(
        title="📝 ПОДАЧА ЗАЯВОК В СЕМЬЮ",
        description=submit_text,
        color=0x00ff00
    )
    
    if submit_image:
        embed.set_image(url=submit_image)
    
    # Ищем существующее сообщение бота
    target_message = None
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.embeds:
            target_message = msg
            break
    
    if target_message:
        await target_message.edit(embed=embed, view=ApplicationPublicView())
    else:
        await channel.send(embed=embed, view=ApplicationPublicView())


class ApplicationsInitializer:
    """Инициализатор каналов системы заявок"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        """Инициализировать все каналы системы заявок"""
        logger.info("🔄 Инициализация системы заявок...")
        
        settings = app_manager.get_settings()
        
        # 1. Канал подачи заявок (только кнопка)
        await self._init_submit_channel(settings)
        
        # 2. Канал для анкет (только проверяем наличие)
        await self._init_applications_channel(settings)
        
        # 3. Канал логов (только проверяем наличие)
        await self._init_log_channel(settings)
        
        # 4. Канал настроек (панель управления)
        await self._init_settings_channel()
        
        # 5. Восстанавливаем кнопки у активных заявок
        await self._restore_application_buttons()
        
        logger.info("✅ Инициализация системы заявок завершена")
    
    async def _init_submit_channel(self, settings):
        """Инициализация канала с кнопкой подачи заявок"""
        channel_id = settings.get('submit_channel')
        if not channel_id:
            logger.warning("⚠️ Канал подачи заявок не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал подачи заявок {channel_id} не найден")
            return
        
        # Обновляем или создаём сообщение
        await update_submit_channel(self.bot)
    
    async def _init_applications_channel(self, settings):
        """Проверка канала для анкет"""
        channel_id = settings.get('applications_channel')
        if not channel_id:
            logger.warning("⚠️ Канал для анкет не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал для анкет {channel_id} не найден")
            return
        
        logger.info(f"✅ Канал для анкет: #{channel.name}")
    
    async def _init_log_channel(self, settings):
        """Проверка канала для логов"""
        channel_id = settings.get('applications_log_channel')
        if not channel_id:
            logger.warning("⚠️ Канал логов не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал логов {channel_id} не найден")
            return
        
        logger.info(f"✅ Канал логов: #{channel.name}")
    
    async def _init_settings_channel(self):
        """Инициализация канала настроек"""
        from core.config import CONFIG
        channel_id = CONFIG.get('applications_settings_channel')
        
        if not channel_id:
            logger.warning("⚠️ Канал настроек заявок не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек {channel_id} не найден")
            return
        
        # Ищем существующее сообщение с панелью управления
        message_exists = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "УПРАВЛЕНИЕ И МОДЕРАЦИЯ ЗАЯВОК" in msg.embeds[0].title:
                    await msg.edit(view=ApplicationsCombinedPanel())
                    message_exists = True
                    logger.info(f"✅ Обновлена панель управления в #{channel.name}")
                    break
        
        if not message_exists:
            embed = discord.Embed(
                title="📋 **УПРАВЛЕНИЕ И МОДЕРАЦИЯ ЗАЯВОК**",
                description="Настройка системы и управление заявками",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=ApplicationsCombinedPanel())
            logger.info(f"✅ Создана панель управления в #{channel.name}")
    
    async def _restore_application_buttons(self):
        """Восстановить кнопки у всех активных заявок"""
        from applications.views import ApplicationModerationView
        
        print("🔄 Восстановление кнопок заявок...")
        
        messages = app_manager.get_all_application_messages()
        
        if not messages:
            print("📭 Нет активных заявок для восстановления")
            return
        
        restored = 0
        for msg_data in messages:
            try:
                channel = self.bot.get_channel(int(msg_data['channel_id']))
                if not channel:
                    print(f"❌ Канал {msg_data['channel_id']} не найден")
                    continue
                
                try:
                    message = await channel.fetch_message(int(msg_data['message_id']))
                except discord.NotFound:
                    print(f"❌ Сообщение {msg_data['message_id']} не найдено")
                    app_manager.delete_application_message(msg_data['application_id'])
                    continue
                
                # Восстанавливаем view
                view = ApplicationModerationView(
                    msg_data['application_id'], 
                    msg_data['applicant_id']
                )
                
                await message.edit(view=view)
                restored += 1
                print(f"✅ Восстановлена заявка {msg_data['application_id']} от {msg_data.get('nickname', 'Unknown')} в #{channel.name}")
                
            except Exception as e:
                print(f"❌ Ошибка восстановления заявки {msg_data['application_id']}: {e}")
        
        print(f"✅ Восстановлено {restored} заявок")


# Глобальный экземпляр
initializer = None

async def setup(bot):
    """Функция для вызова из bot.py"""
    global initializer
    initializer = ApplicationsInitializer(bot)
    await initializer.initialize_all()