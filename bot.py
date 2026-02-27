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
from core.utils import format_mention, is_admin  # 👈 ДОБАВЛЯЕМ is_admin

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
from advertising.slash import AdSlashCommands

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

setup_info(bot)
setup_settings(bot)
setup_log(bot)
setup_stats(bot)

# Запуск планировщика мероприятий
setup_scheduler(bot)

# СОЗДАЕМ ЭКЗЕМПЛЯР СЛЭШ-КОМАНД ДО СИНХРОНИЗАЦИИ
ad_slash = AdSlashCommands(bot)

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
    
    # Синхронизация слэш-команд
    try:
        print("🔄 Синхронизация слэш-команд...")
        synced = await bot.tree.sync()
        print(f"✅ Синхронизировано {len(synced)} глобальных слэш-команд")
        
        # Выводим названия команд для проверки
        if synced:
            for cmd in synced:
                if hasattr(cmd, 'name'):
                    print(f"   - /{cmd.name}")
                elif hasattr(cmd, 'commands'):
                    print(f"   - /{cmd.name} (группа с {len(cmd.commands)} командами)")
        else:
            print("❌ Нет зарегистрированных слэш-команд!")
            
    except Exception as e:
        print(f"❌ Ошибка синхронизации: {e}")
    
    colors = db.get_dual_colors()
    dual_mcl_core.token_colors = {1: colors[0], 2: colors[1]}
    
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="!info | v1.3"
    ))
    
    print("="*60 + "\n")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"❌ Ошибка: {error}")

# Команда для ручной синхронизации (на всякий случай)
@bot.command(name='sync')
async def sync_commands(ctx):
    """Принудительная синхронизация слэш-команд (только для админов)"""
    if not await is_admin(str(ctx.author.id)):  # 👈 Теперь is_admin импортирован
        await ctx.send("❌ Только администраторы")
        return
    
    await ctx.send("🔄 Синхронизация команд...")
    
    try:
        # Очищаем все команды
        bot.tree.clear_commands(guild=None)
        
        # Пересоздаем команды
        from advertising.slash import AdSlashCommands
        ad_slash = AdSlashCommands(bot)
        
        # Синхронизируем
        synced = await bot.tree.sync()
        
        if synced:
            cmd_names = []
            for cmd in synced:
                if hasattr(cmd, 'name'):
                    cmd_names.append(f"/{cmd.name}")
                elif hasattr(cmd, 'commands'):
                    cmd_names.append(f"/{cmd.name} (группа)")
            await ctx.send(f"✅ Синхронизировано {len(synced)} команд: {', '.join(cmd_names)}")
        else:
            await ctx.send("❌ Нет зарегистрированных команд")
    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")

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