"""Auto Advertising Views - Интерфейс настроек"""
import discord
from datetime import datetime
from core.database import db
from core.menus import BaseMenuView

# Тестовая модалка - максимально простая
class TestModal(discord.ui.Modal, title="Тест"):
    test_input = discord.ui.TextInput(
        label="Тест",
        placeholder="Введите что-нибудь",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Вы ввели: {self.test_input.value}", ephemeral=True)

class AdSettingsView(BaseMenuView):
    """Меню настроек авто-рекламы"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        # Тестовая кнопка
        test_btn = discord.ui.Button(
            label="🔴 ТЕСТ",
            style=discord.ButtonStyle.danger,
            emoji="🔴",
            row=0
        )
        async def test_cb(i):
            try:
                modal = TestModal()
                await i.response.send_modal(modal)
            except Exception as e:
                print(f"Ошибка в test_cb: {e}")
                await i.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)
        test_btn.callback = test_cb
        self.add_item(test_btn)
        
        self.add_back_button()
    
    async def show_stats(self, interaction):
        pass
    
    async def toggle_ad(self, interaction):
        pass