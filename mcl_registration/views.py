"""Кнопки для системы MCL"""
import discord
import re
from datetime import datetime
from mcl_registration.base import PermanentView
from mcl_registration.mcl_core import mcl_core
from mcl_registration.manager import mcl_manager
from core.database import db
from core.config import CONFIG
from server_stats.global_collector import get_collector


class StartModal(discord.ui.Modal, title="🎯 НАЧАТЬ РЕГИСТРАЦИЮ"):
    event_name = discord.ui.TextInput(label="Название мероприятия", placeholder="MCL/ВЗМ", max_length=100)
    event_time = discord.ui.TextInput(label="Время сбора (МСК)", placeholder="19:30", max_length=5)
    additional_info = discord.ui.TextInput(label="Дополнительно", required=False, max_length=500, style=discord.TextStyle.paragraph)
    
    async def on_submit(self, interaction: discord.Interaction):
        import re
        from mcl_registration.manager import mcl_manager
        
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', self.event_time.value):
            await interaction.response.send_message("❌ Неверный формат времени", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            await mcl_manager.start_registration(
                str(interaction.user.id),
                interaction.user.display_name,
                interaction.client,
                self.event_name.value,
                self.event_time.value,
                self.additional_info.value
            )
            
            await interaction.followup.send(
                f"✅ Регистрация начата!\n📋 {self.event_name.value} в {self.event_time.value}",
                ephemeral=True
            )
        except Exception as e:
            print(f"❌ Ошибка в StartModal: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)


class SendModal(discord.ui.Modal, title="📨 РАССЫЛКА В ЛС"):
    def __init__(self, session_info):
        super().__init__()
        self.session_info = session_info
        
        self.event_name = discord.ui.TextInput(label="Название", default=session_info.get('event_name', ''), max_length=100)
        self.add_item(self.event_name)
        
        self.event_time = discord.ui.TextInput(label="Время", default=session_info.get('event_time', ''), max_length=5)
        self.add_item(self.event_time)
        
        self.message = discord.ui.TextInput(label="Дополнительно", required=False, max_length=500, style=discord.TextStyle.paragraph)
        self.add_item(self.message)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not CONFIG.get('mcl_role_id'):
            await interaction.response.send_message("❌ Роль для рассылки не настроена", ephemeral=True)
            return
        
        guild = interaction.guild
        role = guild.get_role(int(CONFIG['mcl_role_id']))
        if not role:
            await interaction.response.send_message("❌ Роль не найдена", ephemeral=True)
            return
        
        members = [m for m in guild.members if role in m.roles]
        if not members:
            await interaction.response.send_message("⚠️ Нет участников с этой ролью", ephemeral=True)
            return
        
        await interaction.response.send_message(
            f"🚀 **MCL** | {len(members)} участников | Запуск...",
            ephemeral=False
        )
        
        await mcl_core.send_bulk(
            interaction, members,
            self.event_name.value, self.event_time.value,
            self.message.value or ""
        )


class ModerationView(PermanentView):
    def __init__(self):
        super().__init__()
        self.update_buttons(False)
    
    def update_buttons(self, active: bool):
        for child in self.children:
            if child.custom_id == "mcl_start":
                child.disabled = active
            else:
                child.disabled = not active
    
    @discord.ui.button(label="▶️ НАЧАТЬ", style=discord.ButtonStyle.success, row=0, custom_id="mcl_start")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StartModal())
    
    @discord.ui.button(label="⏹️ ЗАВЕРШИТЬ", style=discord.ButtonStyle.danger, row=0, disabled=True, custom_id="mcl_end")
    async def end(self, interaction: discord.Interaction, button: discord.ui.Button):
        await mcl_manager.end_registration(str(interaction.user.id))
        
        # ✅ Лог с упоминанием
        log_channel_id = CONFIG.get('mcl_log_channel')
        if log_channel_id:
            log_channel = interaction.client.get_channel(int(log_channel_id))
            if log_channel:
                embed = discord.Embed(
                    title="📋 ЗАВЕРШЕНИЕ РЕГИСТРАЦИИ",
                    description="Регистрация MCL завершена",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                await log_channel.send(content=interaction.user.mention, embed=embed)
        
        await interaction.response.send_message("✅ Регистрация завершена", ephemeral=True)
    
    @discord.ui.button(label="➕ В ОСНОВНОЙ", style=discord.ButtonStyle.primary, row=1, disabled=True, custom_id="mcl_to_main")
    async def to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MoveToMainModal())
    
    @discord.ui.button(label="➡️ В РЕЗЕРВ", style=discord.ButtonStyle.secondary, row=1, disabled=True, custom_id="mcl_to_reserve")
    async def to_reserve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MoveToReserveModal())
    
    @discord.ui.button(label="⏫ ВСЕХ В ОСНОВНОЙ", style=discord.ButtonStyle.success, row=2, disabled=True, custom_id="mcl_move_all")
    async def move_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, msg = await mcl_manager.move_all_to_main()
        
        if success:
            log_channel_id = CONFIG.get('mcl_log_channel')
            if log_channel_id:
                log_channel = interaction.client.get_channel(int(log_channel_id))
                if log_channel:
                    embed = discord.Embed(
                        title="📋 ПЕРЕМЕЩЕНИЕ УЧАСТНИКОВ",
                        description="Все участники перемещены в основной список",
                        color=0xffa500,
                        timestamp=datetime.now()
                    )
                    await log_channel.send(content=interaction.user.mention, embed=embed)
        
        await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(label="📨 РАССЫЛКА", style=discord.ButtonStyle.danger, row=3, disabled=True, custom_id="mcl_send")
    async def send(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not mcl_manager.session_info:
            await interaction.response.send_message("❌ Нет активной регистрации", ephemeral=True)
            return
        await interaction.response.send_modal(SendModal(mcl_manager.session_info))


class PublicView(PermanentView):
    def __init__(self):
        super().__init__()
        self.set_registration_active(False)
    
    def set_registration_active(self, active: bool):
        for child in self.children:
            if child.custom_id in ["mcl_join", "mcl_leave"]:
                child.disabled = not active
    
    @discord.ui.button(label="✅ ПРИСОЕДИНИТЬСЯ", style=discord.ButtonStyle.success, row=0, disabled=True, custom_id="mcl_join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not mcl_manager.is_active():
            await interaction.response.send_message("❌ Регистрация не активна", ephemeral=True)
            return
        
        success, msg = await mcl_manager.add_participant(str(interaction.user.id), interaction.user.display_name)
        
        if success:
            # ✅ Только в канал логов
            log_channel_id = CONFIG.get('mcl_log_channel')
            if log_channel_id:
                log_channel = interaction.client.get_channel(int(log_channel_id))
                if log_channel:
                    embed = discord.Embed(
                        title="👤 НОВЫЙ УЧАСТНИК",
                        description=f"{interaction.user.display_name} присоединился к регистрации",
                        color=0x00ff00,
                        timestamp=datetime.now()
                    )
                    await log_channel.send(content=interaction.user.mention, embed=embed)
        
        await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(label="❌ ОТСОЕДИНИТЬСЯ", style=discord.ButtonStyle.danger, row=0, disabled=True, custom_id="mcl_leave")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, msg = await mcl_manager.remove_participant(str(interaction.user.id))
        
        if success:
            # ✅ Только в канал логов
            log_channel_id = CONFIG.get('mcl_log_channel')
            if log_channel_id:
                log_channel = interaction.client.get_channel(int(log_channel_id))
                if log_channel:
                    embed = discord.Embed(
                        title="👤 УЧАСТНИК ВЫШЕЛ",
                        description=f"{interaction.user.display_name} покинул регистрацию",
                        color=0xff0000,
                        timestamp=datetime.now()
                    )
                    await log_channel.send(content=interaction.user.mention, embed=embed)
        
        await interaction.response.send_message(msg, ephemeral=True)


class MoveToMainModal(discord.ui.Modal, title="➕ В ОСНОВНОЙ СПИСОК"):
    number = discord.ui.TextInput(label="Номер в резерве", placeholder="1", max_length=3)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not self.number.value.isdigit():
            await interaction.response.send_message("❌ Введите число", ephemeral=True)
            return
        
        num = int(self.number.value)
        reserve_list = db.mcl_get_registrations('reserve')
        
        if num < 1 or num > len(reserve_list):
            await interaction.response.send_message(f"❌ Номер {num} не существует", ephemeral=True)
            return
        
        reg_id, _, _ = reserve_list[num - 1]
        success, msg = await mcl_manager.move_to_main(reg_id)
        
        if success:
            log_channel_id = CONFIG.get('mcl_log_channel')
            if log_channel_id:
                log_channel = interaction.client.get_channel(int(log_channel_id))
                if log_channel:
                    user_id = reserve_list[num - 1][1]
                    embed = discord.Embed(
                        title="📋 ПЕРЕМЕЩЕНИЕ УЧАСТНИКА",
                        description=f"Участник <@{user_id}> перемещён в основной список",
                        color=0xffa500,
                        timestamp=datetime.now()
                    )
                    await log_channel.send(content=interaction.user.mention, embed=embed)
        
        await interaction.response.send_message(msg, ephemeral=True)


class MoveToReserveModal(discord.ui.Modal, title="➡️ В РЕЗЕРВ"):
    number = discord.ui.TextInput(label="Номер в основном", placeholder="1", max_length=3)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not self.number.value.isdigit():
            await interaction.response.send_message("❌ Введите число", ephemeral=True)
            return
        
        num = int(self.number.value)
        main_list = db.mcl_get_registrations('main')
        
        if num < 1 or num > len(main_list):
            await interaction.response.send_message(f"❌ Номер {num} не существует", ephemeral=True)
            return
        
        reg_id, _, _ = main_list[num - 1]
        success, msg = await mcl_manager.move_to_reserve(reg_id)
        
        if success:
            log_channel_id = CONFIG.get('mcl_log_channel')
            if log_channel_id:
                log_channel = interaction.client.get_channel(int(log_channel_id))
                if log_channel:
                    user_id = main_list[num - 1][1]
                    embed = discord.Embed(
                        title="📋 ПЕРЕВОД В РЕЗЕРВ",
                        description=f"Участник <@{user_id}> переведён в резерв",
                        color=0xffa500,
                        timestamp=datetime.now()
                    )
                    await log_channel.send(content=interaction.user.mention, embed=embed)
        
        await interaction.response.send_message(msg, ephemeral=True)