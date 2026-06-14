"""Панель настроек статистики"""
import discord
from core.admin_views import AdminOnlyView
from core.database import db
from core.config import CONFIG, save_config
from core.utils import is_admin
from stats.manager import stats_manager


class StatsSettingsView(AdminOnlyView):
    
    def __init__(self):
        super().__init__(timeout=None)
        self._add_buttons()
        self._add_back_button()
    
    def _add_buttons(self):
        self.clear_items()
        
        channel_btn = discord.ui.Button(label="📡 Канал статистики", style=discord.ButtonStyle.primary, row=0)
        channel_btn.callback = self.set_channel
        self.add_item(channel_btn)
        
        backup_btn = discord.ui.Button(label="💾 Настройка бекапа", style=discord.ButtonStyle.primary, row=0)
        backup_btn.callback = self.backup_settings
        self.add_item(backup_btn)
    
    def _add_back_button(self):
        back_btn = discord.ui.Button(label="◀ Назад в главное меню", style=discord.ButtonStyle.secondary, row=4)
        
        async def back_callback(interaction: discord.Interaction):
            from core.settings_panel import GlobalSettingsPanel
            embed = discord.Embed(
                title="⚙️ **ЦЕНТР УПРАВЛЕНИЯ СИСТЕМАМИ**",
                description="Настройка всех модулей бота.",
                color=0x7289da
            )
            await interaction.response.edit_message(embed=embed, view=GlobalSettingsPanel(interaction.client))
        
        back_btn.callback = back_callback
        self.add_item(back_btn)
    
    async def set_channel(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetStatsChannelModal())
    
    async def backup_settings(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetBackupSettingsModal())


class SetStatsChannelModal(discord.ui.Modal, title="📡 КАНАЛ СТАТИСТИКИ"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            
            db.set_setting('stats_channel', self.channel_id.value, str(interaction.user.id))
            CONFIG['stats_channel'] = self.channel_id.value
            save_config(str(interaction.user.id))
            
            await interaction.response.send_message(f"✅ Канал статистики настроен: {channel.mention}", ephemeral=True)
            
            # Отправляем панель в канал
            from stats.views import StatsPanelView, BackupPanelView
            embed = discord.Embed(
                title="📊 ПАНЕЛЬ СТАТИСТИКИ",
                description="Управление статистикой сервера",
                color=0x7289da
            )
            await channel.send(embed=embed, view=StatsPanelView())
            
            # Админ-панель (только для супер-админа)
            admin_channel = interaction.guild.get_channel(int(self.channel_id.value))
            if admin_channel:
                embed2 = discord.Embed(
                    title="💾 ПАНЕЛЬ БЕКАПА",
                    description="Управление бекапами сервера (только для супер-админа)",
                    color=0xffa500
                )
                await admin_channel.send(embed=embed2, view=BackupPanelView())
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SetBackupSettingsModal(discord.ui.Modal, title="💾 НАСТРОЙКА БЕКАПА"):
    enabled = discord.ui.TextInput(label="Включить бекап (true/false)", placeholder="true", required=True)
    time = discord.ui.TextInput(label="Время бекапа (ЧЧ:ММ)", placeholder="00:00", required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            enabled = self.enabled.value.lower() == 'true'
            time = self.time.value
            
            if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time):
                await interaction.response.send_message("❌ Неверный формат времени", ephemeral=True)
                return
            
            db.set_setting('stats_backup_enabled', str(enabled), str(interaction.user.id))
            db.set_setting('stats_backup_time', time, str(interaction.user.id))
            CONFIG['stats_backup_enabled'] = str(enabled)
            CONFIG['stats_backup_time'] = time
            save_config(str(interaction.user.id))
            
            stats_manager.backup_enabled = enabled
            stats_manager.backup_time = time
            
            if enabled:
                await stats_manager.start_backup_scheduler()
            
            await interaction.response.send_message(f"✅ Настройки бекапа сохранены: {'включён' if enabled else 'выключен'}, время {time}", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)