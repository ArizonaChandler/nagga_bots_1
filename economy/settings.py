"""Панель настроек экономики (только для админов БД)"""
import discord
from core.admin_views import AdminOnlyView
from core.database import db
from core.config import CONFIG
from core.utils import is_admin
from economy.manager import economy_manager


class EconomySettingsView(AdminOnlyView):
    
    def __init__(self):
        super().__init__(timeout=None)
        self._add_buttons()
        self._add_back_button()
    
    def _add_buttons(self):
        self.clear_items()
        
        # Кнопка настройки каналов
        channel_btn = discord.ui.Button(label="📡 Настройка каналов", style=discord.ButtonStyle.primary, row=0)
        channel_btn.callback = self.channels_menu
        self.add_item(channel_btn)
        
        # Кнопка логов покупок
        logs_btn = discord.ui.Button(label="📋 Канал логов покупок", style=discord.ButtonStyle.primary, row=0)
        logs_btn.callback = self.set_logs_channel
        self.add_item(logs_btn)
        
        # Настройки начислений
        voice_btn = discord.ui.Button(label="🎙️ Голосовой канал (балл/мин)", style=discord.ButtonStyle.secondary, row=1)
        voice_btn.callback = self.set_voice
        self.add_item(voice_btn)
        
        voice_max_btn = discord.ui.Button(label="📊 Максимум баллов в день за войс", style=discord.ButtonStyle.secondary, row=1)
        voice_max_btn.callback = self.set_voice_max
        self.add_item(voice_max_btn)
        
        capt_btn = discord.ui.Button(label="🎯 CAPT (основной/резерв)", style=discord.ButtonStyle.secondary, row=2)
        capt_btn.callback = self.set_capt
        self.add_item(capt_btn)
        
        mcl_btn = discord.ui.Button(label="🎯 MCL/ВЗМ (основной/резерв)", style=discord.ButtonStyle.secondary, row=2)
        mcl_btn.callback = self.set_mcl
        self.add_item(mcl_btn)
        
        event_btn = discord.ui.Button(label="📅 Взятие МП", style=discord.ButtonStyle.secondary, row=3)
        event_btn.callback = self.set_event
        self.add_item(event_btn)
        
        app_btn = discord.ui.Button(label="📝 Принятие заявки", style=discord.ButtonStyle.secondary, row=3)
        app_btn.callback = self.set_application
        self.add_item(app_btn)
        
        tier_btn = discord.ui.Button(label="🌟 Повышение Tier", style=discord.ButtonStyle.secondary, row=4)
        tier_btn.callback = self.set_tier
        self.add_item(tier_btn)
        
        daily_btn = discord.ui.Button(label="📅 Ежедневный бонус", style=discord.ButtonStyle.secondary, row=4)
        daily_btn.callback = self.set_daily
        self.add_item(daily_btn)
    
    def _add_back_button(self):
        back_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=4)
        
        async def back_callback(interaction: discord.Interaction):
            from core.settings_panel import GlobalSettingsPanel
            embed = discord.Embed(title="⚙️ **ЦЕНТР УПРАВЛЕНИЯ**", color=0x7289da)
            await interaction.response.edit_message(embed=embed, view=GlobalSettingsPanel(interaction.client))
        
        back_btn.callback = back_callback
        self.add_item(back_btn)
    
    # ===== МЕНЮ НАСТРОЙКИ КАНАЛОВ =====
    async def channels_menu(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        embed = discord.Embed(title="📡 НАСТРОЙКА КАНАЛОВ ЭКОНОМИКИ", color=0x7289da)
        embed.description = "Выберите, какой канал хотите настроить:"
        
        view = EconomyChannelsView()
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def set_logs_channel(self, interaction: discord.Interaction):
        """Настройка канала для логов покупок"""
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(SetEconomyChannelModal("economy_logs_channel", "канал логов покупок"))
    
    # ===== МЕТОДЫ НАСТРОЙКИ НАЧИСЛЕНИЙ =====
    async def set_voice(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetNumberModal("eco_voice_points", "Баллов за минуту", economy_manager.settings['voice_points_per_minute']))
    
    async def set_voice_max(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetNumberModal("eco_voice_max_per_day", "Максимум баллов в день", economy_manager.settings['voice_max_per_day']))
    
    async def set_capt(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetTwoNumbersModal("eco_capt_main_points", "eco_capt_reserve_points", "CAPT (основной/резерв)",
                                                                 economy_manager.settings['capt_main_points'], economy_manager.settings['capt_reserve_points']))
    
    async def set_mcl(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetTwoNumbersModal("eco_mcl_main_points", "eco_mcl_reserve_points", "MCL/ВЗМ (основной/резерв)",
                                                                 economy_manager.settings['mcl_main_points'], economy_manager.settings['mcl_reserve_points']))
    
    async def set_event(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetNumberModal("eco_event_points", "Баллов за МП", economy_manager.settings['event_points']))
    
    async def set_application(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetNumberModal("eco_application_points", "Баллов за принятие заявки", economy_manager.settings['application_points']))
    
    async def set_tier(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetThreeNumbersModal("eco_tier3_points", "eco_tier2_points", "eco_tier1_points", "Tier (T3/T2/T1)",
                                                                   economy_manager.settings['tier3_points'], economy_manager.settings['tier2_points'], economy_manager.settings['tier1_points']))
    
    async def set_daily(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SetDailyModal(economy_manager.settings['daily_bonus_base'],
                                                            economy_manager.settings['daily_bonus_increment'],
                                                            economy_manager.settings['daily_bonus_limit']))


class EconomyChannelsView(AdminOnlyView):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🛒 Публичный канал (магазин)", style=discord.ButtonStyle.primary, row=0, custom_id="eco_channel_shop")
    async def set_shop_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetEconomyChannelModal("economy_channel", "публичный канал магазина"))
    
    @discord.ui.button(label="⚙️ Админ-канал (управление)", style=discord.ButtonStyle.primary, row=0, custom_id="eco_channel_admin")
    async def set_admin_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetEconomyChannelModal("economy_admin_channel", "админ-канал управления"))
    
    @discord.ui.button(label="📋 Канал логов покупок", style=discord.ButtonStyle.primary, row=1, custom_id="eco_channel_logs")
    async def set_logs_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetEconomyChannelModal("economy_logs_channel", "канал логов покупок"))
    
    @discord.ui.button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=2, custom_id="eco_channels_back")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="⚙️ **НАСТРОЙКИ ЭКОНОМИКИ**", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=EconomySettingsView())


class SetEconomyChannelModal(discord.ui.Modal, title="📡 НАСТРОЙКА КАНАЛА"):
    def __init__(self, setting_key: str, description: str):
        super().__init__(timeout=None)
        self.setting_key = setting_key
        self.channel_input = discord.ui.TextInput(
            label=f"ID {description}",
            placeholder="123456789012345678",
            max_length=20,
            required=True
        )
        self.add_item(self.channel_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        try:
            channel_id = int(self.channel_input.value)
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                await interaction.response.send_message("❌ Канал не найден", ephemeral=True)
                return
            
            db.set_setting(self.setting_key, str(channel_id), str(interaction.user.id))
            CONFIG[self.setting_key] = str(channel_id)
            
            await interaction.response.send_message(f"✅ Канал настроен: {channel.mention}", ephemeral=True)
            
            # Отправляем панели в соответствующие каналы
            if self.setting_key == "economy_channel":
                from economy.views import EconomyPanelView
                view = EconomyPanelView()
                embed = await view.get_shop_embed()
                await channel.send(embed=embed, view=view)
            
            elif self.setting_key == "economy_admin_channel":
                from economy.views import AdminEconomyView
                embed = discord.Embed(
                    title="⚙️ АДМИН-ПАНЕЛЬ ЭКОНОМИКИ",
                    description="Управление баллами и магазином",
                    color=0x7289da
                )
                await channel.send(embed=embed, view=AdminEconomyView())
            
            elif self.setting_key == "economy_logs_channel":
                embed = discord.Embed(
                    title="📋 КАНАЛ ЛОГОВ ЭКОНОМИКИ",
                    description="Сюда будут приходить уведомления о покупках",
                    color=0x00ff00
                )
                await channel.send(embed=embed)
                
        except ValueError:
            await interaction.response.send_message("❌ Введите корректный ID канала", ephemeral=True)


# ===== ОСТАЛЬНЫЕ КЛАССЫ (без изменений) =====
class SetNumberModal(discord.ui.Modal, title="📝 НАСТРОЙКА"):
    def __init__(self, key: str, label: str, current: int):
        super().__init__(timeout=None)
        self.key = key
        self.input = discord.ui.TextInput(label=label, placeholder=str(current), required=True)
        self.add_item(self.input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.input.value)
            if val < 0:
                await interaction.response.send_message("❌ Не может быть отрицательным", ephemeral=True)
                return
            db.set_setting(self.key, str(val), str(interaction.user.id))
            CONFIG[self.key] = str(val)
            economy_manager._load_settings()
            await interaction.response.send_message(f"✅ {val}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)


class SetTwoNumbersModal(discord.ui.Modal, title="📝 НАСТРОЙКА"):
    def __init__(self, key1: str, key2: str, label: str, val1: int, val2: int):
        super().__init__(timeout=None)
        self.key1, self.key2 = key1, key2
        self.input1 = discord.ui.TextInput(label=f"{label} (основной)", placeholder=str(val1), required=True)
        self.add_item(self.input1)
        self.input2 = discord.ui.TextInput(label=f"{label} (резерв)", placeholder=str(val2), required=True)
        self.add_item(self.input2)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            v1 = int(self.input1.value)
            v2 = int(self.input2.value)
            if v1 < 0 or v2 < 0:
                await interaction.response.send_message("❌ Отрицательные", ephemeral=True)
                return
            db.set_setting(self.key1, str(v1), str(interaction.user.id))
            db.set_setting(self.key2, str(v2), str(interaction.user.id))
            CONFIG[self.key1] = str(v1)
            CONFIG[self.key2] = str(v2)
            economy_manager._load_settings()
            await interaction.response.send_message(f"✅ {v1} / {v2}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Числа", ephemeral=True)


class SetThreeNumbersModal(discord.ui.Modal, title="📝 НАСТРОЙКА"):
    def __init__(self, key1: str, key2: str, key3: str, label: str, v1: int, v2: int, v3: int):
        super().__init__(timeout=None)
        self.key1, self.key2, self.key3 = key1, key2, key3
        self.input1 = discord.ui.TextInput(label=f"{label} (T3)", placeholder=str(v1), required=True)
        self.add_item(self.input1)
        self.input2 = discord.ui.TextInput(label=f"{label} (T2)", placeholder=str(v2), required=True)
        self.add_item(self.input2)
        self.input3 = discord.ui.TextInput(label=f"{label} (T1)", placeholder=str(v3), required=True)
        self.add_item(self.input3)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            v1 = int(self.input1.value)
            v2 = int(self.input2.value)
            v3 = int(self.input3.value)
            if v1 < 0 or v2 < 0 or v3 < 0:
                await interaction.response.send_message("❌ Отрицательные", ephemeral=True)
                return
            db.set_setting(self.key1, str(v1), str(interaction.user.id))
            db.set_setting(self.key2, str(v2), str(interaction.user.id))
            db.set_setting(self.key3, str(v3), str(interaction.user.id))
            CONFIG[self.key1] = str(v1)
            CONFIG[self.key2] = str(v2)
            CONFIG[self.key3] = str(v3)
            economy_manager._load_settings()
            await interaction.response.send_message(f"✅ T3={v1} | T2={v2} | T1={v3}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Числа", ephemeral=True)


class SetDailyModal(discord.ui.Modal, title="📝 ЕЖЕДНЕВНЫЙ БОНУС"):
    def __init__(self, base: int, inc: int, limit: int):
        super().__init__(timeout=None)
        self.input_base = discord.ui.TextInput(label="Базовая награда", placeholder=str(base), required=True)
        self.add_item(self.input_base)
        self.input_inc = discord.ui.TextInput(label="Прирост за 2 дня", placeholder=str(inc), required=True)
        self.add_item(self.input_inc)
        self.input_limit = discord.ui.TextInput(label="Лимит серии (дней)", placeholder=str(limit), required=True)
        self.add_item(self.input_limit)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            base = int(self.input_base.value)
            inc = int(self.input_inc.value)
            limit = int(self.input_limit.value)
            if base < 0 or inc < 0 or limit < 0:
                await interaction.response.send_message("❌ Отрицательные", ephemeral=True)
                return
            db.set_setting('eco_daily_bonus', str(base), str(interaction.user.id))
            db.set_setting('eco_daily_increment', str(inc), str(interaction.user.id))
            db.set_setting('eco_daily_limit', str(limit), str(interaction.user.id))
            CONFIG['eco_daily_bonus'] = str(base)
            CONFIG['eco_daily_increment'] = str(inc)
            CONFIG['eco_daily_limit'] = str(limit)
            economy_manager._load_settings()
            await interaction.response.send_message(f"✅ База={base} | +{inc}/2дня | Лимит={limit}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Числа", ephemeral=True)