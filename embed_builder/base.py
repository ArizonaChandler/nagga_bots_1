"""Базовые классы для системы создания embed"""
import discord


class PermanentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True