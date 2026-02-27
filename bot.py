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
from core.utils import format_mention

from commands.info import setup as setup_info
from commands.settings import setup as setup_settings
from commands.log import setup as setup_log
from commands.stats import setup as setup_stats

from capt.core import capt_core
from mcl.core import dual_mcl_core
from files.core import file_manager

# Импорт планировщика мероприятий
from events.scheduler import setup as setup_scheduler

# Авто-реклама
from advertising.core import setup as setup_advertising

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
    
    # Синхронизация слэш-команд
    try:
        synced = await bot.tree.sync()
        print(f"✅ Синхронизировано {len(synced)} слэш-команд")
    except Exception as e:
        print(f"❌ Ошибка синхронизации: {e}")

    # Проверяем проблемный канал
    channel_id = "1471570430983934099"
    channel = bot.get_channel(int(channel_id))
    if channel:
        print(f"✅ Канал {channel_id} найден: #{channel.name}")
    else:
        print(f"❌ Канал {channel_id} НЕ НАЙДЕН в кэше!")
    
    print("="*60 + "\n")
    
    colors = db.get_dual_colors()
    dual_mcl_core.token_colors = {1: colors[0], 2: colors[1]}
    
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="!info | v1.3"
    ))

@bot.command(name='test_channels')
async def test_channels(ctx):
    """Показать все каналы, которые видит бот"""
    embed = discord.Embed(title="📋 Доступные каналы", color=0x7289da)
    
    channels_list = []
    for guild in bot.guilds:
        for channel in guild.channels:
            channels_list.append(f"📌 {guild.name} - {channel.name} (ID: {channel.id})")
    
    if channels_list:
        embed.description = "\n".join(channels_list[:25])
        if len(channels_list) > 25:
            embed.set_footer(text=f"Показано 25 из {len(channels_list)} каналов")
    else:
        embed.description = "❌ Бот не видит ни одного канала!"
    
    await ctx.send(embed=embed)

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