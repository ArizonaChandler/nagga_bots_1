#!/usr/bin/env python3
"""
Unit Management System v1.3
Модульная архитектура с системой автоматических оповещений
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.database import db
from core.config import CONFIG, load_config
from core.utils import format_mention, is_admin

from commands.info import setup as setup_info
from commands.settings import setup as setup_settings
from commands.log import setup as setup_log
from commands.stats import setup as setup_stats

# ВНИМАНИЕ: Импорт capt.core УДАЛЕН! CAPT перенесена в capt_registration
from files.core import file_manager

# Импорт планировщика мероприятий
from events.scheduler import setup as setup_scheduler

# Импорт авто-рекламы
from advertising.core import setup as setup_advertising
from advertising.commands import setup as setup_ad_commands

# Импорт систем заявок
from applications.manager import app_manager
from applications.views import ApplicationPublicView
from applications.admin_views import ApplicationsModerationPanel

# Импорт системы AFK
from afk import setup_afk

# Импорт системы TIER 
from tier import setup_tier

# Импорт системы статистики
from server_stats import setup_stats, setup_stats_collector


import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ DISCORD_BOT_TOKEN не найден в .env")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None
)

# Настройка команд
setup_info(bot)
setup_settings(bot)
setup_log(bot)
setup_stats(bot)

# Настройка команд авто-рекламы
setup_ad_commands(bot)

# Запуск планировщика мероприятий
setup_scheduler(bot)

@bot.event
async def on_ready():
    print("\n" + "="*60)
    print("✅ **MAJESTIC BOT by Nagga**")
    print("="*60)
    print(f"🤖 Бот: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🌐 Серверов: {len(bot.guilds)}")
    print(f"📁 Файловое хранилище: {file_manager.storage_path}")
    
    # Принудительно загружаем все каналы
    print("🔍 Загрузка каналов...")
    for guild in bot.guilds:
        print(f"  ├─ {guild.name} (ID: {guild.id})")
        for channel in guild.channels:
            print(f"  │  └─ #{channel.name} (ID: {channel.id})")
    
    # Инициализация CAPT регистрации
    try:
        from capt_registration.manager import capt_reg_manager
        print("🔄 Инициализация CAPT регистрации...")
        await capt_reg_manager.initialize_buttons(bot)
    except Exception as e:
        print(f"❌ Ошибка инициализации CAPT регистрации: {e}")
        traceback.print_exc()
    
    # Инициализация канала авто-рекламы
    try:
        from advertising.core import advertiser
        print("🔄 Инициализация канала авто-рекламы...")
        if advertiser:
            await advertiser.initialize_settings_channel(bot)
    except Exception as e:
        print(f"❌ Ошибка инициализации авто-рекламы: {e}")
        traceback.print_exc()
    
    # Инициализация канала мероприятий
    try:
        from events.scheduler import scheduler
        print("🔄 Инициализация канала мероприятий...")
        if scheduler:
            await scheduler.initialize_settings_channel(bot)
    except Exception as e:
        print(f"❌ Ошибка инициализации мероприятий: {e}")
        traceback.print_exc()

    # Инициализация системы заявок
    try:
        from applications import setup_applications
        print("🔄 Инициализация системы заявок...")
        await setup_applications(bot)
    except Exception as e:
        print(f"❌ Ошибка инициализации системы заявок: {e}")
        traceback.print_exc()
    
    # Инициализация системы TIER
    try:
        from tier import setup_tier
        print("🔄 Инициализация системы TIER...")
        await setup_tier(bot)
    except Exception as e:
        print(f"❌ Ошибка инициализации TIER: {e}")
        traceback.print_exc()
    
    # Инициализация системы AFK
    try:
        from afk import setup_afk
        print("🔄 Инициализация системы AFK...")
        await setup_afk(bot)
    except Exception as e:
        print(f"❌ Ошибка инициализации AFK: {e}")
        traceback.print_exc()
    
    # Инициализация канала настроек статистики
    try:
        print("📊 Инициализация панели настроек статистики...")
        await setup_stats(bot)
    except Exception as e:
        print(f"❌ Ошибка инициализации панели статистики: {e}")
        traceback.print_exc()
    
    # Инициализация сборщика статистики (фоновые задачи)
    try:
        print("📊 Инициализация сборщика статистики...")
        await setup_stats_collector(bot)
    except Exception as e:
        print(f"❌ Ошибка инициализации сборщика статистики: {e}")
        traceback.print_exc()
    
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{CONFIG.get('family_name', 'Семья')} | !info"
    ))

    print("="*60 + "\n")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"❌ Ошибка: {error}")

@bot.event
async def on_member_join(member):
    """Приветствие нового участника"""
    # В систему статистики
    if collector:
        collector.increment_new_members()

    try:
        from applications.manager import app_manager
        from core.config import CONFIG
        
        settings = app_manager.get_settings()
        welcome_message = settings.get('welcome_message')
        
        if not welcome_message:
            return
        
        # Используем отдельный канал для приветствий
        welcome_channel_id = settings.get('welcome_channel')
        if not welcome_channel_id:
            # Если канал не настроен, не отправляем
            return
        
        welcome_channel = member.guild.get_channel(int(welcome_channel_id))
        if not welcome_channel:
            return
        
        # Получаем канал подачи заявок для ссылки
        submit_channel_id = settings.get('submit_channel')
        submit_channel_mention = f"<#{submit_channel_id}>" if submit_channel_id else "канал подачи заявок"
        
        # Заменяем переменные в сообщении
        welcome_text = welcome_message.format(
            user=member.mention,
            channel=submit_channel_mention,
            server=member.guild.name
        )
        
        # Получаем картинку
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
        
        # Отправляем в канал приветствий
        await welcome_channel.send(content=member.mention, embed=embed)
        print(f"✅ Приветствие отправлено для {member.name} в #{welcome_channel.name}")
        
    except Exception as e:
        print(f"❌ Ошибка при приветствии {member.name}: {e}")

@bot.event
async def on_member_remove(member):
    
    # В систему статистики
    if collector:
        collector.increment_left_members()

    """При выходе пользователя удаляем его личный профиль и каналы обзвона"""
    try:
        # 1. Удаляем профиль (категория PROFILES)
        for category in member.guild.categories:
            if category.name.startswith("📁 PROFILES"):
                for channel in category.text_channels:
                    if channel.topic and str(member.id) in channel.topic:
                        await channel.delete()
                        print(f"✅ Удалён профиль пользователя {member.name} (ID: {member.id})")
                        break
        
        # 2. Удаляем каналы обзвона (категория ОБЗВОНЫ)
        for category in member.guild.categories:
            if category.name.startswith("📞 ОБЗВОНЫ"):
                for channel in category.text_channels:
                    # Проверяем по topic или по имени
                    if channel.topic and str(member.id) in channel.topic:
                        await channel.delete()
                        print(f"✅ Удалён канал обзвона {channel.name} для {member.name}")
                    elif member.display_name.lower() in channel.name.lower():
                        await channel.delete()
                        print(f"✅ Удалён канал обзвона {channel.name} для {member.name}")
        
    except Exception as e:
        print(f"❌ Ошибка при удалении каналов пользователя {member.name}: {e}")

async def main():
    async with bot:
        # Запускаем планировщик мероприятий
        await setup_scheduler(bot)
        
        # Запускаем авто-рекламу
        await setup_advertising(bot)
        
        await bot.start(BOT_TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")