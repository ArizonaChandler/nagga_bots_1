"""Базовые классы для системы временных комнат"""
import discord


class PermanentView(discord.ui.View):
    """View для постоянных кнопок (без таймаута)"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True