"""Единая панель настроек всех модулей"""
import discord
from core.admin_views import AdminOnlyView
from core.module_manager import MODULES, module_manager
from core.utils import is_admin


class GlobalSettingsPanel(AdminOnlyView):
    """Единая панель настроек — кнопки управления модулями и их настройками"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self._add_buttons()

    def _add_buttons(self):
        """Добавить кнопки для всех модулей (только для включённых)"""
        self.clear_items()
        row = 0
        col = 0
        
        for module_key, module in MODULES.items():
            if module_key == "files":
                continue
            
            # Показываем кнопки ТОЛЬКО для включённых модулей
            if not module["enabled"]:
                continue
            
            # Кнопка настройки модуля (ведёт в его панель настроек)
            btn = discord.ui.Button(
                label=f"⚙️ {module['name']}",
                style=discord.ButtonStyle.primary,
                row=row,
                custom_id=f"settings_{module_key}"
            )
            btn.callback = self._create_callback(module_key)
            self.add_item(btn)
            
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _create_callback(self, module_key: str):
        async def callback(interaction: discord.Interaction):
            # Проверка прав
            if not await is_super_admin(str(interaction.user.id)):
                await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
                return
            
            # Открываем панель настроек конкретного модуля
            module = MODULES[module_key]
            
            # Импортируем панель настроек модуля
            settings_view = None
            if module_key == "capt":
                from capt_registration.settings_view import CaptSettingsView
                settings_view = CaptSettingsView()
            elif module_key == "mcl":
                from mcl_registration.settings import MCLSettingsView
                settings_view = MCLSettingsView()
            elif module_key == "applications":
                from applications.settings_view import ApplicationsCombinedPanel
                settings_view = ApplicationsCombinedPanel()
            elif module_key == "events":
                from events.settings_view import EventsSettingsView
                settings_view = EventsSettingsView()
            elif module_key == "afk":
                from afk.settings_view import AFKSettingsView
                settings_view = AFKSettingsView()
            elif module_key == "tier":
                from tier.settings_view import TierSettingsView
                settings_view = TierSettingsView()
            elif module_key == "vacation":
                from vacation.settings_view import VacationSettingsView
                settings_view = VacationSettingsView()
            elif module_key == "games":
                from games.settings import GamesSettingsView
                settings_view = GamesSettingsView()
            elif module_key == "birthday":
                from birthday.settings import BirthdaySettingsView
                settings_view = BirthdaySettingsView()
            elif module_key == "advertising":
                from advertising.settings_view import AdSettingsView
                settings_view = AdSettingsView()
            elif module_key == "server_stats":
                from server_stats.settings_view import StatsSettingsView
                settings_view = StatsSettingsView()
            
            if settings_view:
                embed = discord.Embed(
                    title=f"⚙️ **{module['name']}**",
                    description=module['description'],
                    color=0x00ff00
                )
                await interaction.response.edit_message(embed=embed, view=settings_view)
            else:
                await interaction.response.send_message(f"❌ Панель настроек для {module['name']} не найдена", ephemeral=True)
        
        return callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message(
                "❌ **Доступ запрещён**\nТолько администраторы, добавленные в базу данных, могут настраивать модули.",
                ephemeral=True
            )
            return False
        return True