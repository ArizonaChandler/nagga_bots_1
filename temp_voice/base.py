"""Базовые классы для системы временных комнат"""
import discord


class PermanentView(discord.ui.View):
    """View для постоянных кнопок (без таймаута)"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Разрешаем всем нажимать кнопки"""
        return True


class CreatorOnlyView(discord.ui.View):
    """View, доступный только создателю комнаты"""
    
    def __init__(self, creator_id: int, timeout=None):
        super().__init__(timeout=timeout)
        self.creator_id = creator_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                "❌ Только создатель комнаты может управлять ею!",
                ephemeral=True
            )
            return False
        return True