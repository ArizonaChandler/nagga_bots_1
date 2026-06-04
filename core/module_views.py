"""Панель управления модулями"""
import discord
from core.admin_views import AdminOnlyView
from core.utils import is_super_admin
from core.module_manager import MODULES


class ModulesControlPanel(AdminOnlyView):
    """Панель управления модулями — только для супер-админа"""

    def __init__(self, bot, module_manager):
        super().__init__()
        self.bot = bot
        self.module_manager = module_manager  # ← сохраняем переданный менеджер
        self._add_buttons()

    def _add_buttons(self):
        """Добавить кнопки для всех модулей (по 3 в ряд)"""
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
            if col >= 3:
                col = 0
                row += 1

    def _create_callback(self, module_key: str):
        """Создать callback для кнопки модуля"""
        async def callback(interaction: discord.Interaction):
            if not await is_super_admin(str(interaction.user.id)):
                await interaction.response.send_message(
                    "❌ Только супер-администратор может управлять модулями!",
                    ephemeral=True
                )
                return
            
            if self.module_manager is None:
                await interaction.response.send_message(
                    "❌ Система управления модулями не инициализирована! Перезапустите бота.",
                    ephemeral=True
                )
                return
            
            module = MODULES[module_key]
            new_state = not module["enabled"]
            
            success, msg = await self.module_manager.set_enabled(
                module_key, 
                new_state, 
                str(interaction.user.id)
            )
            
            if success:
                self._add_buttons()
                await interaction.response.edit_message(view=self)
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
        
        return callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message(
                "❌ **Доступ запрещён**\nТолько супер-администратор может управлять модулями.",
                ephemeral=True
            )
            return False
        return True