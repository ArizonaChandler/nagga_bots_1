"""Панель управления модулями"""
import discord
from core.admin_views import AdminOnlyView
from core.utils import is_super_admin


class ModulesControlPanel(AdminOnlyView):
    """Панель управления модулями — только для супер-админа"""

    def __init__(self, bot, module_manager):
        super().__init__()
        self.bot = bot
        self.module_manager = module_manager
        self.page = 0
        self.items_per_page = 10
        self._add_buttons()

    def _add_buttons(self):
        self.clear_items()
        
        # Получаем модули из module_manager
        modules = self.module_manager.MODULES if hasattr(self.module_manager, 'MODULES') else {}
        
        # Собираем все toggleable модули
        toggleable_modules = []
        for module_key, module in modules.items():
            if module.get("toggleable", True):
                toggleable_modules.append((module_key, module))
        
        total_pages = (len(toggleable_modules) + self.items_per_page - 1) // self.items_per_page
        
        # Текущая страница
        start = self.page * self.items_per_page
        end = min(start + self.items_per_page, len(toggleable_modules))
        current_modules = toggleable_modules[start:end]
        
        row = 0
        col = 0
        buttons_per_row = 2
        
        for module_key, module in current_modules:
            status = "🟢 ВКЛ" if module["enabled"] else "🔴 ВЫКЛ"
            label = f"{module['name']} ({status})"
            
            btn = discord.ui.Button(
                label=label[:80],
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
        
        # Кнопки пагинации (если больше одной страницы)
        if total_pages > 1:
            nav_row = 4  # последний ряд
            
            if self.page > 0:
                prev_btn = discord.ui.Button(
                    label="◀ Назад",
                    style=discord.ButtonStyle.secondary,
                    row=nav_row,
                    custom_id="modules_prev"
                )
                prev_btn.callback = self.prev_page
                self.add_item(prev_btn)
            
            # Индикатор страницы
            page_btn = discord.ui.Button(
                label=f"📄 {self.page + 1}/{total_pages}",
                style=discord.ButtonStyle.secondary,
                row=nav_row,
                disabled=True,
                custom_id="modules_page"
            )
            self.add_item(page_btn)
            
            if self.page < total_pages - 1:
                next_btn = discord.ui.Button(
                    label="Вперёд ▶",
                    style=discord.ButtonStyle.secondary,
                    row=nav_row,
                    custom_id="modules_next"
                )
                next_btn.callback = self.next_page
                self.add_item(next_btn)

    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._add_buttons()
        await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._add_buttons()
        await interaction.response.edit_message(view=self)

    def _create_callback(self, module_key: str):
        async def callback(interaction: discord.Interaction):
            if not await is_super_admin(str(interaction.user.id)):
                await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
                return
            
            if self.module_manager is None:
                await interaction.response.send_message("❌ Система управления модулями не инициализирована!", ephemeral=True)
                return
            
            modules = self.module_manager.MODULES if hasattr(self.module_manager, 'MODULES') else {}
            module = modules.get(module_key)
            if not module:
                await interaction.response.send_message("❌ Модуль не найден!", ephemeral=True)
                return
            
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