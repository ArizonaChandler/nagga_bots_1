"""Настройки игр"""
import discord
from core.database import db
from core.utils import is_super_admin, is_admin
from core.config import CONFIG, save_config
from core.admin_views import AdminOnlyView
from games.base import PermanentView


class GamesSettingsView(AdminOnlyView):
    """Панель настроек игр"""

    def __init__(self):
        super().__init__()
        self._add_buttons()
        self._add_back_button()

    def _add_buttons(self):
        self.clear_items()
        channels_btn = discord.ui.Button(label="📡 Настройка каналов", style=discord.ButtonStyle.primary, emoji="📡", row=0, custom_id="games_channels")
        channels_btn.callback = self.channels_menu
        self.add_item(channels_btn)

        battleship_enabled = db.get_game_enabled("battleship")
        toggle_btn = discord.ui.Button(label=f"{'🟢 ВКЛЮЧЁН' if battleship_enabled else '🔴 ВЫКЛЮЧЕН'}", style=discord.ButtonStyle.success if battleship_enabled else discord.ButtonStyle.danger, emoji="🎮", row=0, custom_id="games_toggle")
        toggle_btn.callback = self.toggle_battleship
        self.add_item(toggle_btn)

    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=1,
            custom_id="games_back_to_global"
        )
        
        async def back_callback(interaction: discord.Interaction):
            from core.settings_panel import GlobalSettingsPanel
            embed = discord.Embed(
                title="⚙️ **ЦЕНТР УПРАВЛЕНИЯ СИСТЕМАМИ**",
                description="Настройка всех модулей бота.\n\n"
                            "Здесь отображаются кнопки только для **включённых** систем.",
                color=0x7289da
            )
            await interaction.response.edit_message(embed=embed, view=GlobalSettingsPanel(interaction.client))
        
        back_btn.callback = back_callback
        self.add_item(back_btn)

    async def channels_menu(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        embed = discord.Embed(title="📡 **НАСТРОЙКА КАНАЛОВ ИГР**", description="Выберите, какой канал хотите настроить:", color=0x7289da)
        view = GamesChannelsView()
        await interaction.response.edit_message(embed=embed, view=view)

    async def toggle_battleship(self, interaction: discord.Interaction):
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
            return
        new_state = not db.get_game_enabled("battleship")
        db.set_game_enabled("battleship", new_state)
        self._add_buttons()
        await interaction.response.send_message(f"✅ Морской бой {'включён' if new_state else 'выключен'}", ephemeral=True)
        await interaction.message.edit(view=self)


class GamesChannelsView(AdminOnlyView):
    def __init__(self):
        super().__init__(timeout=60)

        rules_btn = discord.ui.Button(label="📜 Канал правил", style=discord.ButtonStyle.secondary, row=0, custom_id="games_rules")
        rules_btn.callback = self.set_rules_channel
        self.add_item(rules_btn)

        lobby_btn = discord.ui.Button(label="🎮 Канал лобби", style=discord.ButtonStyle.secondary, row=0, custom_id="games_lobby")
        lobby_btn.callback = self.set_lobby_channel
        self.add_item(lobby_btn)

        log_btn = discord.ui.Button(label="📝 Канал логов", style=discord.ButtonStyle.secondary, row=1, custom_id="games_log")
        log_btn.callback = self.set_log_channel
        self.add_item(log_btn)

        settings_btn = discord.ui.Button(label="⚙️ Канал настроек", style=discord.ButtonStyle.secondary, row=1, custom_id="games_settings")
        settings_btn.callback = self.set_settings_channel
        self.add_item(settings_btn)

        category_btn = discord.ui.Button(label="📁 Категория игр", style=discord.ButtonStyle.secondary, row=2, custom_id="games_category")
        category_btn.callback = self.set_category
        self.add_item(category_btn)

        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=2, custom_id="games_back")
        back_btn.callback = self.back
        self.add_item(back_btn)

    async def set_rules_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetChannelModal("games_rules_channel", "канал правил игр"))

    async def set_lobby_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetChannelModal("games_lobby_channel", "канал лобби игр"))

    async def set_log_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetChannelModal("games_log_channel", "канал логов игр"))

    async def set_settings_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetChannelModal("games_settings_channel", "канал настроек игр"))

    async def set_category(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetChannelModal("games_category_id", "категория для игр"))

    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ **НАСТРОЙКИ ИГР**", description="Настройка системы игр Discord", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=GamesSettingsView())


class SetChannelModal(discord.ui.Modal, title="📡 НАСТРОЙКА КАНАЛА"):
    def __init__(self, setting_key: str, description: str):
        super().__init__()
        self.setting_key = setting_key
        self.channel_id = discord.ui.TextInput(label=f"ID {description}", placeholder="123456789012345678", max_length=20, required=True)
        self.add_item(self.channel_id)

    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        try:
            if self.setting_key == "games_category_id":
                category = interaction.guild.get_channel(int(self.channel_id.value))
                if not category or not isinstance(category, discord.CategoryChannel):
                    await interaction.response.send_message("❌ Категория не найдена", ephemeral=True)
                    return
            else:
                channel = interaction.guild.get_channel(int(self.channel_id.value))
                if not channel:
                    await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                    return
            db.set_setting(self.setting_key, self.channel_id.value, str(interaction.user.id))
            CONFIG[self.setting_key] = self.channel_id.value
            save_config(str(interaction.user.id))
            await interaction.response.send_message(f"✅ Настройка сохранена!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)