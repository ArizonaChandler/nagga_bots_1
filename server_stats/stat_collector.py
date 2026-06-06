"""Сборщик статистики сервера"""
import asyncio
import discord
import logging
import os
from datetime import datetime
import pytz
from core.database import db
from core.config import CONFIG
from server_stats.manager import stats_manager
from server_stats.backup import create_backup

logger = logging.getLogger(__name__)
MSK_TZ = pytz.timezone('Europe/Moscow')


class StatsCollector:
    """Коллектор статистики сервера"""
    
    def __init__(self, bot):
        self.bot = bot
        self.task = None
        self.last_report_date = None
    
    async def start(self):
        """Запустить сборщик статистики"""
        logger.info("📊 Запуск сборщика статистики сервера")
        self.task = asyncio.create_task(self._run())
    
    async def _run(self):
        """Фоновый процесс"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            now = datetime.now(MSK_TZ)
            
            if now.hour == 23 and now.minute == 59:
                if self.last_report_date != now.date():
                    await self.send_daily_report()
                    self.last_report_date = now.date()
                    await asyncio.sleep(60)
            
            await self.update_max_voice()
            await asyncio.sleep(60)
    
    async def update_max_voice(self):
        """Обновить максимальное количество людей в войсе"""
        total_in_voice = 0
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                total_in_voice += len(vc.members)
        stats_manager.update_max_voice(total_in_voice)
    
    async def send_daily_report(self):
        """Отправить ежедневный отчёт"""
        settings = stats_manager.get_settings()
        channel_id = settings.get('stats_channel')
        
        if not channel_id:
            logger.warning("⚠️ Канал для статистики не настроен")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            logger.error(f"❌ Канал статистики {channel_id} не найден")
            return
        
        today_stats = stats_manager.get_today_stats()
        
        if not today_stats:
            today_stats = {
                'new_members': 0,
                'new_applications': 0,
                'left_members': 0,
                'accepted_applications': 0,
                'max_voice_online': 0,
                'capt_registrations': 0,
                'mp_takes': 0,
                'mcl_registrations': 0,
            }
        
        embed = discord.Embed(
            title="📊 СТАТИСТИКА СЕРВЕРА",
            description=f"**{datetime.now(MSK_TZ).strftime('%d.%m.%Y')}**",
            color=0x00ff00,
            timestamp=datetime.now(MSK_TZ)
        )
        
        embed.add_field(
            name="👥 ПОЛЬЗОВАТЕЛИ",
            value=f"└ 🟢 Новых: **{today_stats.get('new_members', 0)}**\n"
                f"└ 🔴 Ушло: **{today_stats.get('left_members', 0)}**\n"
                f"└ 📈 Всего в войсе (макс): **{today_stats.get('max_voice_online', 0)}**",
            inline=False
        )
        
        embed.add_field(
            name="📝 ЗАЯВКИ",
            value=f"└ 📋 Новых: **{today_stats.get('new_applications', 0)}**\n"
                f"└ ✅ Принято: **{today_stats.get('accepted_applications', 0)}**",
            inline=False
        )
        
        embed.add_field(
            name="🎯 CAPT",
            value=f"└ 📨 Регистраций: **{today_stats.get('capt_registrations', 0)}**",
            inline=False
        )
        
        embed.add_field(
            name="🎯 MCL/ВЗМ",
            value=f"└ 📨 Регистраций: **{today_stats.get('mcl_registrations', 0)}**",
            inline=False
        )
        
        embed.add_field(
            name="📅 МЕРОПРИЯТИЯ",
            value=f"└ 🎮 Взято МП: **{today_stats.get('mp_takes', 0)}**",
            inline=False
        )
        
        embed.set_footer(text="Статистика за сегодня")
        
        await channel.send(embed=embed)
        logger.info(f"✅ Отчёт статистики отправлен в #{channel.name}")
    
    async def send_backup_to_admin(self, backup_path: str):
        """Отправить бекап супер-админу"""
        super_admin_id = CONFIG.get('super_admin_id')
        if not super_admin_id:
            return
        
        try:
            user = await self.bot.fetch_user(int(super_admin_id))
            if user:
                embed = discord.Embed(
                    title="💾 БЕКАП БАЗЫ ДАННЫХ",
                    description=f"Ежедневный бекап за {datetime.now(MSK_TZ).strftime('%d.%m.%Y')}",
                    color=0x00ff00
                )
                await user.send(embed=embed)
                with open(backup_path, 'rb') as f:
                    await user.send(file=discord.File(f, os.path.basename(backup_path)))
                logger.info(f"✅ Бекап отправлен супер-админу")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки бекапа: {e}")
    
    # ===== МЕТОДЫ ДЛЯ ИНКРЕМЕНТА =====
    
    def increment_new_members(self):
        stats_manager.increment_stat('new_members')
        print(f"📊 +1 новый участник")
    
    def increment_left_members(self):
        stats_manager.increment_stat('left_members')
        print(f"📊 +1 уход участника")
    
    def increment_new_applications(self):
        stats_manager.increment_stat('new_applications')
        print(f"📊 +1 новая заявка")
    
    def increment_accepted_applications(self):
        stats_manager.increment_stat('accepted_applications')
        print(f"📊 +1 принятая заявка")
    
    def increment_capt_registrations(self):
        stats_manager.increment_stat('capt_registrations')
        print(f"📊 +1 регистрация CAPT")

    async def update_mp_stats(self):
        """Обновить статистику по МП"""
        total_takes = db.get_total_mp_takes()
        today_takes = db.get_today_mp_takes()
        
        # Сохраняем в БД для ежедневного отчёта
        stats = stats_manager.get_today_stats() or {}
        stats['mp_takes'] = today_takes
        stats_manager.save_daily_stats(stats)

    async def update_mcl_stats(self):
        """Обновить статистику по MCL/ВЗМ"""
        total_reg = db.get_total_mcl_registrations()
        today_reg = db.get_today_mcl_registrations()
        
        stats = stats_manager.get_today_stats() or {}
        stats['mcl_registrations'] = today_reg
        stats_manager.save_daily_stats(stats)

    def increment_mp_take(self):
        """Увеличить счётчик взятых МП (вызывать при взятии МП)"""
        stats = stats_manager.get_today_stats() or {}
        stats['mp_takes'] = stats.get('mp_takes', 0) + 1
        stats_manager.save_daily_stats(stats)

    def increment_mcl_registration(self):
        """Увеличить счётчик регистраций MCL (вызывать при регистрации)"""
        stats = stats_manager.get_today_stats() or {}
        stats['mcl_registrations'] = stats.get('mcl_registrations', 0) + 1
        stats_manager.save_daily_stats(stats)

    async def stop(self):
        """Остановить сбор статистики"""
        print("📊 [STATS] Остановка сбора статистики...")
        
        if self.task:
            self.task.cancel()


# Глобальный экземпляр
collector = None