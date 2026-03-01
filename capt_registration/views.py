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

logger = logging.getLogger(__name__)

# ===== МОДАЛКА ДЛЯ НАЧАЛА РЕГИСТРАЦИИ =====

class StartRegistrationModal(discord.ui.Modal, title="🎯 НАЧАТЬ РЕГИСТРАЦИЮ НА CAPT"):
    """Модалка для ввода информации о CAPT"""
    
    enemy = discord.ui.TextInput(
        label="Против кого играем",
        placeholder="Например: Пираты 50",
        max_length=100,
        required=True,
        style=discord.TextStyle.short
    )
    
    teleport_time = discord.ui.TextInput(
        label="Время телепорта (МСК)",
        placeholder="19:30",
        max_length=5,
        required=True,
        style=discord.TextStyle.short
    )
    
    additional_info = discord.ui.TextInput(
        label="Дополнительная информация",
        placeholder="Сбор у банка, форма одежды и т.д.",
        max_length=500,
        required=False,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверяем формат времени
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', self.teleport_time.value):
            await interaction.response.send_message(
                "❌ Неверный формат времени. Используйте ЧЧ:ММ (например 19:30)",
                ephemeral=True
            )
            return
        
        # Сохраняем информацию о CAPT в менеджере
        capt_reg_manager.capt_info = {
            'enemy': self.enemy.value,
            'teleport_time': self.teleport_time.value,
            'additional_info': self.additional_info.value or "Нет",
            'started_by': interaction.user.mention,
            'started_by_name': interaction.user.display_name
        }
        
        # Запускаем регистрацию
        await capt_reg_manager.start_registration(
            str(interaction.user.id),
            interaction.user.display_name,
            interaction.client,
            self.enemy.value,
            self.teleport_time.value,
            self.additional_info.value
        )
        
        # Отправляем подтверждение
        await interaction.response.send_message(
            f"✅ Регистрация начата!\n"
            f"🎯 Противник: {self.enemy.value}\n"
            f"⏰ Телепорт в: {self.teleport_time.value} МСК",
            ephemeral=True
        )


# ===== МОДАЛКА ДЛЯ ПЕРЕМЕЩЕНИЯ В ОСНОВНОЙ =====

class MoveToMainModal(discord.ui.Modal, title="➕ Добавить в основной список"):
    """Модалка для добавления пользователя в основной список по номеру"""
    
    number = discord.ui.TextInput(
        label="Номер участника в резерве",
        placeholder="Введите номер из списка резерва",
        max_length=3,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверяем что ввели число
        if not self.number.value.isdigit():
            await interaction.response.send_message(
                "❌ Введите число",
                ephemeral=True
            )
            return
        
        number = int(self.number.value)
        
        # Получаем текущие списки
        main_list, reserve_list = capt_reg_manager.get_lists()
        
        # Проверяем, что номер существует в резерве
        if number < 1 or number > len(reserve_list):
            await interaction.response.send_message(
                f"❌ В резерве только {len(reserve_list)} участников. Номер {number} не существует.",
                ephemeral=True
            )
            return
        
        # Получаем registration_id по номеру из резерва
        reg_id, user_id, user_name = reserve_list[number - 1]
        
        # Перемещаем в основной список по ID записи
        success, msg = await capt_reg_manager.move_to_main(
            str(interaction.user.id),
            reg_id,
            interaction.client
        )
        
        await interaction.response.send_message(msg, ephemeral=True)


# ===== МОДАЛКА ДЛЯ ПЕРЕВОДА В РЕЗЕРВ =====

class MoveToReserveModal(discord.ui.Modal, title="➡️ Перевести в резерв"):
    """Модалка для перевода пользователя в резерв по номеру"""
    
    number = discord.ui.TextInput(
        label="Номер участника в основном списке",
        placeholder="Введите номер из основного списка",
        max_length=3,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверяем что ввели число
        if not self.number.value.isdigit():
            await interaction.response.send_message(
                "❌ Введите число",
                ephemeral=True
            )
            return
        
        number = int(self.number.value)
        
        # Получаем текущие списки
        main_list, reserve_list = capt_reg_manager.get_lists()
        
        # Проверяем, что номер существует в основном списке
        if number < 1 or number > len(main_list):
            await interaction.response.send_message(
                f"❌ В основном списке только {len(main_list)} участников. Номер {number} не существует.",
                ephemeral=True
            )
            return
        
        # Получаем registration_id по номеру из основного списка
        reg_id, user_id, user_name = main_list[number - 1]
        
        # Перемещаем в резерв по ID записи
        success, msg = await capt_reg_manager.move_to_reserve(
            str(interaction.user.id),
            reg_id,
            interaction.client
        )
        
        await interaction.response.send_message(msg, ephemeral=True)


# ===== МОДАЛКА ДЛЯ ОТПРАВКИ CAPT =====

class CaptRegSendModal(discord.ui.Modal, title="🚨 ОТПРАВКА CAPT"):
    """Модалка для отправки CAPT участникам"""
    
    def __init__(self, capt_info):
        super().__init__()
        self.capt_info = capt_info
        
        # Предзаполняем поля данными из регистрации
        self.enemy = discord.ui.TextInput(
            label="👊 Противник",
            default=capt_info['enemy'],
            max_length=100,
            required=True
        )
        self.add_item(self.enemy)
        
        self.teleport_time = discord.ui.TextInput(
            label="⏰ Время телепорта",
            default=capt_info['teleport_time'],
            max_length=5,
            required=True
        )
        self.add_item(self.teleport_time)
        
        self.additional_info = discord.ui.TextInput(
            label="📝 Дополнительно",
            default=capt_info['additional_info'] if capt_info['additional_info'] != "Нет" else "",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        self.add_item(self.additional_info)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверяем наличие роли
        if not CONFIG['capt_role_id']:
            await interaction.response.send_message(
                "❌ Роль для рассылки CAPT не настроена!\n"
                "Администратор должен настроить её в !settings → Глобальные настройки → 🎭 Роль для рассылки CAPT",
                ephemeral=True
            )
            return
        
        if not CONFIG['capt_channel_id']:
            await interaction.response.send_message(
                "❌ Канал для ошибок CAPT не настроен!",
                ephemeral=True
            )
            return
        
        # Получаем роль
        guild = interaction.guild
        if not guild:
            guild = interaction.client.get_guild(int(CONFIG['server_id']))
        
        role = guild.get_role(int(CONFIG['capt_role_id']))
        if not role:
            await interaction.response.send_message(
                "❌ Роль CAPT не найдена на сервере",
                ephemeral=True
            )
            return
        
        # Получаем участников с ролью
        members = [m for m in guild.members if role in m.roles]
        if not members:
            await interaction.response.send_message(
                "⚠️ Нет участников с этой ролью",
                ephemeral=True
            )
            return
        
        # Отправляем подтверждение
        await interaction.response.send_message(
            f"🚀 **CAPT** | {len(members)} участников с ролью {role.mention} | ⚡ Запуск...",
            ephemeral=False
        )
        
        # Формируем сообщение из данных
        time_str = self.teleport_time.value
        message = f"👊 Противник: {self.enemy.value}"
        if self.additional_info.value:
            message += f"\n📝 {self.additional_info.value}"
        
        # Запускаем рассылку
        await capt_core.send_bulk(interaction, members, time_str, message)


# ===== ЧАТ МОДЕРАЦИИ (ДЛЯ АДМИНОВ) =====

class ModerationView(PermanentView):
    """View для чата модерации - кнопки управления (доступны всем в чате)"""
    
    def __init__(self):
        super().__init__()
        # По умолчанию все кнопки неактивны (кроме "Начать")
        self.update_buttons(registration_active=False)
        logger.debug("ModerationView создан")
    
    def update_buttons(self, registration_active: bool):
        """Обновить состояние кнопок в зависимости от активности регистрации"""
        for child in self.children:
            # Кнопка "Начать регистрацию" всегда активна
            if child.custom_id == "capt_reg_start":
                child.disabled = False
            # Все остальные кнопки активны только когда регистрация идёт
            else:
                child.disabled = not registration_active
        logger.debug(f"Кнопки модерации {'активированы' if registration_active else 'деактивированы'}")
    
    @discord.ui.button(
        label="▶️ НАЧАТЬ РЕГИСТРАЦИЮ", 
        style=discord.ButtonStyle.success,
        emoji="▶️",
        row=0,
        custom_id="capt_reg_start"
    )
    async def start_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Начать регистрацию (доступно всем в чате)"""
        logger.info(f"Нажата кнопка 'Начать регистрацию' от {interaction.user}")
        
        # УБРАНА ПРОВЕРКА has_access
        await interaction.response.send_modal(StartRegistrationModal())
    
    @discord.ui.button(
        label="⏹️ ЗАВЕРШИТЬ РЕГИСТРАЦИЮ", 
        style=discord.ButtonStyle.danger,
        emoji="⏹️",
        row=0,
        disabled=True,
        custom_id="capt_reg_end"
    )
    async def end_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Завершить регистрацию (доступно всем в чате)"""
        logger.info(f"Нажата кнопка 'Завершить регистрацию' от {interaction.user}")
        
        # УБРАНА ПРОВЕРКА has_access
        
        try:
            # Сначала отвечаем, чтобы не было ошибки взаимодействия
            await interaction.response.send_message(
                "🧹 Завершение регистрации и очистка чата...",
                ephemeral=True
            )
            
            # Затем выполняем очистку
            await capt_reg_manager.end_registration(str(interaction.user.id), interaction.client)
            
            # Деактивируем кнопки после завершения
            self.update_buttons(registration_active=False)
            await interaction.message.edit(view=self)
            
            # Редактируем наше эфемерное сообщение
            await interaction.edit_original_response(
                content="✅ Регистрация завершена! Чат очищен."
            )
            
        except Exception as e:
            logger.error(f"Ошибка при завершении регистрации: {e}", exc_info=True)
            try:
                await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)
            except:
                pass
    
    @discord.ui.button(
        label="➕ ДОБАВИТЬ В ОСНОВНОЙ", 
        style=discord.ButtonStyle.primary,
        emoji="➕",
        row=1,
        disabled=True,
        custom_id="capt_reg_add_main"
    )
    async def add_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Добавить пользователя в основной список (доступно всем в чате)"""
        logger.info(f"Нажата кнопка 'Добавить в основной' от {interaction.user}")
        
        # УБРАНА ПРОВЕРКА has_access
        await interaction.response.send_modal(MoveToMainModal())
    
    @discord.ui.button(
        label="➡️ ПЕРЕВЕСТИ В РЕЗЕРВ", 
        style=discord.ButtonStyle.secondary,
        emoji="➡️",
        row=1,
        disabled=True,
        custom_id="capt_reg_move_reserve"
    )
    async def move_to_reserve(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Перевести пользователя в резерв (доступно всем в чате)"""
        logger.info(f"Нажата кнопка 'Перевести в резерв' от {interaction.user}")
        
        # УБРАНА ПРОВЕРКА has_access
        await interaction.response.send_modal(MoveToReserveModal())
    
    @discord.ui.button(
        label="📨 РАССЫЛКА В ЛС", 
        style=discord.ButtonStyle.danger,
        emoji="📨",
        row=2,
        disabled=True,
        custom_id="capt_reg_send"
    )
    async def send_capt(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отправить CAPT участникам (доступно всем в чате)"""
        logger.info(f"Нажата кнопка 'Рассылка в ЛС' от {interaction.user}")
        
        # УБРАНА ПРОВЕРКА has_access
        
        # Проверяем, активна ли регистрация
        if not capt_reg_manager.active_session or not capt_reg_manager.capt_info:
            await interaction.response.send_message(
                "❌ Нет активной регистрации",
                ephemeral=True
            )
            return
        
        await interaction.response.send_modal(CaptRegSendModal(capt_reg_manager.capt_info))
    
    @discord.ui.button(
        label="🔄 ПОВТОРНЫЙ @EVERYONE", 
        style=discord.ButtonStyle.primary,
        emoji="🔄",
        row=3,
        disabled=True,
        custom_id="capt_reg_reeveryone"
    )
    async def resend_everyone(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Повторно отправить @everyone оповещение (доступно всем в чате)"""
        logger.info(f"Нажата кнопка 'Повторный @everyone' от {interaction.user}")
        
        # УБРАНА ПРОВЕРКА has_access
        
        # Проверяем, активна ли регистрация
        if not capt_reg_manager.active_session or not capt_reg_manager.capt_info:
            await interaction.response.send_message(
                "❌ Нет активной регистрации",
                ephemeral=True
            )
            return
        
        # Отправляем повторное оповещение
        await capt_reg_manager._send_capt_announcement(interaction.client)
        
        await interaction.response.send_message(
            "✅ Повторное @everyone оповещение отправлено!",
            ephemeral=True
        )
    
    @discord.ui.button(
        label="🎤 ПРОВЕРКА ПО ВОЙСУ", 
        style=discord.ButtonStyle.success,
        emoji="🎤",
        row=3,
        disabled=True,
        custom_id="capt_reg_voicecheck"
    )
    async def voice_check(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Проверить участников в текущем войс-канале"""
        logger.info(f"Нажата кнопка 'Проверка по войсу' от {interaction.user}")
        
        # Проверяем, активна ли регистрация
        if not capt_reg_manager.active_session:
            await interaction.response.send_message(
                "❌ Нет активной регистрации",
                ephemeral=True
            )
            return
        
        # Проверяем, находится ли пользователь в войс-канале
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ Ты должен находиться в голосовом канале, чтобы использовать эту кнопку",
                ephemeral=True
            )
            return
        
        # Получаем войс-канал, в котором находится пользователь
        current_voice_channel = interaction.user.voice.channel
        
        # Отвечаем сразу, чтобы не было ошибки взаимодействия
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Получаем списки участников (теперь с ID записей)
            main_list, reserve_list = capt_reg_manager.get_lists()
            # main_list = [(id, user_id, user_name), ...]
            # reserve_list = [(id, user_id, user_name), ...]
            
            # Создаем множества для быстрого поиска
            main_users = {user_id for _, user_id, _ in main_list}
            reserve_users = {user_id for _, user_id, _ in reserve_list}
            all_registered_users = main_users | reserve_users  # Объединение множеств
            
            # Собираем информацию о всех участниках в текущем войс-канале
            in_voice_from_main = []      # Из основного списка
            in_voice_from_reserve = []   # Из резерва
            in_voice_not_registered = [] # Не зарегистрированы вообще
            
            for member in current_voice_channel.members:
                user_id = str(member.id)
                user_name = member.display_name
                
                if user_id in main_users:
                    in_voice_from_main.append((user_id, user_name))
                elif user_id in reserve_users:
                    in_voice_from_reserve.append((user_id, user_name))
                else:
                    in_voice_not_registered.append((user_id, user_name))
            
            # Проверяем, кто из основного списка не в этом войсе
            not_in_voice = []
            for _, user_id, user_name in main_list:
                if user_id not in {str(m.id) for m in current_voice_channel.members}:
                    not_in_voice.append((user_id, user_name))
            
            # Создаем embed с результатами
            from datetime import datetime
            embed = discord.Embed(
                title="🎤 ПРОВЕРКА ПО ВОЙСУ",
                description=f"Проверка в канале: **{current_voice_channel.name}**",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            # Из основного списка в войсе
            if in_voice_from_main:
                in_voice_text = ""
                for i, (user_id, user_name) in enumerate(in_voice_from_main, 1):
                    in_voice_text += f"{i}. <@{user_id}> — {user_name}\n"
                embed.add_field(
                    name=f"✅ ИЗ ОСНОВНОГО СПИСКА В ВОЙСЕ ({len(in_voice_from_main)})",
                    value=in_voice_text,
                    inline=False
                )
            
            # Из резерва в войсе
            if in_voice_from_reserve:
                reserve_voice_text = ""
                for i, (user_id, user_name) in enumerate(in_voice_from_reserve, 1):
                    reserve_voice_text += f"{i}. <@{user_id}> — {user_name}\n"
                embed.add_field(
                    name=f"⏳ ИЗ РЕЗЕРВА В ВОЙСЕ ({len(in_voice_from_reserve)})",
                    value=reserve_voice_text,
                    inline=False
                )
            
            # Не зарегистрированные в войсе
            if in_voice_not_registered:
                not_reg_text = ""
                for i, (user_id, user_name) in enumerate(in_voice_not_registered, 1):
                    not_reg_text += f"{i}. <@{user_id}> — {user_name}\n"
                embed.add_field(
                    name=f"⚪ В ВОЙСЕ, НО НЕ ЗАРЕГИСТРИРОВАНЫ ({len(in_voice_not_registered)})",
                    value=not_reg_text,
                    inline=False
                )
            
            # Из основного списка не в войсе
            if not_in_voice:
                not_in_voice_text = ""
                for i, (user_id, user_name) in enumerate(not_in_voice, 1):
                    not_in_voice_text += f"{i}. <@{user_id}> — {user_name}\n"
                embed.add_field(
                    name=f"❌ ИЗ ОСНОВНОГО СПИСКА НЕ В ВОЙСЕ ({len(not_in_voice)})",
                    value=not_in_voice_text,
                    inline=False
                )
            
            # Информация о текущем войс-канале
            member_mentions = []
            for member in current_voice_channel.members[:5]:  # Показываем первых 5
                member_mentions.append(member.mention)
            
            voice_info = f"👥 **Всего в канале:** {len(current_voice_channel.members)}"
            if member_mentions:
                voice_info += f"\n{', '.join(member_mentions)}"
                if len(current_voice_channel.members) > 5:
                    voice_info += f" и ещё {len(current_voice_channel.members) - 5}"
            
            embed.add_field(
                name=f"🔊 Текущий войс-канал",
                value=voice_info,
                inline=False
            )
            
            # Если вообще никого нет
            if not in_voice_from_main and not in_voice_from_reserve and not in_voice_not_registered and not not_in_voice:
                embed.description += "\n\nВ этом войс-канале никого нет, а список участников пуст."
            
            embed.set_footer(text=f"Всего в основном списке: {len(main_list)} • Проверка: {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Ошибка при проверке по войсу: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Ошибка при проверке: {e}",
                ephemeral=True
            )

# ===== ЧАТ ДЛЯ ВСЕХ =====

class PublicView(PermanentView):
    """View для публичного чата - 2 кнопки"""
    
    def __init__(self):
        super().__init__()
        logger.debug("PublicView создан")
        # По умолчанию кнопки неактивны
        self.set_registration_active(False)
    
    def set_registration_active(self, active: bool):
        """Активировать/деактивировать кнопки"""
        for child in self.children:
            if child.custom_id in ["capt_reg_join", "capt_reg_leave"]:
                child.disabled = not active
        logger.debug(f"Кнопки публичного чата {'активированы' if active else 'деактивированы'}")
    
    @discord.ui.button(
        label="✅ ПРИСОЕДИНИТЬСЯ", 
        style=discord.ButtonStyle.success,
        emoji="✅",
        row=0,
        disabled=True,
        custom_id="capt_reg_join"
    )
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Присоединиться к регистрации"""
        logger.info(f"Нажата кнопка 'Присоединиться' от {interaction.user}")
        
        # Проверяем, активна ли регистрация
        if not capt_reg_manager.active_session:
            await interaction.response.send_message(
                "❌ Регистрация ещё не начата", 
                ephemeral=True
            )
            return
        
        success, msg = await capt_reg_manager.add_participant(
            str(interaction.user.id),
            interaction.user.display_name,
            interaction.client
        )
        
        await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(
        label="❌ ОТСОЕДИНИТЬСЯ", 
        style=discord.ButtonStyle.danger,
        emoji="❌",
        row=0,
        disabled=True,
        custom_id="capt_reg_leave"
    )
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отсоединиться от регистрации"""
        logger.info(f"Нажата кнопка 'Отсоединиться' от {interaction.user}")
        
        success, msg = await capt_reg_manager.remove_participant(
            str(interaction.user.id),
            interaction.client
        )
        
        await interaction.response.send_message(msg, ephemeral=True)