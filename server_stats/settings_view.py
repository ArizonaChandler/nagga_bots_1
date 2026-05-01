"""Панель настроек системы статистики"""
import discord
from server_stats.base import PermanentView
from server_stats.manager import stats_manager
from core.config import CONFIG, save_config
from core.database import db
from core.utils import format_mention


class StatsSettingsView(PermanentView):
    """Постоянные кнопки для настройки системы статистики"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="📊 Канал статистики", 
        style=discord.ButtonStyle.primary,
        emoji="📊",
        row=0,
        custom_id="stats_channel"
    )
    async def set_stats_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Настроить канал для статистики"""
        await interaction.response.send_modal(SetStatsChannelModal())
    
    @discord.ui.button(
        label="💾 Бекап в ЛС", 
        style=discord.ButtonStyle.primary,
        emoji="💾",
        row=0,
        custom_id="stats_backup_toggle"
    )
    async def toggle_backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Включить/выключить отправку бекапа в ЛС"""
        current = CONFIG.get('stats_backup_enabled', True)
        new_value = not current
        
        stats_manager.save_setting('stats_backup_enabled', str(new_value), str(interaction.user.id))
        
        await interaction.response.send_message(
            f"✅ Отправка бекапа в ЛС {'ВКЛЮЧЕНА' if new_value else 'ВЫКЛЮЧЕНА'}",
            ephemeral=True
        )
    
    @discord.ui.button(
        label="📊 Текущие настройки", 
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        row=1,
        custom_id="stats_settings_show"
    )
    async def show_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать текущие настройки"""
        embed = discord.Embed(
            title="📊 НАСТРОЙКИ СТАТИСТИКИ СЕРВЕРА",
            color=0x00ff00
        )
        
        guild = interaction.guild
        settings = stats_manager.get_settings()
        
        stats_channel = format_mention(guild, settings.get('stats_channel'), 'channel') if settings.get('stats_channel') else "`Не настроен`"
        backup_enabled = "✅ Включена" if settings.get('stats_backup_enabled', True) else "❌ Выключена"
        
        embed.add_field(name="📊 Канал статистики", value=stats_channel, inline=False)
        embed.add_field(name="💾 Бекап в ЛС", value=backup_enabled, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetStatsChannelModal(discord.ui.Modal, title="📊 КАНАЛ СТАТИСТИКИ"):
    def __init__(self):
        super().__init__()
    
    channel_id = discord.ui.TextInput(
        label="ID канала для статистики",
        placeholder="123456789012345678",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            
            stats_manager.save_setting('stats_channel', self.channel_id.value, str(interaction.user.id))
            
            await interaction.response.send_message(
                f"✅ Канал статистики настроен: {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)