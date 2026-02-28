"""Кнопки для системы регистрации на CAPT"""
import discord
import logging
from capt_registration.base import PermanentView
from core.utils import has_access, is_admin
from capt_registration.manager import capt_reg_manager

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
        import re
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


# ===== ЧАТ МОДЕРАЦИИ (для админов) =====

class ModerationView(PermanentView):
    """View для чата модерации - кнопки управления"""
    
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
        """Начать регистрацию (для всех с доступом)"""
        logger.info(f"Нажата кнопка 'Начать регистрацию' от {interaction.user}")
        
        # Проверяем есть ли доступ к боту (has_access)
        if not await has_access(str(interaction.user.id)):
            await interaction.response.send_message("❌ У вас нет доступа к боту", ephemeral=True)
            return
        
        # Открываем модалку для ввода информации
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
        """Завершить регистрацию (очистить всё)"""
        logger.info(f"Нажата кнопка 'Завершить регистрацию' от {interaction.user}")
        
        # Проверяем есть ли доступ к боту
        if not await has_access(str(interaction.user.id)):
            await interaction.response.send_message("❌ У вас нет доступа к боту", ephemeral=True)
            return
        
        try:
            await capt_reg_manager.end_registration(str(interaction.user.id), interaction.client)
            
            # Деактивируем кнопки после завершения
            self.update_buttons(registration_active=False)
            await interaction.message.edit(view=self)
            
            await interaction.response.send_message(
                "✅ Регистрация завершена! Все списки очищены.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Ошибка при завершении регистрации: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
    
    @discord.ui.button(
        label="➕ ДОБАВИТЬ В ОСНОВНОЙ", 
        style=discord.ButtonStyle.primary,
        emoji="➕",
        row=1,
        disabled=True,
        custom_id="capt_reg_add_main"
    )
    async def add_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Добавить пользователя в основной список"""
        logger.info(f"Нажата кнопка 'Добавить в основной' от {interaction.user}")
        
        if not await has_access(str(interaction.user.id)):
            await interaction.response.send_message("❌ У вас нет доступа к боту", ephemeral=True)
            return
        
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
        """Перевести пользователя в резерв"""
        logger.info(f"Нажата кнопка 'Перевести в резерв' от {interaction.user}")
        
        if not await has_access(str(interaction.user.id)):
            await interaction.response.send_message("❌ У вас нет доступа к боту", ephemeral=True)
            return
        
        await interaction.response.send_modal(MoveToReserveModal())


class MoveToMainModal(discord.ui.Modal, title="➕ Добавить в основной список"):
    """Модалка для добавления пользователя в основной список по номеру из резерва"""
    
    reserve_number = discord.ui.TextInput(
        label="Номер участника из резервного списка",
        placeholder="Например: 2",
        max_length=3,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверяем что ввели число
        if not self.reserve_number.value.isdigit():
            await interaction.response.send_message(
                "❌ Введите число",
                ephemeral=True
            )
            return
        
        number = int(self.reserve_number.value)
        
        # Получаем текущие списки
        main_list, reserve_list = capt_reg_manager.get_lists()
        
        # Проверяем, что номер существует в резерве
        if number < 1 or number > len(reserve_list):
            await interaction.response.send_message(
                f"❌ В резерве только {len(reserve_list)} участников. Номер {number} не существует.",
                ephemeral=True
            )
            return
        
        # Получаем данные участника по номеру из резерва
        target_user_id, target_user_name = reserve_list[number - 1]
        
        # Перемещаем в основной список
        success, msg = await capt_reg_manager.move_to_main(
            str(interaction.user.id),
            target_user_id,
            interaction.client
        )
        
        await interaction.response.send_message(msg, ephemeral=True)


class MoveToReserveModal(discord.ui.Modal, title="➡️ Перевести в резерв"):
    """Модалка для перевода пользователя в резерв по номеру из основного списка"""
    
    main_number = discord.ui.TextInput(
        label="Номер участника из основного списка",
        placeholder="Например: 1",
        max_length=3,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Проверяем что ввели число
        if not self.main_number.value.isdigit():
            await interaction.response.send_message(
                "❌ Введите число",
                ephemeral=True
            )
            return
        
        number = int(self.main_number.value)
        
        # Получаем текущие списки
        main_list, reserve_list = capt_reg_manager.get_lists()
        
        # Проверяем, что номер существует в основном списке
        if number < 1 or number > len(main_list):
            await interaction.response.send_message(
                f"❌ В основном списке только {len(main_list)} участников. Номер {number} не существует.",
                ephemeral=True
            )
            return
        
        # Получаем данные участника по номеру из основного списка
        target_user_id, target_user_name = main_list[number - 1]
        
        # Перемещаем в резерв
        success, msg = await capt_reg_manager.move_to_reserve(
            str(interaction.user.id),
            target_user_id,
            interaction.client
        )
        
        await interaction.response.send_message(msg, ephemeral=True)


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