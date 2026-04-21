"""Панель настроек системы AFK"""
import discord
from afk.base import PermanentView
from afk.manager import afk_manager
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention


class AFKSettingsView(PermanentView):
    """Постоянные кнопки для настройки системы AFK"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="📢 Канал AFK", 
        style=discord.ButtonStyle.primary,
        emoji="📢",
        row=0,
        custom_id="afk_settings_channel"
    )
    async def set_afk_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для AFK"""
        await interaction.response.send_modal(SetAFKChannelModal())
    
    @discord.ui.button(
        label="⏰ Макс. часов AFK", 
        style=discord.ButtonStyle.primary,
        emoji="⏰",
        row=0,
        custom_id="afk_settings_max_hours"
    )
    async def set_max_hours(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить максимальное количество часов AFK"""
        await interaction.response.send_modal(SetAFKMaxHoursModal())
    
    @discord.ui.button(
        label="📊 Текущие настройки", 
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        row=1,
        custom_id="afk_settings_show"
    )
    async def show_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать текущие настройки"""
        embed = discord.Embed(
            title="📊 НАСТРОЙКИ СИСТЕМЫ AFK",
            color=0x00ff00
        )
        
        guild = interaction.guild
        settings = afk_manager.get_settings()
        
        afk_channel = format_mention(guild, settings.get('afk_channel'), 'channel') if settings.get('afk_channel') else "`Не настроен`"
        max_hours = settings.get('afk_max_hours', 24)
        
        embed.add_field(name="📢 Канал AFK", value=afk_channel, inline=False)
        embed.add_field(name="⏰ Максимальное время AFK", value=f"`{max_hours} часов`", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ===== МОДАЛКИ ДЛЯ НАСТРОЕК =====

class SetAFKChannelModal(discord.ui.Modal, title="📢 КАНАЛ AFK"):
    def __init__(self):
        super().__init__()
    
    channel_id = discord.ui.TextInput(
        label="ID канала для AFK",
        placeholder="123456789012345678",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from core.config import CONFIG, save_config
        from core.database import db
        
        try:
            # Получаем сервер из CONFIG
            server_id = CONFIG.get('server_id')
            if not server_id:
                await interaction.response.send_message(
                    "❌ Сначала установите ID сервера в Глобальных настройках",
                    ephemeral=True
                )
                return
            
            guild = interaction.client.get_guild(int(server_id))
            if not guild:
                await interaction.response.send_message(
                    f"❌ Сервер с ID {server_id} не найден",
                    ephemeral=True
                )
                return
            
            # Получаем канал
            channel = guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message(
                    f"❌ Канал {self.channel_id.value} не найден на сервере {guild.name}",
                    ephemeral=True
                )
                return
            
            # Сохраняем в CONFIG и БД
            CONFIG['afk_channel'] = self.channel_id.value
            db.set_setting('afk_channel', self.channel_id.value, str(interaction.user.id))
            save_config(str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Канал AFK настроен: {channel.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetAFKMaxHoursModal(discord.ui.Modal, title="⏰ МАКСИМАЛЬНОЕ ВРЕМЯ AFK"):
    def __init__(self):
        super().__init__()
    
    hours = discord.ui.TextInput(
        label="Максимальное количество часов",
        placeholder="24",
        max_length=3,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from core.config import CONFIG, save_config
        from core.database import db
        
        try:
            hours_num = int(self.hours.value)
            if hours_num <= 0:
                await interaction.response.send_message("❌ Часов должно быть больше 0", ephemeral=True)
                return
            if hours_num > 168:  # Максимум 7 дней
                await interaction.response.send_message("❌ Максимум 168 часов (7 дней)", ephemeral=True)
                return
            
            # Сохраняем настройку
            CONFIG['afk_max_hours'] = str(hours_num)
            db.set_setting('afk_max_hours', str(hours_num), str(interaction.user.id))
            save_config(str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Максимальное время AFK установлено: **{hours_num} часов**",
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)