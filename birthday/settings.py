"""Настройки системы дней рождения"""
import discord
from core.database import db
from core.utils import is_super_admin, is_admin
from core.config import CONFIG, save_config
from birthday.base import PermanentView


class BirthdaySettingsView(PermanentView):
    """Панель настроек дней рождения"""

    def __init__(self):
        super().__init__()

        channels_btn = discord.ui.Button(
            label="📡 Настройка каналов",
            style=discord.ButtonStyle.primary,
            emoji="📡",
            row=0
        )
        channels_btn.callback = self.channels_menu
        self.add_item(channels_btn)

    async def channels_menu(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return

        embed = discord.Embed(
            title="📡 **НАСТРОЙКА КАНАЛОВ ДНЕЙ РОЖДЕНИЯ**",
            description="Выберите, какой канал хотите настроить:",
            color=0x7289da
        )
        view = BirthdayChannelsView()
        await interaction.response.edit_message(embed=embed, view=view)


class BirthdayChannelsView(discord.ui.View):
    """Меню выбора канала"""

    def __init__(self):
        super().__init__(timeout=60)

        public_btn = discord.ui.Button(label="🎂 Канал дней рождения", style=discord.ButtonStyle.secondary, row=0)
        public_btn.callback = self.set_public_channel
        self.add_item(public_btn)

        settings_btn = discord.ui.Button(label="⚙️ Канал настроек", style=discord.ButtonStyle.secondary, row=0)
        settings_btn.callback = self.set_settings_channel
        self.add_item(settings_btn)

        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=1)
        back_btn.callback = self.back
        self.add_item(back_btn)

    async def set_public_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetChannelModal("birthday_channel", "канал дней рождения"))

    async def set_settings_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetChannelModal("birthday_settings_channel", "канал настроек дней рождения"))

    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКИ ДНЕЙ РОЖДЕНИЯ**",
            description="Настройка системы дней рождения",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=BirthdaySettingsView())


class SetChannelModal(discord.ui.Modal, title="📡 НАСТРОЙКА КАНАЛА"):
    def __init__(self, setting_key: str, description: str):
        super().__init__()
        self.setting_key = setting_key

        self.channel_id = discord.ui.TextInput(
            label=f"ID {description}",
            placeholder="123456789012345678",
            max_length=20,
            required=True
        )
        self.add_item(self.channel_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return

            db.set_setting(self.setting_key, self.channel_id.value, str(interaction.user.id))
            CONFIG[self.setting_key] = self.channel_id.value

            await interaction.response.send_message(f"✅ Настройка сохранена: {channel.mention}", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)