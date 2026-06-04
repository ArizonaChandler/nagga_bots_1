"""Базовые классы для меню с навигацией"""
import discord
import traceback
from core.database import db


class BaseMenuView(discord.ui.View):
    """Базовый класс для всех меню с поддержкой навигации и логированием ошибок"""
    
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None, timeout=120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.guild = guild
        self.previous_view = previous_view
        self.previous_embed = previous_embed
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        """Глобальный перехват ошибок для всех кнопок"""
        error_msg = f"❌ Ошибка: {type(error).__name__}: {error}"
        print(f"🔴 [BUTTON ERROR] {error_msg}")
        print(traceback.format_exc())
        
        db.log_action(
            str(interaction.user.id),
            "BUTTON_ERROR",
            f"Кнопка: {item.custom_id if hasattr(item, 'custom_id') else 'unknown'} | Ошибка: {type(error).__name__}: {error}"
        )
        
        try:
            await interaction.response.send_message(error_msg, ephemeral=True)
        except:
            await interaction.followup.send(error_msg, ephemeral=True)
    
    async def show_menu(self, interaction, embed, view):
        await interaction.response.edit_message(embed=embed, view=view)
    
    def add_back_button(self, row=4):
        if self.previous_view:
            back_btn = discord.ui.Button(
                label="◀ Назад",
                style=discord.ButtonStyle.secondary,
                emoji="◀",
                row=row,
                custom_id="back_button"
            )
            async def back_callback(i):
                await i.response.edit_message(
                    embed=self.previous_embed,
                    view=self.previous_view
                )
            back_btn.callback = back_callback
            self.add_item(back_btn)
    
    async def interaction_check(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Это меню вызвано другим пользователем", ephemeral=True)
            return False
        return True