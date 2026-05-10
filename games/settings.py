"""Настройки игр — временная упрощённая версия"""
import discord
from core.database import db
from core.utils import is_super_admin, is_admin


class GamesSettingsView(discord.ui.View):
    """Панель настроек игр (упрощённая)"""

    def __init__(self):
        super().__init__(timeout=120)  # ← таймаут 120 секунд
        self.add_item(discord.ui.Button(
            label="📡 Настройка каналов",
            style=discord.ButtonStyle.primary,
            emoji="📡",
            custom_id="test_btn"
        ))
        self.add_item(discord.ui.Button(
            label="✅ ТЕСТОВАЯ КНОПКА",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id="test_btn2"
        ))

    async def interaction_check(self, interaction):
        # Разрешаем всем для теста
        return True