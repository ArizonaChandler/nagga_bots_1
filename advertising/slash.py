"""Auto Advertising Slash Commands"""
import discord
from discord import app_commands
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import is_admin

class AdSlashCommands:
    def __init__(self, bot):
        self.bot = bot
        self.setup_commands()
    
    def setup_commands(self):
        @self.bot.tree.command(name="ad_text", description="Настроить текст рекламы")
        @app_commands.describe(text="Текст рекламы")
        async def ad_text(interaction: discord.Interaction, text: str):
            print(f"🔵 [slash] ad_text called by {interaction.user.id}")
            
            if not await is_admin(str(interaction.user.id)):
                await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
                return
            
            current = db.get_active_ad() or {}
            
            success = db.save_ad_settings(
                message_text=text,
                image_url=current.get('image_url'),
                channel_id=current.get('channel_id', ''),
                interval=current.get('interval_minutes', 65),
                sleep_start=current.get('sleep_start', '02:00'),
                sleep_end=current.get('sleep_end', '06:30'),
                updated_by=str(interaction.user.id)
            )
            
            if success:
                await interaction.response.send_message(f"✅ Текст сохранен:\n{text[:100]}...", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Ошибка сохранения", ephemeral=True)
        
        @self.bot.tree.command(name="ad_channel", description="Установить канал для рекламы")
        @app_commands.describe(channel="Канал для отправки")
        async def ad_channel(interaction: discord.Interaction, channel: discord.TextChannel):
            print(f"🔵 [slash] ad_channel called by {interaction.user.id}")
            
            if not await is_admin(str(interaction.user.id)):
                await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
                return
            
            current = db.get_active_ad() or {}
            
            success = db.save_ad_settings(
                message_text=current.get('message_text', ''),
                image_url=current.get('image_url'),
                channel_id=str(channel.id),
                interval=current.get('interval_minutes', 65),
                sleep_start=current.get('sleep_start', '02:00'),
                sleep_end=current.get('sleep_end', '06:30'),
                updated_by=str(interaction.user.id)
            )
            
            if success:
                await interaction.response.send_message(f"✅ Канал установлен: {channel.mention}", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Ошибка сохранения", ephemeral=True)
        
        @self.bot.tree.command(name="ad_interval", description="Установить интервал отправки")
        @app_commands.describe(minutes="Интервал в минутах (1-1440)")
        async def ad_interval(interaction: discord.Interaction, minutes: int):
            print(f"🔵 [slash] ad_interval called by {interaction.user.id}")
            
            if not await is_admin(str(interaction.user.id)):
                await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
                return
            
            if minutes < 1 or minutes > 1440:
                await interaction.response.send_message("❌ Интервал должен быть от 1 до 1440 минут", ephemeral=True)
                return
            
            current = db.get_active_ad() or {}
            
            success = db.save_ad_settings(
                message_text=current.get('message_text', ''),
                image_url=current.get('image_url'),
                channel_id=current.get('channel_id', ''),
                interval=minutes,
                sleep_start=current.get('sleep_start', '02:00'),
                sleep_end=current.get('sleep_end', '06:30'),
                updated_by=str(interaction.user.id)
            )
            
            if success:
                await interaction.response.send_message(f"✅ Интервал установлен: {minutes} мин", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Ошибка сохранения", ephemeral=True)
        
        @self.bot.tree.command(name="ad_sleep", description="Установить режим сна")
        @app_commands.describe(start="Начало сна (ЧЧ:ММ)", end="Конец сна (ЧЧ:ММ)")
        async def ad_sleep(interaction: discord.Interaction, start: str, end: str):
            print(f"🔵 [slash] ad_sleep called by {interaction.user.id}")
            
            if not await is_admin(str(interaction.user.id)):
                await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
                return
            
            # Проверка формата времени
            try:
                datetime.strptime(start, "%H:%M")
                datetime.strptime(end, "%H:%M")
            except ValueError:
                await interaction.response.send_message("❌ Неверный формат времени. Используйте ЧЧ:ММ", ephemeral=True)
                return
            
            current = db.get_active_ad() or {}
            
            success = db.save_ad_settings(
                message_text=current.get('message_text', ''),
                image_url=current.get('image_url'),
                channel_id=current.get('channel_id', ''),
                interval=current.get('interval_minutes', 65),
                sleep_start=start,
                sleep_end=end,
                updated_by=str(interaction.user.id)
            )
            
            if success:
                await interaction.response.send_message(f"✅ Режим сна: {start} - {end}", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Ошибка сохранения", ephemeral=True)
        
        @self.bot.tree.command(name="ad_image", description="Установить URL картинки")
        @app_commands.describe(url="URL картинки (начинается с http:// или https://)")
        async def ad_image(interaction: discord.Interaction, url: str):
            print(f"🔵 [slash] ad_image called by {interaction.user.id}")
            
            if not await is_admin(str(interaction.user.id)):
                await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
                return
            
            if not (url.startswith('http://') or url.startswith('https://')):
                await interaction.response.send_message("❌ URL должен начинаться с http:// или https://", ephemeral=True)
                return
            
            current = db.get_active_ad() or {}
            
            success = db.save_ad_settings(
                message_text=current.get('message_text', ''),
                image_url=url,
                channel_id=current.get('channel_id', ''),
                interval=current.get('interval_minutes', 65),
                sleep_start=current.get('sleep_start', '02:00'),
                sleep_end=current.get('sleep_end', '06:30'),
                updated_by=str(interaction.user.id)
            )
            
            if success:
                await interaction.response.send_message(f"✅ URL картинки сохранен", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Ошибка сохранения", ephemeral=True)
        
        @self.bot.tree.command(name="ad_status", description="Показать статус рекламы")
        async def ad_status(interaction: discord.Interaction):
            print(f"🔵 [slash] ad_status called by {interaction.user.id}")
            
            settings = db.get_active_ad()
            
            embed = discord.Embed(
                title="📊 Статус авто-рекламы",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            if settings:
                embed.add_field(name="📝 Текст", value=settings['message_text'][:100] + "...", inline=False)
                embed.add_field(name="📢 Канал", value=f"<#{settings['channel_id']}>" if settings['channel_id'] else "❌ Не установлен", inline=True)
                embed.add_field(name="⏱️ Интервал", value=f"{settings['interval_minutes']} мин", inline=True)
                embed.add_field(name="😴 Сон", value=f"{settings['sleep_start']} - {settings['sleep_end']}", inline=True)
                embed.add_field(name="🖼️ Картинка", value="✅ Есть" if settings.get('image_url') else "❌ Нет", inline=True)
                embed.add_field(name="🔘 Статус", value="✅ Активна" if settings.get('is_active') else "❌ Неактивна", inline=True)
                
                if settings.get('last_sent'):
                    embed.add_field(name="🕐 Последняя отправка", value=settings['last_sent'][:16], inline=False)
            else:
                embed.description = "❌ Настройки не найдены"
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        @self.bot.tree.command(name="ad_toggle", description="Включить/выключить рекламу")
        async def ad_toggle(interaction: discord.Interaction):
            print(f"🔵 [slash] ad_toggle called by {interaction.user.id}")
            
            if not await is_admin(str(interaction.user.id)):
                await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
                return
            
            settings = db.get_active_ad()
            if not settings:
                await interaction.response.send_message("❌ Сначала настройте рекламу", ephemeral=True)
                return
            
            new_status = 0 if settings['is_active'] else 1
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE auto_ad SET is_active = ? WHERE id = ?', 
                              (new_status, settings['id']))
                conn.commit()
            
            status_text = "✅ Включена" if new_status else "❌ Выключена"
            await interaction.response.send_message(f"Реклама: {status_text}", ephemeral=True)