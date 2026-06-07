"""Базовые классы для экономической системы"""
import discord


class PermanentView(discord.ui.View):
    """Постоянное View (без таймаута)"""
    def __init__(self):
        super().__init__(timeout=None)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True


class ConfirmView(discord.ui.View):
    """Подтверждение покупки"""
    def __init__(self, user_id: int, item_id: int, price: int, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.item_id = item_id
        self.price = price
        self.confirmed = False
    
    @discord.ui.button(label="✅ Подтвердить", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша покупка!", ephemeral=True)
            return
        self.confirmed = True
        self.stop()
    
    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша покупка!", ephemeral=True)
            return
        self.confirmed = False
        self.stop()