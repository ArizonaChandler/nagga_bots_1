"""Настройки игр"""
import discord
from core.database import db
from core.utils import is_super_admin, is_admin
from core.config import CONFIG, save_config


class GamesSettingsView(discord.ui.View):
    """Панель настроек игр"""

    def __init__(self):
        super().__init__(timeout=120)

        # Кнопка настройки каналов
        channels_btn = discord.ui.Button(
            label="📡 Настройка каналов",
            style=discord.ButtonStyle.primary,
            emoji="📡",
            custom_id="games_channels_btn"
        )
        channels_btn.callback = self.channels_menu
        self.add_item(channels_btn)

        # Кнопка включения/выключения морского боя
        battleship_enabled = db.get_game_enabled("battleship")
        toggle_btn = discord.ui.Button(
            label=f"{'🟢 ВКЛЮЧЁН' if battleship_enabled else '🔴 ВЫКЛЮЧЕН'}",
            style=discord.ButtonStyle.success if battleship_enabled else discord.ButtonStyle.danger,
            emoji="🎮",
            custom_id="games_toggle_btn"
        )
        toggle_btn.callback = self.toggle_battleship
        self.add_item(toggle_btn)

    async def channels_menu(self, interaction: discord.Interaction):
        """Открыть меню выбора канала"""
        # Проверяем права
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return

        embed = discord.Embed(
            title="📡 **НАСТРОЙКА КАНАЛОВ ИГР**",
            description="Выберите, какой канал хотите настроить:",
            color=0x7289da
        )
        view = GamesChannelsView()
        await interaction.response.edit_message(embed=embed, view=view)

    async def toggle_battleship(self, interaction: discord.Interaction):
        """Включить/выключить морской бой"""
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
            return

        new_state = not db.get_game_enabled("battleship")
        db.set_game_enabled("battleship", new_state)

        # Обновляем кнопку в текущем view
        self.clear_items()
        
        channels_btn = discord.ui.Button(
            label="📡 Настройка каналов",
            style=discord.ButtonStyle.primary,
            emoji="📡",
            custom_id="games_channels_btn"
        )
        channels_btn.callback = self.channels_menu
        self.add_item(channels_btn)

        toggle_btn = discord.ui.Button(
            label=f"{'🟢 ВКЛЮЧЁН' if new_state else '🔴 ВЫКЛЮЧЕН'}",
            style=discord.ButtonStyle.success if new_state else discord.ButtonStyle.danger,
            emoji="🎮",
            custom_id="games_toggle_btn"
        )
        toggle_btn.callback = self.toggle_battleship
        self.add_item(toggle_btn)

        await interaction.response.send_message(f"✅ Морской бой {'включён' if new_state else 'выключен'}", ephemeral=True)
        await interaction.message.edit(view=self)


class GamesChannelsView(discord.ui.View):
    """Меню выбора канала для настройки"""

    def __init__(self):
        super().__init__(timeout=60)

        # Ряд 0
        rules_btn = discord.ui.Button(label="📜 Канал правил", style=discord.ButtonStyle.secondary, row=0, custom_id="games_rules_btn")
        rules_btn.callback = self.set_rules_channel
        self.add_item(rules_btn)

        lobby_btn = discord.ui.Button(label="🎮 Канал лобби", style=discord.ButtonStyle.secondary, row=0, custom_id="games_lobby_btn")
        lobby_btn.callback = self.set_lobby_channel
        self.add_item(lobby_btn)

        # Ряд 1
        log_btn = discord.ui.Button(label="📝 Канал логов", style=discord.ButtonStyle.secondary, row=1, custom_id="games_log_btn")
        log_btn.callback = self.set_log_channel
        self.add_item(log_btn)

        settings_btn = discord.ui.Button(label="⚙️ Канал настроек", style=discord.ButtonStyle.secondary, row=1, custom_id="games_settings_btn")
        settings_btn.callback = self.set_settings_channel
        self.add_item(settings_btn)

        # Ряд 2
        category_btn = discord.ui.Button(label="📁 Категория игр", style=discord.ButtonStyle.secondary, row=2, custom_id="games_category_btn")
        category_btn.callback = self.set_category
        self.add_item(category_btn)

        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=2, custom_id="games_back_btn")
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
        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКИ ИГР**",
            description="Настройка системы игр Discord",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=GamesSettingsView())


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
            from core.database import db
            from core.config import CONFIG, save_config
            
            # Просто проверяем, что введены цифры
            if not self.channel_id.value.isdigit():
                await interaction.response.send_message("❌ ID должен содержать только цифры", ephemeral=True)
                return

            channel_id = self.channel_id.value
            
            # Просто сохраняем
            db.set_setting(self.setting_key, channel_id, str(interaction.user.id))
            CONFIG[self.setting_key] = channel_id
            save_config(str(interaction.user.id))
            
            await interaction.response.send_message(f"✅ Настройка сохранена! (ID: {channel_id})", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
