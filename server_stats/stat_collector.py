"""Сборщик статистики сервера"""
import asyncio
import discord
import logging
import os
from datetime import datetime, timedelta
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
        
        # Загружаем статистику за сегодня из БД
        today_stats = stats_manager.get_today_stats()
        if not today_stats:
            # Создаём новую запись
            stats_manager.save_daily_stats({
                'new_members': 0,
                'new_applications': 0,
                'left_members': 0,
                'accepted_applications': 0,
                'max_voice_online': 0,
                'capt_registrations': 0,
                'date': datetime.now(MSK_TZ).date().isoformat()
            })
        
        self.task = asyncio.create_task(self._run())
    
    async def _run(self):
        """Фоновый процесс"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            now = datetime.now(MSK_TZ)
            
            # Проверяем, нужно ли отправить отчёт (23:59)
            if now.hour == 23 and now.minute == 59:
                # Проверяем, не отправляли ли уже сегодня
                if self.last_report_date != now.date():
                    await self.send_daily_report()
                    self.last_report_date = now.date()
                    await asyncio.sleep(60)  # Ждём до следующего дня
            
            # Обновляем максимальное количество в войсе
            await self.update_max_voice()
            
            await asyncio.sleep(60)  # Проверяем каждую минуту
    
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
        
        # Получаем статистику за сегодня
        today_stats = stats_manager.get_today_stats()
        
        if not today_stats:
            today_stats = {
                'new_members': 0,
                'new_applications': 0,
                'left_members': 0,
                'accepted_applications': 0,
                'max_voice_online': 0,
                'capt_registrations': 0,
            }
        
        # Формируем отчёт
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
        
        embed.set_footer(text="Статистика за сегодня")
        
        # Отправляем в канал
        await channel.send(embed=embed)
        logger.info(f"✅ Отчёт статистики отправлен в #{channel.name}")
        
        # Создаём бекап базы данных
        backup_path = create_backup()
        if backup_path:
            logger.info(f"✅ Бекап создан: {os.path.basename(backup_path)}")
        
        # Отправляем бекап супер-админу (если включено)
        if settings.get('stats_backup_enabled', True):
            await self.send_backup_to_admin(backup_path)
    
    async def send_backup_to_admin(self, backup_path: str):
        """Отправить бекап супер-админу в ЛС"""
        super_admin_id = CONFIG.get('super_admin_id')
        if not super_admin_id:
            logger.warning("⚠️ Супер-админ не настроен")
            return
        
        try:
            user = await self.bot.fetch_user(int(super_admin_id))
            if not user:
                return
            
            embed = discord.Embed(
                title="💾 БЕКАП БАЗЫ ДАННЫХ",
                description=f"Ежедневный бекап за {datetime.now(MSK_TZ).strftime('%d.%m.%Y')}",
                color=0x00ff00
            )
            
            await user.send(embed=embed)
            
            if backup_path and os.path.exists(backup_path):
                with open(backup_path, 'rb') as f:
                    await user.send(
                        content="📁 **Файл бекапа:**",
                        file=discord.File(f, os.path.basename(backup_path))
                    )
                logger.info(f"✅ Бекап отправлен супер-админу {user.name}")
            else:
                await user.send("❌ Не удалось создать бекап базы данных")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки бекапа: {e}")
    
    # ===== МЕТОДЫ ДЛЯ ИНКРЕМЕНТА СТАТИСТИКИ =====
    
    def increment_new_members(self):
        """Увеличить счётчик новых участников"""
        stats_manager.increment_stat('new_members')
    
    def increment_left_members(self):
        """Увеличить счётчик ушедших участников"""
        stats_manager.increment_stat('left_members')
    
    def increment_new_applications(self):
        """Увеличить счётчик новых заявок"""
        stats_manager.increment_stat('new_applications')
    
    def increment_accepted_applications(self):
        """Увеличить счётчик принятых заявок"""
        stats_manager.increment_stat('accepted_applications')
    
    def increment_capt_registrations(self, count: int = 1):
        """Увеличить счётчик регистраций CAPT"""
        for _ in range(count):
            stats_manager.increment_stat('capt_registrations')


# Глобальный экземпляр
collector = None

async def setup(bot):
    """Функция для вызова из bot.py"""
    global collector
    collector = StatsCollector(bot)
    await collector.start()