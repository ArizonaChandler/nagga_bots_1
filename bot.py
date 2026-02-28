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

from capt.core import capt_core
from mcl.core import dual_mcl_core
from files.core import file_manager

# Импорт планировщика мероприятий
from events.scheduler import setup as setup_scheduler

# Импорт авто-рекламы
from advertising.core import setup as setup_advertising
from advertising.commands import setup as setup_ad_commands

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# для CAPT регистрации
from capt_registration.views import ModerationView, PublicView
from capt_registration.manager import capt_reg_manager
from capt_registration.embeds import create_registration_embed

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
    print("✅ **UNIT MANAGEMENT SYSTEM v1.3**")
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
    
    # Проверяем проблемный канал
    channel_id = "1471570430983934099"
    channel = bot.get_channel(int(channel_id))
    if channel:
        print(f"✅ Канал {channel_id} найден: #{channel.name}")
    else:
        print(f"❌ Канал {channel_id} НЕ НАЙДЕН в кэше!")
    
    # Синхронизация слэш-команд (если есть)
    try:
        print("🔄 Синхронизация слэш-команд...")
        synced = await bot.tree.sync()
        print(f"✅ Синхронизировано {len(synced)} глобальных слэш-команд")
        
        if synced:
            for cmd in synced:
                if hasattr(cmd, 'name'):
                    print(f"   - /{cmd.name}")
                elif hasattr(cmd, 'commands'):
                    print(f"   - /{cmd.name} (группа с {len(cmd.commands)} командами)")
    except Exception as e:
        print(f"❌ Ошибка синхронизации: {e}")
    
    colors = db.get_dual_colors()
    dual_mcl_core.token_colors = {1: colors[0], 2: colors[1]}
    
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="!info | v1.3"
    ))
    
    # Отправляем постоянные кнопки для CAPT регистрации
    main_channel_id = CONFIG.get('capt_reg_main_channel')
    reserve_channel_id = CONFIG.get('capt_reg_reserve_channel')

    if main_channel_id and reserve_channel_id:
        main_channel = bot.get_channel(int(main_channel_id))
        reserve_channel = bot.get_channel(int(reserve_channel_id))
        
        if main_channel and reserve_channel:
            # Очищаем старые сообщения (опционально)
            async for msg in main_channel.history(limit=10):
                if msg.author == bot.user:
                    await msg.delete()
            
            async for msg in reserve_channel.history(limit=10):
                if msg.author == bot.user:
                    await msg.delete()
            
            # Получаем текущие списки
            main_list, reserve_list = capt_reg_manager.get_lists()
            embed = create_registration_embed(main_list, reserve_list)
            
            # Отправляем новые сообщения с кнопками
            await main_channel.send(embed=embed, view=ModerationView())
            await reserve_channel.send(embed=embed, view=PublicView())
            
            print(f"✅ Постоянные кнопки CAPT регистрации отправлены")

    print("="*60 + "\n")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"❌ Ошибка: {error}")

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