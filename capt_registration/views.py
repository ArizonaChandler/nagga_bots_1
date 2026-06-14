"""Кнопки для системы регистрации на CAPT"""
import discord
import logging
import re
from datetime import datetime
from capt_registration.base import PermanentView
from core.utils import has_access
from capt_registration.manager import capt_reg_manager
from capt_registration.capt_core import capt_core
from core.config import CONFIG
from core.database import db

logger = logging.getLogger(__name__)

# ===== МОДАЛКА ДЛЯ НАЧАЛА РЕГИСТРАЦИИ =====

class StartRegistrationModal(discord.ui.Modal, title="🎯 НАЧАТЬ РЕГИСТРАЦИЮ НА CAPT"):
    enemy = discord.ui.TextInput(
        label="Против кого играем",
        placeholder="Например: Cortez",
        max_length=100,
        required=True
    )
    
    teleport_time = discord.ui.TextInput(
        label="Время телепорта (МСК)",
        placeholder="19:30",
        max_length=5,
        required=True
    )
    
    additional_info = discord.ui.TextInput(
        label="Дополнительная информация",
        placeholder="Сбор на особе, проверка по войсу за 5 минут до начала",
        max_length=500,
        required=False,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', self.teleport_time.value):
            await interaction.response.send_message(
                "❌ Неверный формат времени. Используйте ЧЧ:ММ (например 19:30)",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            await capt_reg_manager.start_registration(
                str(interaction.user.id),
                interaction.user.display_name,
                interaction.client,
                self.enemy.value,
                self.teleport_time.value,
                self.additional_info.value
            )
            
            await interaction.followup.send(
                f"✅ Регистрация начата!\n"
                f"🎯 Противник: {self.enemy.value}\n"
                f"⏰ Телепорт в: {self.teleport_time.value} МСК",
                ephemeral=True
            )
        except Exception as e:
            print(f"❌ Ошибка в StartRegistrationModal: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)


# ===== МОДАЛКА ДЛЯ ПЕРЕМЕЩЕНИЯ В ОСНОВНОЙ =====

class MoveToMainModal(discord.ui.Modal, title="➕ Добавить в основной список"):
    number = discord.ui.TextInput(
        label="Номер участника в резерве",
        placeholder="Введите номер из списка резерва",
        max_length=3,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not self.number.value.isdigit():
            await interaction.response.send_message("❌ Введите число", ephemeral=True)
            return
        
        number = int(self.number.value)
        main_list, reserve_list = capt_reg_manager.get_lists()
        
        if number < 1 or number > len(reserve_list):
            await interaction.response.send_message(
                f"❌ В резерве только {len(reserve_list)} участников. Номер {number} не существует.",
                ephemeral=True
            )
            return
        
        reg_id, user_id, user_name = reserve_list[number - 1]
        success, msg = await capt_reg_manager.move_to_main(reg_id)
        
        await interaction.response.send_message(msg, ephemeral=True)


# ===== МОДАЛКА ДЛЯ ПЕРЕВОДА В РЕЗЕРВ =====

class MoveToReserveModal(discord.ui.Modal, title="➡️ Перевести в резерв"):
    number = discord.ui.TextInput(
        label="Номер участника в основном списке",
        placeholder="Введите номер из основного списка",
        max_length=3,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not self.number.value.isdigit():
            await interaction.response.send_message("❌ Введите число", ephemeral=True)
            return
        
        number = int(self.number.value)
        main_list, reserve_list = capt_reg_manager.get_lists()
        
        if number < 1 or number > len(main_list):
            await interaction.response.send_message(
                f"❌ В основном списке только {len(main_list)} участников. Номер {number} не существует.",
                ephemeral=True
            )
            return
        
        reg_id, user_id, user_name = main_list[number - 1]
        success, msg = await capt_reg_manager.move_to_reserve(reg_id)
        
        await interaction.response.send_message(msg, ephemeral=True)


# ===== МОДАЛКА ДЛЯ ОТПРАВКИ CAPT =====

class CaptRegSendModal(discord.ui.Modal, title="🚨 ОТПРАВКА CAPT"):
    def __init__(self, capt_info):
        super().__init__()
        self.capt_info = capt_info
        
        self.enemy = discord.ui.TextInput(
            label="👊 Противник",
            default=capt_info.get('enemy', ''),
            max_length=100,
            required=True
        )
        self.add_item(self.enemy)
        
        self.teleport_time = discord.ui.TextInput(
            label="⏰ Время телепорта",
            default=capt_info.get('event_time', ''),
            max_length=5,
            required=True
        )
        self.add_item(self.teleport_time)
        
        additional_default = capt_info.get('additional_info', '')
        self.additional_info = discord.ui.TextInput(
            label="📝 Дополнительно",
            default=additional_default if additional_default != "Нет" else "",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        self.add_item(self.additional_info)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not CONFIG.get('capt_role_id'):
            await interaction.response.send_message(
                "❌ Роль для рассылки CAPT не настроена!\n"
                "Администратор должен настроить её в настройках CAPT",
                ephemeral=True
            )
            return
        
        guild = interaction.guild
        if not guild:
            guild = interaction.client.get_guild(int(CONFIG.get('server_id', 0)))
        
        role = guild.get_role(int(CONFIG['capt_role_id']))
        if not role:
            await interaction.response.send_message("❌ Роль CAPT не найдена на сервере", ephemeral=True)
            return
        
        members = [m for m in guild.members if role in m.roles]
        if not members:
            await interaction.response.send_message("⚠️ Нет участников с этой ролью", ephemeral=True)
            return
        
        # ✅ Упоминание роли в content (если нужно упомянуть роль, выносим в content)
        role_mention = role.mention
        await interaction.response.send_message(
            f"🚀 **CAPT** | {len(members)} участников с ролью | ⚡ Запуск...",
            ephemeral=False
        )
        # Если нужно отправить отдельное сообщение с упоминанием роли:
        # await interaction.followup.send(content=role_mention, ephemeral=False)
        
        time_str = self.teleport_time.value
        message = f"👊 Противник: {self.enemy.value}"
        if self.additional_info.value:
            message += f"\n📝 {self.additional_info.value}"
        
        await capt_core.send_bulk(interaction, members, time_str, message)


# ===== КЛАСС ПОДТВЕРЖДЕНИЯ ДЛЯ ПЕРЕМЕЩЕНИЯ ВСЕХ =====

class ConfirmMoveAllView(discord.ui.View):
    def __init__(self, count: int):
        super().__init__(timeout=30)
        self.count = count
    
    @discord.ui.button(label="✅ Да, переместить всех", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            success, msg = await capt_reg_manager.move_all_to_main()
            
            if success:
                db.log_action(
                    str(interaction.user.id),
                    "CAPT_MOVE_ALL_TO_MAIN",
                    f"Перемещены все {self.count} участников из резерва в основной"
                )
                # ✅ Отправляем лог с упоминанием в канал (если нужно)
                log_channel_id = CONFIG.get('capt_log_channel')
                if log_channel_id:
                    log_channel = interaction.client.get_channel(int(log_channel_id))
                    if log_channel:
                        embed = discord.Embed(
                            title="📋 ДЕЙСТВИЕ",
                            description=f"Перемещены все участники из резерва в основной",
                            color=0xffa500,
                            timestamp=datetime.now()
                        )
                        await log_channel.send(content=interaction.user.mention, embed=embed)
            
            await interaction.followup.send(msg, ephemeral=True)
            await interaction.edit_original_response(content=f"✅ {msg}", view=None)
        except Exception as e:
            logger.error(f"Ошибка: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)
    
    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Отменено", view=None)


# ===== ЧАТ МОДЕРАЦИИ =====

class ModerationView(PermanentView):
    def __init__(self):
        super().__init__()
        self.update_buttons(registration_active=False)
        logger.debug("ModerationView создан")
    
    def update_buttons(self, registration_active: bool):
        for child in self.children:
            if child.custom_id == "capt_reg_start":
                child.disabled = registration_active  # ← АКТИВНА ТОЛЬКО КОГДА НЕТ РЕГИСТРАЦИИ!
            elif child.custom_id == "capt_reg_end":
                child.disabled = not registration_active
            else:
                child.disabled = not registration_active
    
    @discord.ui.button(label="▶️ НАЧАТЬ РЕГИСТРАЦИЮ", style=discord.ButtonStyle.success, row=0, custom_id="capt_reg_start")
    async def start_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Нажата кнопка 'Начать регистрацию' от {interaction.user}")
        await interaction.response.send_modal(StartRegistrationModal())
    
    @discord.ui.button(label="⏹️ ЗАВЕРШИТЬ РЕГИСТРАЦИЮ", style=discord.ButtonStyle.danger, row=0, disabled=True, custom_id="capt_reg_end")
    async def end_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Нажата кнопка 'Завершить регистрацию' от {interaction.user}")
        await interaction.response.defer(ephemeral=True)
        
        try:
            await capt_reg_manager.end_registration(str(interaction.user.id))
            db.log_action(str(interaction.user.id), "CAPT_REG_END", "Регистрация завершена")
            
            # ✅ Лог с упоминанием
            log_channel_id = CONFIG.get('capt_log_channel')
            if log_channel_id:
                log_channel = interaction.client.get_channel(int(log_channel_id))
                if log_channel:
                    embed = discord.Embed(
                        title="📋 ЗАВЕРШЕНИЕ РЕГИСТРАЦИИ",
                        description="Регистрация CAPT завершена",
                        color=0x00ff00,
                        timestamp=datetime.now()
                    )
                    await log_channel.send(content=interaction.user.mention, embed=embed)
            
            await interaction.followup.send("✅ Регистрация завершена! Чат очищен.", ephemeral=True)
        except Exception as e:
            print(f"❌ Ошибка при завершении: {e}")
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)
    
    @discord.ui.button(label="➕ ДОБАВИТЬ В ОСНОВНОЙ", style=discord.ButtonStyle.primary, row=1, disabled=True, custom_id="capt_reg_add_main")
    async def add_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Нажата кнопка 'Добавить в основной' от {interaction.user}")
        await interaction.response.send_modal(MoveToMainModal())
    
    @discord.ui.button(label="➡️ ПЕРЕВЕСТИ В РЕЗЕРВ", style=discord.ButtonStyle.secondary, row=1, disabled=True, custom_id="capt_reg_move_reserve")
    async def move_to_reserve(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Нажата кнопка 'Перевести в резерв' от {interaction.user}")
        await interaction.response.send_modal(MoveToReserveModal())
    
    @discord.ui.button(label="⏫ ВСЕХ В ОСНОВНОЙ", style=discord.ButtonStyle.success, row=2, disabled=True, custom_id="capt_reg_move_all")
    async def move_all_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Нажата кнопка 'Всех в основной' от {interaction.user}")
        
        if not capt_reg_manager.active_session:
            await interaction.response.send_message("❌ Нет активной регистрации", ephemeral=True)
            return
        
        main_list, reserve_list = capt_reg_manager.get_lists()
        
        if not reserve_list:
            await interaction.response.send_message("❌ В резерве нет участников", ephemeral=True)
            return
        
        view = ConfirmMoveAllView(len(reserve_list))
        await interaction.response.send_message(
            f"⚠️ Переместить **{len(reserve_list)}** участников из резерва в основной?",
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(label="📨 РАССЫЛКА В ЛС", style=discord.ButtonStyle.danger, row=3, disabled=True, custom_id="capt_reg_send")
    async def send_capt(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Нажата кнопка 'Рассылка в ЛС' от {interaction.user}")
        
        if not capt_reg_manager.active_session or not capt_reg_manager.session_info:
            await interaction.response.send_message("❌ Нет активной регистрации", ephemeral=True)
            return
        
        await interaction.response.send_modal(CaptRegSendModal(capt_reg_manager.session_info))
    
    @discord.ui.button(label="🔄 ПОВТОРНЫЙ @EVERYONE", style=discord.ButtonStyle.primary, row=4, disabled=True, custom_id="capt_reg_reeveryone")
    async def resend_everyone(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Нажата кнопка 'Повторный @everyone' от {interaction.user}")
        
        if not capt_reg_manager.active_session or not capt_reg_manager.session_info:
            await interaction.response.send_message("❌ Нет активной регистрации", ephemeral=True)
            return
        
        await capt_reg_manager._send_announcement(
            capt_reg_manager.session_info.get('enemy', ''),
            capt_reg_manager.session_info.get('event_time', ''),
            capt_reg_manager.session_info.get('additional_info', '')
        )
        
        await interaction.response.send_message("✅ Повторное @everyone оповещение отправлено!", ephemeral=True)
    
    @discord.ui.button(label="🎤 ПРОВЕРКА ПО ВОЙСУ", style=discord.ButtonStyle.success, row=4, disabled=True, custom_id="capt_reg_voicecheck")
    async def voice_check(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Нажата кнопка 'Проверка по войсу' от {interaction.user}")
        
        if not capt_reg_manager.active_session:
            await interaction.response.send_message("❌ Нет активной регистрации", ephemeral=True)
            return
        
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Ты должен находиться в голосовом канале", ephemeral=True)
            return
        
        current_voice_channel = interaction.user.voice.channel
        await interaction.response.defer(ephemeral=True)
        
        try:
            main_list, reserve_list = capt_reg_manager.get_lists()
            
            main_users = {user_id for _, user_id, _ in main_list}
            reserve_users = {user_id for _, user_id, _ in reserve_list}
            
            in_voice_from_main = []
            in_voice_from_reserve = []
            in_voice_not_registered = []
            
            for member in current_voice_channel.members:
                user_id = str(member.id)
                if user_id in main_users:
                    in_voice_from_main.append(user_id)
                elif user_id in reserve_users:
                    in_voice_from_reserve.append(user_id)
                else:
                    in_voice_not_registered.append(user_id)
            
            not_in_voice = []
            for _, user_id, _ in main_list:
                if user_id not in {str(m.id) for m in current_voice_channel.members}:
                    not_in_voice.append(user_id)
            
            embed = discord.Embed(
                title="🎤 ПРОВЕРКА ПО ВОЙСУ",
                description=f"Канал: **{current_voice_channel.name}**",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            if in_voice_from_main:
                embed.add_field(name=f"✅ В ОСНОВНОМ И В ВОЙСЕ ({len(in_voice_from_main)})", 
                              value="\n".join([f"<@{uid}>" for uid in in_voice_from_main[:20]]), inline=False)
            if in_voice_from_reserve:
                embed.add_field(name=f"⏳ В РЕЗЕРВЕ И В ВОЙСЕ ({len(in_voice_from_reserve)})", 
                              value="\n".join([f"<@{uid}>" for uid in in_voice_from_reserve[:20]]), inline=False)
            if not_in_voice:
                embed.add_field(name=f"❌ В ОСНОВНОМ НЕ В ВОЙСЕ ({len(not_in_voice)})", 
                              value="\n".join([f"<@{uid}>" for uid in not_in_voice[:20]]), inline=False)
            
            embed.set_footer(text=f"Всего в основном: {len(main_list)}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Ошибка при проверке: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)


# ===== ЧАТ ДЛЯ ВСЕХ =====

class PublicView(PermanentView):
    def __init__(self):
        super().__init__()
        logger.debug("PublicView создан")
        self.set_registration_active(False)
    
    def set_registration_active(self, active: bool):
        for child in self.children:
            if child.custom_id in ["capt_reg_join", "capt_reg_leave"]:
                child.disabled = not active
    
    @discord.ui.button(label="✅ ПРИСОЕДИНИТЬСЯ", style=discord.ButtonStyle.success, row=0, disabled=True, custom_id="capt_reg_join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Нажата кнопка 'Присоединиться' от {interaction.user}")
        
        if not capt_reg_manager.active_session:
            await interaction.response.send_message("❌ Регистрация ещё не начата", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            success, msg = await capt_reg_manager.add_participant(
                str(interaction.user.id),
                interaction.user.display_name
            )
            
            if success:
                db.log_action(str(interaction.user.id), "CAPT_JOIN", "Присоединился к регистрации")
                
                # ✅ Только в канал логов
                log_channel_id = CONFIG.get('capt_log_channel')
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
            
            await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            print(f"❌ Ошибка в join: {e}")
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)

    @discord.ui.button(label="❌ ОТСОЕДИНИТЬСЯ", style=discord.ButtonStyle.danger, row=0, disabled=True, custom_id="capt_reg_leave")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"Нажата кнопка 'Отсоединиться' от {interaction.user}")
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            success, msg = await capt_reg_manager.remove_participant(str(interaction.user.id))
            
            if success:
                db.log_action(str(interaction.user.id), "CAPT_LEAVE", "Отсоединился от регистрации")
                
                # ✅ Только в канал логов
                log_channel_id = CONFIG.get('capt_log_channel')
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
            
            await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            print(f"❌ Ошибка в leave: {e}")
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)