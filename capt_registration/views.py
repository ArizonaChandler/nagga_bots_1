"""Кнопки для системы регистрации на CAPT"""
import discord
import logging
from capt_registration.base import PermanentView
from core.utils import is_admin
from capt_registration.manager import capt_reg_manager

logger = logging.getLogger(__name__)

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
            # Кнопка "Завершить регистрацию" активна только когда регистрация идёт
            elif child.custom_id == "capt_reg_end":
                child.disabled = not registration_active
            # Кнопки перемещения активны только когда регистрация идёт
            elif child.custom_id in ["capt_reg_to_main", "capt_reg_to_reserve"]:
                child.disabled = not registration_active
    
    @discord.ui.button(
        label="▶️ НАЧАТЬ РЕГИСТРАЦИЮ", 
        style=discord.ButtonStyle.success,
        emoji="▶️",
        row=0,
        custom_id="capt_reg_start"
    )
    async def start_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Начать регистрацию (только для админов)"""
        logger.info(f"Нажата кнопка 'Начать регистрацию' от {interaction.user}")
        
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        try:
            await capt_reg_manager.start_registration(
                str(interaction.user.id),
                interaction.user.display_name,
                interaction.client
            )
            
            # Активируем кнопки после старта
            self.update_buttons(registration_active=True)
            await interaction.message.edit(view=self)
            
            await interaction.response.send_message(
                "✅ Регистрация начата! Кнопки управления активированы.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Ошибка при старте регистрации: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
    
    @discord.ui.button(
        label="⏹️ ЗАВЕРШИТЬ РЕГИСТРАЦИЮ", 
        style=discord.ButtonStyle.danger,
        emoji="⏹️",
        row=0,
        disabled=True,  # По умолчанию неактивна
        custom_id="capt_reg_end"
    )
    async def end_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Завершить регистрацию (очистить всё)"""
        logger.info(f"Нажата кнопка 'Завершить регистрацию' от {interaction.user}")
        
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
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
        label="🔢 ПЕРЕМЕСТИТЬ ПО НОМЕРУ", 
        style=discord.ButtonStyle.primary,
        emoji="🔢",
        row=1,
        disabled=True,  # По умолчанию неактивна
        custom_id="capt_reg_move"
    )
    async def move_by_number(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Переместить участника по номеру из списка"""
        logger.info(f"Нажата кнопка 'Переместить по номеру' от {interaction.user}")
        
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        await interaction.response.send_modal(MoveByNumberModal())


class MoveByNumberModal(discord.ui.Modal, title="🔢 Переместить участника"):
    """Модалка для перемещения по номеру из списка"""
    
    number = discord.ui.TextInput(
        label="Номер участника в списке",
        placeholder="Например: 3",
        max_length=3,
        required=True
    )
    
    target_list = discord.ui.TextInput(
        label="Куда переместить (основной/резерв)",
        placeholder="Введите 'основной' или 'резерв'",
        max_length=10,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Получаем текущие списки
        main_list, reserve_list = capt_reg_manager.get_lists()
        
        try:
            num = int(self.number.value)
            target = self.target_list.value.lower().strip()
            
            # Определяем, откуда перемещаем
            user_id = None
            user_name = None
            from_list = None
            
            # Проверяем в основном списке
            if 1 <= num <= len(main_list):
                user_id, user_name = main_list[num-1]
                from_list = 'main'
            # Проверяем в резерве
            elif 1 <= num <= len(reserve_list):
                user_id, user_name = reserve_list[num-1]
                from_list = 'reserve'
            else:
                await interaction.response.send_message(
                    f"❌ Номер {num} не найден в списках",
                    ephemeral=True
                )
                return
            
            # Определяем, куда перемещать
            if target in ['основной', 'осн', 'main']:
                if from_list == 'main':
                    await interaction.response.send_message(
                        f"❌ Участник уже в основном списке",
                        ephemeral=True
                    )
                    return
                success, msg = await capt_reg_manager.move_to_main(
                    str(interaction.user.id),
                    user_id,
                    interaction.client
                )
            elif target in ['резерв', 'рез', 'reserve']:
                if from_list == 'reserve':
                    await interaction.response.send_message(
                        f"❌ Участник уже в резерве",
                        ephemeral=True
                    )
                    return
                success, msg = await capt_reg_manager.move_to_reserve(
                    str(interaction.user.id),
                    user_id,
                    interaction.client
                )
            else:
                await interaction.response.send_message(
                    "❌ Неверно указано место. Используйте 'основной' или 'резерв'",
                    ephemeral=True
                )
                return
            
            await interaction.response.send_message(msg, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)


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