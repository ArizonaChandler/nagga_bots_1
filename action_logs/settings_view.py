"""Панель настроек логов"""
import discord
from core.admin_views import AdminOnlyView
from action_logs.views import ActionLogsAdminView


class ActionLogsSettingsView(AdminOnlyView):
    
    def __init__(self):
        super().__init__(timeout=None)
        self._add_buttons()
        self._add_back_button()
    
    def _add_buttons(self):
        self.clear_items()
        
        settings_btn = discord.ui.Button(
            label="⚙️ Настройка логов",
            style=discord.ButtonStyle.primary,
            emoji="⚙️",
            row=0,
            custom_id="logs_settings"
        )
        settings_btn.callback = self.open_admin_panel
        self.add_item(settings_btn)
    
    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=4,
            custom_id="logs_back_to_global"
        )
        
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
    
    async def open_admin_panel(self, interaction: discord.Interaction):
        from action_logs.views import ActionLogsAdminView
        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКА ЛОГОВ ДЕЙСТВИЙ**",
            description="Настройка канала логов и выбираемых событий",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=ActionLogsAdminView())