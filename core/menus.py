"""Базовые классы для меню с навигацией"""
import discord

class BaseMenuView(discord.ui.View):
    """Базовый класс для всех меню с поддержкой навигации"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        self.previous_view = previous_view
        self.previous_embed = previous_embed
    
    async def show_menu(self, interaction, embed, view):
        """Показать новое меню (редактируя текущее сообщение)"""
        await interaction.response.edit_message(embed=embed, view=view)
    
    def add_back_button(self, row=4):
        """Добавить кнопку "Назад" если есть предыдущее меню"""
        if self.previous_view:
            back_btn = discord.ui.Button(
                label="◀ Назад",
                style=discord.ButtonStyle.secondary,
                emoji="◀",
                row=row
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