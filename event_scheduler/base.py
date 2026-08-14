"""Базовый класс для постоянных кнопок (без проверки пользователя)"""
import discord

class PermanentView(discord.ui.View):
    """View для постоянных кнопок (без таймаута и без проверки пользователя)"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Разрешаем всем пользователям нажимать кнопки"""
        return True