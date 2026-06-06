#!/usr/bin/env python3
"""
Unit Management System v1.3
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

# ========== КОМАНДЫ ==========
from commands.info import setup as setup_info
from commands.settings import setup as setup_settings
from commands.log import setup as setup_log

# ========== МОДУЛИ ==========
from files.core import file_manager
from events.scheduler import setup as setup_scheduler
from core.module_manager import setup as setup_modules

# ========== СТАТИСТИКА ==========
from server_stats.global_collector import set_collector, get_collector

# ========== НАСТРОЙКА ==========
load_dotenv()
load_config()

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

    # Инициализация системы модулей
    try:
        print("🎛️ Инициализация системы модулей...")
        await setup_modules(bot)
    except Exception as e:
        print(f"❌ Ошибка инициализации модулей: {e}")
        traceback.print_exc()

    # Инициализация сборщика статистики
    try:
        print("📊 Инициализация сборщика статистики...")
        from server_stats.initializer import setup as setup_stats_panel
        await setup_stats_panel(bot)
        
        set_collector(bot)
        collector = get_collector()
        if collector:
            await collector.start()
        else:
            print("❌ collector не инициализирован")
    except Exception as e:
        print(f"❌ Ошибка инициализации статистики: {e}")
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
    # В систему статистики
    collector = get_collector()
    if collector:
        collector.increment_new_members()

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
    print(f"🔴 {member.name} (ID: {member.id}) покинул сервер")

    collector = get_collector()
    if collector:
        collector.increment_left_members()

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


@bot.command(name="fix_tier_message")
@commands.has_permissions(administrator=True)
async def fix_tier_message(ctx, application_id: int):
    """Восстановить испорченное сообщение заявки"""
    app = tier_manager.get_application(application_id)
    if not app:
        await ctx.send("❌ Заявка не найдена")
        return
    
    from tier.views import TierModerationView
    
    embed = discord.Embed(
        title="🌟 НОВАЯ ЗАЯВКА НА TIER",
        color=0xffa500,
        timestamp=datetime.now()
    )
    embed.add_field(name="👤 Отправитель", value=f"<@{app['user_id']}>", inline=True)
    embed.add_field(name="🎮 Игровой ник", value=app['nickname'], inline=True)
    embed.add_field(name="🏆 Откат с арены", value=app['arena_link'], inline=False)
    embed.add_field(name="📸 Скриншоты", value=app['screenshots'][:200], inline=False)
    embed.add_field(name="📝 Дополнительно", value=app.get('additional', 'Нет'), inline=False)
    embed.set_footer(text=f"Заявка ID: {application_id}")
    
    settings = tier_manager.get_settings()
    channel_id = settings.get('tier_applications_channel')
    channel = ctx.guild.get_channel(int(channel_id))
    
    if channel:
        await channel.send(embed=embed, view=TierModerationView(application_id))
        await ctx.send(f"✅ Заявка {application_id} восстановлена")

@bot.tree.command(name="fix_tier_app", description="Восстановить испорченную заявку TIER")
@commands.has_permissions(administrator=True)
async def fix_tier_app(interaction: discord.Interaction, application_id: int):
    """Восстановить испорченную заявку"""
    
    app = tier_manager.get_application(application_id)
    if not app:
        await interaction.response.send_message(f"❌ Заявка {application_id} не найдена", ephemeral=True)
        return
    
    from tier.views import TierModerationView
    from datetime import datetime
    
    # Создаём новый embed
    embed = discord.Embed(
        title="🌟 НОВАЯ ЗАЯВКА НА TIER",
        color=0xffa500,
        timestamp=datetime.now()
    )
    embed.add_field(name="👤 Отправитель", value=f"<@{app['user_id']}>", inline=True)
    embed.add_field(name="🎮 Игровой ник", value=app['nickname'], inline=True)
    embed.add_field(name="🏆 Откат с арены", value=app['arena_link'], inline=False)
    embed.add_field(name="📸 Скриншоты", value=app['screenshots'][:200], inline=False)
    embed.add_field(name="📝 Дополнительно", value=app.get('additional', 'Нет'), inline=False)
    embed.set_footer(text=f"Заявка ID: {application_id}")
    
    settings = tier_manager.get_settings()
    channel_id = settings.get('tier_applications_channel')
    
    if not channel_id:
        await interaction.response.send_message("❌ Канал анкет не настроен", ephemeral=True)
        return
    
    channel = interaction.guild.get_channel(int(channel_id))
    if not channel:
        await interaction.response.send_message("❌ Канал анкет не найден", ephemeral=True)
        return
    
    # Удаляем старую запись о сообщении
    tier_manager.delete_application_message(application_id)
    
    # Отправляем новое сообщение
    sent_message = await channel.send(embed=embed, view=TierModerationView(application_id))
    
    # Сохраняем новую запись
    tier_manager.save_application_message(
        application_id=application_id,
        channel_id=str(channel.id),
        message_id=str(sent_message.id),
        user_id=app['user_id']
    )
    
    await interaction.response.send_message(f"✅ Заявка {application_id} восстановлена", ephemeral=True)

@bot.tree.command(name="restore_tier_apps", description="СРОЧНО восстановить заявки TIER")
@commands.has_permissions(administrator=True)
async def restore_tier_apps(interaction: discord.Interaction):
    """Принудительное восстановление заявок TIER"""
    
    from tier.views import TierModerationView
    from tier.manager import tier_manager
    
    await interaction.response.defer(ephemeral=True)
    
    # Получаем все ожидающие заявки из БД напрямую
    import sqlite3
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, user_id, user_name, nickname, arena_link, screenshots, additional FROM tier_applications WHERE status = 'pending'")
    apps = cursor.fetchall()
    conn.close()
    
    if not apps:
        await interaction.followup.send("❌ Нет ожидающих заявок TIER в БД", ephemeral=True)
        return
    
    settings = tier_manager.get_settings()
    channel_id = settings.get('tier_applications_channel')
    
    if not channel_id:
        await interaction.followup.send("❌ Канал анкет не настроен", ephemeral=True)
        return
    
    channel = interaction.guild.get_channel(int(channel_id))
    if not channel:
        await interaction.followup.send("❌ Канал не найден", ephemeral=True)
        return
    
    restored = 0
    for app in apps:
        app_id, user_id, user_name, nickname, arena_link, screenshots, additional = app
        
        embed = discord.Embed(
            title="🌟 НОВАЯ ЗАЯВКА НА TIER",
            color=0xffa500,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Отправитель", value=f"<@{user_id}>", inline=True)
        embed.add_field(name="🎮 Игровой ник", value=nickname, inline=True)
        embed.add_field(name="🏆 Откат с арены", value=arena_link, inline=False)
        embed.add_field(name="📸 Скриншоты", value=screenshots[:200], inline=False)
        embed.add_field(name="📝 Дополнительно", value=additional or "Нет", inline=False)
        embed.set_footer(text=f"Заявка ID: {app_id}")
        
        sent = await channel.send(embed=embed, view=TierModerationView(app_id))
        
        # Обновляем запись о сообщении
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO tier_application_messages (application_id, channel_id, message_id, user_id)
            VALUES (?, ?, ?, ?)
        """, (app_id, str(channel.id), str(sent.id), user_id))
        conn.commit()
        conn.close()
        
        restored += 1
    
    await interaction.followup.send(f"✅ Восстановлено {restored} заявок TIER", ephemeral=True)

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