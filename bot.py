#!/usr/bin/env python3
"""
Unit Management System v1.2
Модульная архитектура с файловым хранилищем
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
    print("✅ **UNIT MANAGEMENT SYSTEM v1.2**")
    print("="*60)
    print(f"🤖 Бот: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🌐 Серверов: {len(bot.guilds)}")
    print(f"📁 Файловое хранилище: {file_manager.storage_path}")
    print("="*60 + "\n")
    
    colors = db.get_dual_colors()
    dual_mcl_core.token_colors = {1: colors[0], 2: colors[1]}
    
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="!info | v1.2"
    ))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"❌ Ошибка: {error}")

async def main():
    async with bot:
        await bot.start(BOT_TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")