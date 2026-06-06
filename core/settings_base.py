"""Базовый класс для панелей настроек модулей с кнопкой "Назад""""
import discord
from core.admin_views import AdminOnlyView


class BaseSettingsView(AdminOnlyView):
    """Базовый класс для всех панелей настроек модулей с кнопкой "Назад""""
    
    def __init__(self, bot=None):
        super().__init__()
        self.bot = bot
    
    def add_back_button(self, row: int = 4):
        """Добавить кнопку "Назад" в главную панель настроек"""
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=row,
            custom_id="back_to_global_settings"
        )
        
        async def back_callback(interaction: discord.Interaction):
            from core.settings_panel import GlobalSettingsPanel
            embed = discord.Embed(
                title="⚙️ **ЦЕНТР УПРАВЛЕНИЯ СИСТЕМАМИ**",
                description="Настройка всех модулей бота.\n\n"
                            "Здесь отображаются кнопки только для **включённых** систем.\n"
                            "Чтобы включить/выключить модуль, используйте 🎛️ Управление модулями в !settings.",
                color=0x7289da
            )
            await interaction.response.edit_message(embed=embed, view=GlobalSettingsPanel(interaction.client))
        
        back_btn.callback = back_callback
        self.add_item(back_btn)