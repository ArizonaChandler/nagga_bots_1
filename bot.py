#!/usr/bin/env python3
"""
Management System v0.28
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
intents.voice_states = True
intents.message_content = True
intents.guilds = True
intents.emojis = True
intents.reactions = True
intents.typing = False

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


# ========== ЕДИНЫЙ ОБРАБОТЧИК ГОЛОСОВЫХ СОБЫТИЙ ==========
@bot.event
async def on_voice_state_update(member: discord.Member, before, after):
    """Единый обработчик голосовых событий для всех модулей"""
    from core.module_manager import MODULES
    
    # 1. Экономика (начисление баллов за голосовой онлайн)
    if MODULES.get("economy", {}).get("enabled", False):
        from economy.manager import economy_manager
        await economy_manager.process_voice_update(member, before, after)
    
    # 2. Временные комнаты
    if MODULES.get("temp_voice", {}).get("enabled", False):
        from temp_voice.manager import temp_voice_manager
        room = temp_voice_manager.get_user_room(member.id)
        if room:
            channel = member.guild.get_channel(int(room['channel_id']))
            if channel:
                if before.channel == channel and after.channel != channel:
                    await temp_voice_manager.schedule_deletion(channel, member.id)
                elif after.channel == channel and before.channel != channel:
                    await temp_voice_manager.cancel_deletion(channel)
    
    # 3. Логи действий
    if MODULES.get("action_logs", {}).get("enabled", False):
        from action_logs.events import log_voice_state
        await log_voice_state(member, before, after)


# ========== ЛОГИ ДЕЙСТВИЙ (ОБРАБОТЧИКИ) ==========
@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    from core.module_manager import MODULES
    if MODULES.get("action_logs", {}).get("enabled", False):
        from action_logs.events import log_message_edit
        await log_message_edit(before, after)


@bot.event
async def on_message_delete(message: discord.Message):
    from core.module_manager import MODULES
    if MODULES.get("action_logs", {}).get("enabled", False):
        from action_logs.events import log_message_delete
        await log_message_delete(message)


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    from core.module_manager import MODULES
    if MODULES.get("action_logs", {}).get("enabled", False):
        from action_logs.events import log_channel_create
        await log_channel_create(channel)


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    from core.module_manager import MODULES
    if MODULES.get("action_logs", {}).get("enabled", False):
        from action_logs.events import log_channel_delete
        await log_channel_delete(channel)


@bot.event
async def on_guild_channel_update(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
    from core.module_manager import MODULES
    if MODULES.get("action_logs", {}).get("enabled", False):
        from action_logs.events import log_channel_update
        await log_channel_update(before, after)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    from core.module_manager import MODULES
    if MODULES.get("action_logs", {}).get("enabled", False):
        from action_logs.events import log_member_update
        await log_member_update(before, after)


@bot.event
async def on_guild_role_create(role: discord.Role):
    from core.module_manager import MODULES
    if MODULES.get("action_logs", {}).get("enabled", False):
        from action_logs.events import log_role_create
        await log_role_create(role)


@bot.event
async def on_guild_role_delete(role: discord.Role):
    from core.module_manager import MODULES
    if MODULES.get("action_logs", {}).get("enabled", False):
        from action_logs.events import log_role_delete
        await log_role_delete(role)


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