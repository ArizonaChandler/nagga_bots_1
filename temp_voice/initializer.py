"""Инициализация каналов системы временных комнат"""
import discord
import logging
from core.database import db
from core.config import CONFIG
from temp_voice.views import TempVoicePublicView
from temp_voice.settings_view import TempVoiceSettingsView
from temp_voice.manager import temp_voice_manager

logger = logging.getLogger(__name__)


class TempVoiceInitializer:
    """Инициализатор системы временных комнат"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        """Инициализировать все каналы системы"""
        logger.info("🔄 Инициализация системы временных комнат...")
        print("🎤 [TEMP_VOICE] Инициализация системы временных комнат...")
        
        # Устанавливаем бота в менеджер
        temp_voice_manager.set_bot(self.bot)
        
        # Загружаем настройки из БД
        self.public_channel_id = db.get_setting('temp_voice_public_channel')
        self.settings_channel_id = db.get_setting('temp_voice_settings_channel')
        
        # 1. Публичный канал с кнопками
        await self._init_public_channel()
        
        # 2. Канал настроек
        await self._init_settings_channel()
        
        # 3. Проверяем создателей комнат после перезапуска
        await self._restore_rooms()
        
        logger.info("✅ Инициализация системы временных комнат завершена")
        print("🎤 [TEMP_VOICE] Инициализация завершена")
    
    async def _init_public_channel(self):
        """Публичный канал с кнопками создания комнат"""
        if not self.public_channel_id:
            logger.warning("⚠️ Публичный канал временных комнат не настроен")
            print("⚠️ [TEMP_VOICE] Публичный канал не настроен")
            return
        
        channel = self.bot.get_channel(int(self.public_channel_id))
        if not channel:
            logger.error(f"❌ Публичный канал {self.public_channel_id} не найден")
            return
        
        # Ищем существующее сообщение с кнопками
        found = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                if msg.components and len(msg.components) > 0:
                    await msg.edit(view=TempVoicePublicView())
                    found = True
                    print(f"🎤 [TEMP_VOICE] Обновлена панель в #{channel.name}")
                    break
        
        if not found:
            embed = discord.Embed(
                title="🎤 **ВРЕМЕННЫЕ ГОЛОСОВЫЕ КОМНАТЫ**",
                description="Создайте свою временную комнату для общения с друзьями!\n\n"
                            "**Как это работает:**\n"
                            "└ Нажмите кнопку «СОЗДАТЬ КОМНАТУ» и введите название\n"
                            "└ Комната появится в голосовом канале\n"
                            "└ Приглашайте друзей — они смогут зайти\n"
                            "└ Управляйте комнатой через кнопку «УПРАВЛЯТЬ»\n\n"
                            "**Возможности управления:**\n"
                            "└ Расширить комнату (+2 слота)\n"
                            "└ Кикнуть нежелательного пользователя\n"
                            "└ Закрыть комнату\n\n"
                            "**Важно:** Комната будет автоматически удалена через 60 секунд после того, как создатель покинет её.",
                color=0x00bfff
            )
            await channel.send(embed=embed, view=TempVoicePublicView())
            print(f"🎤 [TEMP_VOICE] Создана панель в #{channel.name}")
    
    async def _init_settings_channel(self):
        """Канал настроек системы"""
        if not self.settings_channel_id:
            logger.warning("⚠️ Канал настроек временных комнат не настроен")
            return
        
        channel = self.bot.get_channel(int(self.settings_channel_id))
        if not channel:
            logger.error(f"❌ Канал настроек {self.settings_channel_id} не найден")
            return
        
        # Ищем существующую панель
        found = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "ВРЕМЕННЫХ КОМНАТ" in msg.embeds[0].title:
                    await msg.edit(view=TempVoiceSettingsView())
                    found = True
                    print(f"🎤 [TEMP_VOICE] Обновлена панель настроек в #{channel.name}")
                    break
        
        if not found:
            embed = discord.Embed(
                title="⚙️ **УПРАВЛЕНИЕ СИСТЕМОЙ ВРЕМЕННЫХ КОМНАТ**",
                description="Настройка системы временных голосовых комнат",
                color=0x00ff00
            )
            await channel.send(embed=embed, view=TempVoiceSettingsView())
            print(f"🎤 [TEMP_VOICE] Создана панель настроек в #{channel.name}")
    
    async def _restore_rooms(self):
        """Восстановить комнаты после перезапуска"""
        print("🎤 [TEMP_VOICE] Проверка комнат после перезапуска...")
        
        # Устанавливаем бота в менеджер
        temp_voice_manager.set_bot(self.bot)
        
        # Получаем все серверы бота
        for guild in self.bot.guilds:
            await temp_voice_manager.check_creator_presence(guild)
        
        print("🎤 [TEMP_VOICE] Проверка комнат завершена")
    
    async def stop(self):
        """Остановка системы"""
        await temp_voice_manager.stop()
        print("🎤 [TEMP_VOICE] Система остановлена")


initializer = None

async def setup(bot):
    global initializer
    initializer = TempVoiceInitializer(bot)
    await initializer.initialize_all()
    return initializer