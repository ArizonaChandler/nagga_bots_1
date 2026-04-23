"""Базовые классы для системы TIR"""
import discord

class PermanentView(discord.ui.View):
    """View для постоянных кнопок (без таймаута)"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Разрешаем всем нажимать кнопки"""
        return True