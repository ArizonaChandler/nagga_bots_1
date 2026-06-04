"""Панель управления модулями (единый канал настроек)"""
import discord
from core.admin_views import AdminOnlyView
from core.database import db
from core.utils import is_super_admin
from core.module_manager import MODULES, module_manager


class ModulesControlPanel(AdminOnlyView):
    """Панель управления модулями — только для супер-админа"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self._add_buttons()

    def _add_buttons(self):
        self.clear_items()
        row = 0
        col = 0
        for module_key, module in MODULES.items():
            if not module.get("toggleable", True):
                continue

            status = "🟢 ВКЛЮЧЁН" if module["enabled"] else "🔴 ВЫКЛЮЧЕН"
            btn = discord.ui.Button(
                label=f"{module['name']} ({status})",
                style=discord.ButtonStyle.success if module["enabled"] else discord.ButtonStyle.secondary,
                row=row,
                custom_id=f"module_toggle_{module_key}"
            )
            btn.callback = self._create_callback(module_key)
            self.add_item(btn)

            col += 1
            if col >= 2:
                col = 0
                row += 1

        # Кнопка настройки канала глобальных настроек (только для супер-админа)
        settings_btn = discord.ui.Button(
            label="📡 Настройка канала управления",
            style=discord.ButtonStyle.primary,
            emoji="📡",
            row=row + 1,
            custom_id="global_settings_channel"
        )
        settings_btn.callback = self.set_global_settings_channel
        self.add_item(settings_btn)

    def _create_callback(self, module_key: str):
        async def callback(interaction: discord.Interaction):
            if not await is_super_admin(str(interaction.user.id)):
                await interaction.response.send_message(
                    "❌ Только **Супер-администратор** может управлять модулями!",
                    ephemeral=True
                )
                return

            module = MODULES[module_key]
            new_state = not module["enabled"]

            # Меняем состояние
            success, msg = await module_manager.set_enabled(module_key, new_state, str(interaction.user.id))

            if success:
                # Обновляем кнопки
                self._add_buttons()
                await interaction.response.edit_message(view=self)

                # Отправляем подтверждение
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {msg}", ephemeral=True)

        return callback

    async def set_global_settings_channel(self, interaction: discord.Interaction):
        """Настроить канал для глобальных настроек"""
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
            return

        await interaction.response.send_modal(SetGlobalSettingsChannelModal())

    async def interaction_check(self, interaction: discord.Interaction):
        # Проверка на супер-админа
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message(
                "❌ **Доступ запрещён**\nТолько супер-администратор может управлять модулями.",
                ephemeral=True
            )
            return False
        return True


class SetGlobalSettingsChannelModal(discord.ui.Modal, title="📡 КАНАЛ УПРАВЛЕНИЯ МОДУЛЯМИ"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return

            db.set_setting('global_settings_channel', self.channel_id.value, str(interaction.user.id))
            CONFIG['global_settings_channel'] = self.channel_id.value
            save_config(str(interaction.user.id))

            await interaction.response.send_message(
                f"✅ Канал управления модулями установлен: {channel.mention}\n"
                f"🔄 Перезапустите бота для создания панели.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)