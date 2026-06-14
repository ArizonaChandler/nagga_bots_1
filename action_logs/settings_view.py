"""Панель настроек логов"""
import discord
from core.admin_views import AdminOnlyView
from action_logs.views import ActionLogsPanelView
from action_logs.manager import action_logs_manager


class ActionLogsSettingsView(AdminOnlyView):
    
    def __init__(self):
        super().__init__(timeout=None)
        self._add_buttons()
        self._add_back_button()
    
    def _add_buttons(self):
        self.clear_items()
        
        settings_btn = discord.ui.Button(
            label="⚙️ Настройка логов",
            style=discord.ButtonStyle.primary,
            emoji="⚙️",
            row=0,
            custom_id="logs_settings"
        )
        settings_btn.callback = self.open_admin_panel
        self.add_item(settings_btn)
    
    def _add_back_button(self):
        back_btn = discord.ui.Button(
            label="◀ Назад в главное меню",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=4,
            custom_id="logs_back_to_global"
        )
        
        async def back_callback(interaction: discord.Interaction):
            from core.settings_panel import GlobalSettingsPanel
            embed = discord.Embed(
                title="⚙️ **ЦЕНТР УПРАВЛЕНИЯ СИСТЕМАМИ**",
                description="Настройка всех модулей бота.",
                color=0x7289da
            )
            await interaction.response.edit_message(embed=embed, view=GlobalSettingsPanel(interaction.client))
        
        back_btn.callback = back_callback
        self.add_item(back_btn)
    
    async def open_admin_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКА ЛОГОВ ДЕЙСТВИЙ**",
            description="Настройка канала логов и выбираемых событий",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=ActionLogsAdminView())


class ActionLogsAdminView(AdminOnlyView):
    """Админ-панель логов (настройка)"""
    
    def __init__(self):
        super().__init__(timeout=None)
        self._add_buttons()
    
    def _add_buttons(self):
        self.clear_items()
        
        channel_btn = discord.ui.Button(
            label="📢 Канал логов",
            style=discord.ButtonStyle.primary,
            emoji="📢",
            row=0,
            custom_id="logs_set_channel"
        )
        channel_btn.callback = self.set_log_channel
        self.add_item(channel_btn)
        
        events_btn = discord.ui.Button(
            label="⚙️ Выбрать события",
            style=discord.ButtonStyle.primary,
            emoji="⚙️",
            row=0,
            custom_id="logs_events"
        )
        events_btn.callback = self.select_events
        self.add_item(events_btn)
        
        back_btn = discord.ui.Button(
            label="◀ Назад",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=4,
            custom_id="logs_back"
        )
        back_btn.callback = self.back
        self.add_item(back_btn)
    
    async def set_log_channel(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetLogChannelModal())
    
    async def select_events(self, interaction: discord.Interaction):
        event_types = [
            ("voice_join", "🎙️ Вход в войс"),
            ("voice_leave", "🎙️ Выход из войса"),
            ("voice_move", "🎙️ Перемещение"),
            ("message_edit", "✏️ Редактирование"),
            ("message_delete", "🗑️ Удаление"),
            ("channel_create", "📝 Создание канала"),
            ("channel_delete", "📝 Удаление канала"),
            ("channel_update", "📝 Изменение канала"),
            ("role_grant", "🎭 Выдача роли"),
            ("role_revoke", "🎭 Снятие роли"),
            ("role_create", "🎭 Создание роли"),
            ("role_delete", "🎭 Удаление роли"),
            ("member_join", "👤 Присоединение"),
            ("member_leave", "👤 Уход"),
            ("member_update", "👤 Изменение профиля"),
        ]
        
        view = SelectEventsView(event_types)
        embed = discord.Embed(
            title="⚙️ ВЫБЕРИТЕ СОБЫТИЯ ДЛЯ ЛОГИРОВАНИЯ",
            description="Выберите события, которые будут записываться в лог",
            color=0x7289da
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def back(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКА ЛОГОВ ДЕЙСТВИЙ**",
            description="Настройка системы логирования",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=ActionLogsSettingsView())


class SetLogChannelModal(discord.ui.Modal, title="📢 КАНАЛ ЛОГОВ"):
    channel_id = discord.ui.TextInput(label="ID канала", placeholder="123456789012345678", max_length=20, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(int(self.channel_id.value))
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            action_logs_manager.save_setting('action_logs_channel', self.channel_id.value, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Канал логов настроен: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class SelectEventsView(discord.ui.View):
    def __init__(self, event_types):
        super().__init__(timeout=60)
        
        current_selected = action_logs_manager.get_settings().get('action_logs_enabled_events', [])
        
        select = discord.ui.Select(
            placeholder="Выберите события для логирования",
            options=[
                discord.SelectOption(
                    label=name,
                    value=event_id,
                    default=event_id in current_selected
                )
                for event_id, name in event_types
            ],
            min_values=0,
            max_values=len(event_types)
        )
        
        async def select_callback(interaction: discord.Interaction):
            selected = select.values
            action_logs_manager.save_setting('action_logs_enabled_events', selected, str(interaction.user.id))
            await interaction.response.send_message(f"✅ Выбрано событий для логирования: {len(selected)}", ephemeral=True)
        
        select.callback = select_callback
        self.add_item(select)
        
        cancel_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        async def cancel_callback(interaction: discord.Interaction):
            embed = discord.Embed(
                title="⚙️ **НАСТРОЙКА ЛОГОВ ДЕЙСТВИЙ**",
                description="Настройка канала логов и выбираемых событий",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=ActionLogsAdminView())
        cancel_btn.callback = cancel_callback
        self.add_item(cancel_btn)