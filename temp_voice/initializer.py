"""Инициализация каналов системы временных комнат"""
import discord
import logging
from core.database import db
from temp_voice.views import TempVoicePublicView
from temp_voice.manager import temp_voice_manager

logger = logging.getLogger(__name__)


class TempVoiceInitializer:
    """Инициализатор системы временных комнат"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def initialize_all(self):
        logger.info("🔄 Инициализация системы временных комнат...")
        print("🎤 [TEMP_VOICE] Инициализация системы...")
        
        temp_voice_manager.set_bot(self.bot)
        
        self.public_channel_id = db.get_setting('temp_voice_public_channel')
        
        await self._init_public_channel()
        await self._restore_rooms()
        
        logger.info("✅ Инициализация системы временных комнат завершена")
        print("🎤 [TEMP_VOICE] Инициализация завершена")
    
    async def _init_public_channel(self):
        if not self.public_channel_id:
            logger.warning("⚠️ Публичный канал временных комнат не настроен")
            return
        
        channel = self.bot.get_channel(int(self.public_channel_id))
        if not channel:
            logger.error(f"❌ Публичный канал {self.public_channel_id} не найден")
            return
        
        found = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.components:
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
                            "└ Управляйте комнатой кнопками ниже\n\n"
                            "**Возможности управления:**\n"
                            "└ Расширить комнату (выберите количество слотов)\n"
                            "└ Кикнуть нежелательного пользователя\n"
                            "└ Закрыть комнату\n\n"
                            "**Важно:** Комната будет автоматически удалена через N секунд после того, как создатель покинет её.",
                color=0x00bfff
            )
            await channel.send(embed=embed, view=TempVoicePublicView())
            print(f"🎤 [TEMP_VOICE] Создана панель в #{channel.name}")
    
    async def _restore_rooms(self):
        print("🎤 [TEMP_VOICE] Проверка комнат после перезапуска...")
        for guild in self.bot.guilds:
            await temp_voice_manager.check_creator_presence(guild)
        print("🎤 [TEMP_VOICE] Проверка комнат завершена")
    
    async def stop(self):
        await temp_voice_manager.stop()
        print("🎤 [TEMP_VOICE] Система остановлена")


initializer = None

async def setup(bot):
    global initializer
    initializer = TempVoiceInitializer(bot)
    await initializer.initialize_all()
    return initializer