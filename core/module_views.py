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
        self.module_manager = module_manager
        self._add_buttons()

    def _add_buttons(self):
        self.clear_items()
        row = 0
        col = 0
        
        # Собираем все toggleable модули
        toggleable_modules = []
        for module_key, module in MODULES.items():
            if module.get("toggleable", True):
                toggleable_modules.append((module_key, module))
        
        # Определяем количество кнопок в ряду
        # Максимум 5 рядов, поэтому при 2 кнопках в ряду = 10 модулей
        # При 3 кнопках в ряду = 15 модулей
        buttons_per_row = 3
        max_rows = 4  # 0, 1, 2, 3 (4 ряда, 5й оставляем для других кнопок)
        
        for idx, (module_key, module) in enumerate(toggleable_modules):
            # Если превысили максимум рядов — выходим
            if row >= max_rows:
                break
            
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
            if col >= buttons_per_row:
                col = 0
                row += 1

    def _create_callback(self, module_key: str):
        async def callback(interaction: discord.Interaction):
            if not await is_super_admin(str(interaction.user.id)):
                await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
                return
            
            if self.module_manager is None:
                await interaction.response.send_message("❌ Система управления модулями не инициализирована!", ephemeral=True)
                return
            
            module = MODULES[module_key]
            new_state = not module["enabled"]
            
            await interaction.response.send_message(f"🔄 {module['name']} {'включается' if new_state else 'выключается'}...", ephemeral=True)
            
            success, msg = await self.module_manager.set_enabled(
                module_key, 
                new_state, 
                str(interaction.user.id)
            )
            
            if success:
                try:
                    self._add_buttons()
                    await interaction.message.edit(view=self)
                except:
                    pass
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {msg}", ephemeral=True)
        
        return callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message(
                "❌ **Доступ запрещён**\nТолько супер-администратор может управлять модулями.",
                ephemeral=True
            )
            return False
        return True