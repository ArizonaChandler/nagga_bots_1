"""Кнопки для системы регистрации на CAPT"""
import discord
from core.menus import BaseMenuView
from core.utils import has_access, is_admin
from capt_registration.manager import capt_reg_manager

# ===== ЧАТ МОДЕРАЦИИ (для админов) =====

class ModerationView(BaseMenuView):
    """View для чата модерации - 4 кнопки"""
    
    def __init__(self):
        # Убираем проверку user_id, так как view постоянное
        super().__init__(None, None)
        self.timeout = None  # Бесконечный таймаут
    
    @discord.ui.button(
        label="▶️ НАЧАТЬ РЕГИСТРАЦИЮ", 
        style=discord.ButtonStyle.success,
        emoji="▶️",
        row=0
    )
    async def start_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Начать регистрацию (только для админов)"""
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        await capt_reg_manager.start_registration(
            str(interaction.user.id),
            interaction.user.display_name,
            interaction.client
        )
        
        await interaction.response.send_message(
            "✅ Регистрация начата! Кнопки 'Присоединиться' активированы.",
            ephemeral=True
        )
    
    @discord.ui.button(
        label="⏹️ ЗАВЕРШИТЬ РЕГИСТРАЦИЮ", 
        style=discord.ButtonStyle.danger,
        emoji="⏹️",
        row=0
    )
    async def end_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Завершить регистрацию (очистить всё)"""
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        await capt_reg_manager.end_registration(str(interaction.user.id), interaction.client)
        
        await interaction.response.send_message(
            "✅ Регистрация завершена! Все списки очищены.",
            ephemeral=True
        )
    
    @discord.ui.button(
        label="⬆️ ПЕРЕВЕСТИ В ОСНОВНОЙ", 
        style=discord.ButtonStyle.primary,
        emoji="⬆️",
        row=1
    )
    async def move_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Перевести пользователя в основной список"""
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        # Отправляем модалку для ввода ID пользователя
        await interaction.response.send_modal(MoveUserModal('main'))
    
    @discord.ui.button(
        label="⬇️ ПЕРЕВЕСТИ В РЕЗЕРВ", 
        style=discord.ButtonStyle.secondary,
        emoji="⬇️",
        row=1
    )
    async def move_to_reserve(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Перевести пользователя в резерв"""
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        await interaction.response.send_modal(MoveUserModal('reserve'))


class MoveUserModal(discord.ui.Modal, title="🔄 Переместить пользователя"):
    def __init__(self, target_list: str):
        super().__init__()
        self.target_list = target_list  # 'main' или 'reserve'
    
    user_id = discord.ui.TextInput(
        label="ID пользователя или упоминание",
        placeholder="123456789012345678 или @user",
        max_length=30
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Извлекаем ID из упоминания если нужно
        user_input = self.user_id.value.strip()
        if user_input.startswith('<@') and user_input.endswith('>'):
            user_id = user_input.replace('<@', '').replace('>', '').replace('!', '')
        else:
            user_id = user_input
        
        if self.target_list == 'main':
            success, msg = await capt_reg_manager.move_to_main(
                str(interaction.user.id),
                user_id,
                interaction.client
            )
        else:
            success, msg = await capt_reg_manager.move_to_reserve(
                str(interaction.user.id),
                user_id,
                interaction.client
            )
        
        await interaction.response.send_message(msg, ephemeral=True)


# ===== ЧАТ ДЛЯ ВСЕХ =====

class PublicView(BaseMenuView):
    """View для публичного чата - 2 кнопки"""
    
    def __init__(self):
        super().__init__(None, None)
        self.timeout = None  # Бесконечный таймаут
        self.update_button_states()
    
    def update_button_states(self):
        """Обновить состояние кнопок в зависимости от активности сессии"""
        # Эта функция будет вызываться при старте/завершении регистрации
        pass
    
    @discord.ui.button(
        label="✅ ПРИСОЕДИНИТЬСЯ", 
        style=discord.ButtonStyle.success,
        emoji="✅",
        row=0,
        disabled=True  # По умолчанию disabled, активируется при старте
    )
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Присоединиться к регистрации"""
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
        disabled=True  # По умолчанию disabled, активируется при старте
    )
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отсоединиться от регистрации"""
        success, msg = await capt_reg_manager.remove_participant(
            str(interaction.user.id),
            interaction.client
        )
        
        await interaction.response.send_message(msg, ephemeral=True)
    
    async def set_registration_active(self, active: bool):
        """Активировать/деактивировать кнопки"""
        for child in self.children:
            if child.label in ["✅ ПРИСОЕДИНИТЬСЯ", "❌ ОТСОЕДИНИТЬСЯ"]:
                child.disabled = not active