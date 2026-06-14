#!/usr/bin/env python3
"""
Management System v0.27
Модульная архитектура с системой автоматических оповещений
"""
import asyncio
import sys
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

from core.database import db
from core.config import CONFIG, load_config
from core.utils import format_mention, is_admin
from tier.manager import tier_manager
from vacation.manager import vacation_manager

# ========== КОМАНДЫ ==========
from commands.info import setup as setup_info
from commands.settings import setup as setup_settings
from commands.log import setup as setup_log

# ========== МОДУЛИ ==========
from files.core import file_manager
from events.scheduler import setup as setup_scheduler
from core.module_manager import setup as setup_modules

# ========== НАСТРОЙКА ==========
load_dotenv()
load_config()

BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ DISCORD_BOT_TOKEN не найден в .env")
    exit(1)

# ========== ИНТЕНТЫ ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True  # ← КЛЮЧЕВОЙ ИНТЕНТ ДЛЯ ВОЙСА

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None
)

# ========== РЕГИСТРАЦИЯ КОМАНД ==========
setup_info(bot)
setup_settings(bot)
setup_log(bot)


# ========== СОБЫТИЯ ==========
@bot.event
async def on_ready():
    print("\n" + "=" * 60)
    print("✅ **MAJESTIC BOT by Nagga**")
    print("=" * 60)
    print(f"🤖 Бот: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🌐 Серверов: {len(bot.guilds)}")
    print(f"📁 Файловое хранилище: {file_manager.storage_path}")

    # Проверка интентов
    print(f"🎤 [DEBUG] voice_states intent: {bot.intents.voice_states}")

    # Регистрация persistent view для временных комнат
    try:
        from temp_voice.views import TempVoicePublicView
        bot.add_view(TempVoicePublicView())
        print("✅ Зарегистрирован persistent view для временных комнат")
    except Exception as e:
        print(f"❌ Ошибка регистрации view: {e}")

    # Инициализация системы модулей
    try:
        print("🎛️ Инициализация системы модулей...")
        await setup_modules(bot)
    except Exception as e:
        print(f"❌ Ошибка инициализации модулей: {e}")
        traceback.print_exc()

    # Создаём единую панель настроек (если канал настроен)
    try:
        from core.module_manager import module_manager
        if module_manager:
            await module_manager.update_settings_panel()
    except Exception as e:
        print(f"❌ Ошибка создания панели настроек: {e}")

    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{CONFIG.get('family_name', 'Семья')} | !info"
    ))

    print("=" * 60 + "\n")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"❌ Ошибка: {error}")


@bot.event
async def on_member_join(member):
    try:
        from applications.manager import app_manager
        
        settings = app_manager.get_settings()
        welcome_message = settings.get('welcome_message')
        
        if not welcome_message:
            return
        
        welcome_channel_id = settings.get('welcome_channel')
        if not welcome_channel_id:
            return
        
        welcome_channel = member.guild.get_channel(int(welcome_channel_id))
        if not welcome_channel:
            return
        
        submit_channel_id = settings.get('submit_channel')
        submit_channel_mention = f"<#{submit_channel_id}>" if submit_channel_id else "канал подачи заявок"
        
        welcome_text = welcome_message.format(
            user=member.mention,
            channel=submit_channel_mention,
            server=member.guild.name
        )
        
        welcome_image = settings.get('welcome_image')
        
        embed = discord.Embed(
            title="👋 ДОБРО ПОЖАЛОВАТЬ!",
            description=welcome_text,
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        if welcome_image:
            embed.set_image(url=welcome_image)
        
        embed.set_footer(text=member.guild.name)
        
        await welcome_channel.send(content=member.mention, embed=embed)
        print(f"✅ Приветствие отправлено для {member.name} в #{welcome_channel.name}")
        
    except Exception as e:
        print(f"❌ Ошибка при приветствии {member.name}: {e}")


@bot.event
async def on_member_remove(member):
    try:
        # Закрытие заявок
        application_id = db.get_active_application_id(str(member.id))
        
        if application_id:
            db.close_application_on_leave(application_id)
            print(f"✅ Заявка #{application_id} закрыта")

        # Удаление каналов обзвона
        for category in member.guild.categories:
            if category.name == "📞 ОБЗВОНЫ":
                for channel in category.text_channels:
                    if channel.topic and (f"#{application_id}" in channel.topic or str(member.id) in channel.topic):
                        await channel.delete()
                        print(f"✅ Удалён канал обзвона {channel.name}")

        # Удаление профиля
        for category in member.guild.categories:
            if category.name.startswith("📁 PROFILES"):
                for channel in category.text_channels:
                    if channel.topic and str(member.id) in channel.topic:
                        await channel.delete()
                        print(f"✅ Удалён профиль {member.name}")
                        break

        # Очистка отпусков
        try:
            from vacation.manager import vacation_manager
            vacation = vacation_manager.get_user_vacation(str(member.id))
            if vacation:
                vacation_manager.remove_user_from_vacation(str(member.id))
                print(f"✅ {member.name} удалён из системы отпусков")
                
                log_channel_id = db.get_setting('vacation_log_channel')
                if log_channel_id:
                    log_channel = bot.get_channel(int(log_channel_id))
                    if log_channel:
                        embed = discord.Embed(
                            title="👋 УДАЛЁН ИЗ ОТПУСКА",
                            description=f"Пользователь **{member.name}** покинул сервер",
                            color=0x808080,
                            timestamp=datetime.now()
                        )
                        await log_channel.send(embed=embed)
        except Exception as e:
            print(f"❌ Ошибка удаления из отпуска: {e}")

        # Очистка дней рождения
        db.remove_birthday(str(member.id))
        print(f"🗑️ [Birthday] {member.name} удалён из системы дней рождения")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        traceback.print_exc()


@bot.event
async def on_voice_state_update(member: discord.Member, before, after):
    """ТЕСТОВЫЙ ОБРАБОТЧИК — ПРОВЕРЯЕМ, ВЫЗЫВАЕТСЯ ЛИ СОБЫТИЕ"""
    print(f"🔊🔊🔊 [VOICE_TEST] {member.name} | Before: {before.channel.name if before.channel else 'None'} | After: {after.channel.name if after.channel else 'None'}")
    
    from core.module_manager import MODULES
    
    # Проверяем, включён ли модуль temp_voice
    if not MODULES.get("temp_voice", {}).get("enabled", False):
        print(f"🎤 [DEBUG] temp_voice выключен, пропускаем")
        return
    
    from temp_voice.manager import temp_voice_manager
    
    # Проверяем, есть ли у пользователя комната
    room = temp_voice_manager.get_user_room(member.id)
    if not room:
        print(f"🎤 [DEBUG] У {member.name} нет комнаты")
        return
    
    channel = member.guild.get_channel(int(room['channel_id']))
    if not channel:
        print(f"🎤 [DEBUG] Комната {room['channel_id']} не найдена")
        return
    
    print(f"🎤 [DEBUG] Комната найдена: {channel.name}")
    
    # Создатель вышел из комнаты
    if before.channel == channel and after.channel != channel:
        print(f"🎤 [DEBUG] Создатель {member.name} ВЫШЕЛ из комнаты, запускаем таймер")
        await temp_voice_manager.schedule_deletion(channel, member.id)
    
    # Создатель вернулся в комнату
    elif after.channel == channel and before.channel != channel:
        print(f"🎤 [DEBUG] Создатель {member.name} ВЕРНУЛСЯ в комнату, отменяем таймер")
        await temp_voice_manager.cancel_deletion(channel)


# ========== ЗАПУСК ==========
async def main():
    async with bot:
        await setup_scheduler(bot)
        await bot.start(BOT_TOKEN)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")