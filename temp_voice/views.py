"""Кнопки для системы временных комнат (ТЕСТОВАЯ ВЕРСИЯ)"""
import discord
from temp_voice.base import PermanentView, CreatorOnlyView
from temp_voice.manager import temp_voice_manager
from temp_voice.modals import CreateRoomModal


class TempVoicePublicView(PermanentView):
    """Публичные кнопки для создания и управления комнатами"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="🎤 СОЗДАТЬ КОМНАТУ",
        style=discord.ButtonStyle.success,
        emoji="🎤",
        row=0,
        custom_id="temp_voice_create"
    )
    async def create_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        print("🎤 [TEST] create_room НАЖАТА!")
        existing = temp_voice_manager.get_user_room(interaction.user.id)
        if existing:
            await interaction.response.send_message(
                f"❌ У вас уже есть комната: <#{existing['channel_id']}>",
                ephemeral=True
            )
            return
        await interaction.response.send_modal(CreateRoomModal())
    
    @discord.ui.button(
        label="🔧 УПРАВЛЯТЬ",
        style=discord.ButtonStyle.primary,
        emoji="🔧",
        row=0,
        custom_id="temp_voice_manage"
    )
    async def manage_room(self, interaction: discord.Interaction, button: discord.ui.Button):
        print("🎤 [TEST] manage_room НАЖАТА!")
        room = temp_voice_manager.get_user_room(interaction.user.id)
        if not room:
            await interaction.response.send_message("❌ У вас нет комнаты", ephemeral=True)
            return
        
        channel = interaction.guild.get_channel(int(room['channel_id']))
        if not channel:
            await interaction.response.send_message("❌ Комната не найдена", ephemeral=True)
            return
        
        view = TempVoiceManageView(interaction.user.id, channel.id)
        embed = discord.Embed(title="🎤 УПРАВЛЕНИЕ", description=f"Комната: {channel.mention}", color=0x00bfff)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class TempVoiceManageView(CreatorOnlyView):
    """Панель управления комнатой (ТЕСТОВАЯ ВЕРСИЯ)"""
    
    def __init__(self, creator_id: int, channel_id: int):
        super().__init__(creator_id, timeout=None)
        self.channel_id = channel_id
        
        # ПРОСТАЯ КНОПКА ДЛЯ ТЕСТА
        self.test_btn = discord.ui.Button(
            label="✅ ТЕСТОВАЯ КНОПКА",
            style=discord.ButtonStyle.success,
            row=0,
            custom_id="test_button"
        )
        self.test_btn.callback = self.test_callback
        self.add_item(self.test_btn)
    
    async def test_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Простейший тестовый callback"""
        print("🎤 [TEST] ТЕСТОВАЯ КНОПКА НАЖАТА!")
        await interaction.response.send_message("✅ Кнопка работает!", ephemeral=True)