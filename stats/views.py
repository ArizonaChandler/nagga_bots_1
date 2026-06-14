"""Кнопки для статистики и бекапа"""
import discord
import json
from datetime import datetime
from stats.base import PermanentView, ConfirmView
from stats.manager import stats_manager
from core.utils import is_admin, is_super_admin
from core.database import db
from core.config import CONFIG


class StatsPanelView(PermanentView):
    """Главная панель статистики"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(label="📊 Статистика сегодня", style=discord.ButtonStyle.primary, row=0)
    async def today_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать статистику за сегодня"""
        today = datetime.now().date().isoformat()
        stats = db.get_stats_for_date(today)
        
        if not stats:
            await interaction.response.send_message("❌ Статистика за сегодня ещё не собрана", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📊 СТАТИСТИКА ЗА {datetime.now().strftime('%d.%m.%Y')}",
            color=0x7289da,
            timestamp=datetime.now()
        )
        embed.add_field(name="📈 Новых участников", value=f"**{stats.get('new_members', 0)}**", inline=True)
        embed.add_field(name="📉 Покинуло", value=f"**{stats.get('left_members', 0)}**", inline=True)
        embed.add_field(name="📝 Новых заявок", value=f"**{stats.get('new_applications', 0)}**", inline=True)
        embed.add_field(name="✅ Принято заявок", value=f"**{stats.get('accepted_applications', 0)}**", inline=True)
        embed.add_field(name="🎯 CAPT", value=f"**{stats.get('capt_registrations', 0)}**", inline=True)
        embed.add_field(name="🎯 MCL/ВЗМ", value=f"**{stats.get('mcl_registrations', 0)}**", inline=True)
        embed.add_field(name="📅 МП", value=f"**{stats.get('mp_takes', 0)}**", inline=True)
        embed.add_field(name="🎙️ Пик в войсе", value=f"**{stats.get('max_voice_online', 0)}**", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🏆 Топ участников", style=discord.ButtonStyle.primary, row=0)
    async def top_users(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать топ участников"""
        # TODO: реализовать топ по активности
        await interaction.response.send_message("🏆 Функция в разработке", ephemeral=True)
    
    @discord.ui.button(label="📜 История по дням", style=discord.ButtonStyle.secondary, row=1)
    async def history_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать историю статистики"""
        await interaction.response.send_modal(StatsHistoryModal())
    
    @discord.ui.button(label="👤 Статистика пользователя", style=discord.ButtonStyle.secondary, row=1)
    async def user_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Статистика по пользователю"""
        await interaction.response.send_modal(UserStatsModal())


class StatsHistoryModal(discord.ui.Modal, title="📜 СТАТИСТИКА ПО ДНЯМ"):
    days = discord.ui.TextInput(
        label="Количество дней",
        placeholder="7",
        default="7",
        max_length=3,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            days = int(self.days.value)
            if days < 1 or days > 30:
                await interaction.response.send_message("❌ Введите число от 1 до 30", ephemeral=True)
                return
            
            stats_list = db.get_stats_for_last_days(days)
            
            if not stats_list:
                await interaction.response.send_message("❌ Нет данных за указанный период", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"📊 СТАТИСТИКА ЗА ПОСЛЕДНИЕ {days} ДНЕЙ",
                color=0x7289da,
                timestamp=datetime.now()
            )
            
            total_new = 0
            total_accepted = 0
            total_capt = 0
            
            for stat in stats_list:
                total_new += stat.get('new_members', 0)
                total_accepted += stat.get('accepted_applications', 0)
                total_capt += stat.get('capt_registrations', 0)
            
            embed.add_field(name="📈 Всего новых", value=f"**{total_new}**", inline=True)
            embed.add_field(name="✅ Всего принято", value=f"**{total_accepted}**", inline=True)
            embed.add_field(name="🎯 Всего CAPT", value=f"**{total_capt}**", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)


class UserStatsModal(discord.ui.Modal, title="👤 СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ"):
    user_id = discord.ui.TextInput(
        label="ID пользователя",
        placeholder="123456789012345678",
        max_length=20,
        required=True
    )
    days = discord.ui.TextInput(
        label="Количество дней",
        placeholder="7",
        default="7",
        max_length=3,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value)
            days = int(self.days.value)
            
            user_stats = await stats_manager.get_user_stats(uid, days)
            
            if not user_stats:
                await interaction.response.send_message("❌ Нет данных по этому пользователю", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"👤 СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ",
                description=f"<@{uid}>",
                color=0x7289da,
                timestamp=datetime.now()
            )
            embed.add_field(name="📝 Сообщений", value=f"**{user_stats.get('messages', 0)}**", inline=True)
            embed.add_field(name="🎙️ Минут в войсе", value=f"**{user_stats.get('voice_minutes', 0)}**", inline=True)
            embed.add_field(name="📅 Дней", value=f"**{days}**", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Введите корректный ID", ephemeral=True)


class BackupPanelView(PermanentView):
    """Панель управления бекапами (только для супер-админа)"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(label="💾 Создать бекап", style=discord.ButtonStyle.success, row=0)
    async def create_backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Создать бекап сервера"""
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            backup = await stats_manager.create_backup(interaction.guild, str(interaction.user.id))
            
            embed = discord.Embed(
                title="✅ БЕКАП СОЗДАН",
                description=f"Дата: {backup['timestamp']}",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)
    
    @discord.ui.button(label="🔄 Восстановить из бекапа", style=discord.ButtonStyle.danger, row=0)
    async def restore_backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Восстановить сервер из бекапа"""
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
            return
        
        backups = db.get_server_backups(10)
        
        if not backups:
            await interaction.response.send_message("❌ Нет доступных бекапов", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔄 ВЫБЕРИТЕ БЕКАП ДЛЯ ВОССТАНОВЛЕНИЯ",
            description="Введите ID бекапа из списка",
            color=0xffa500
        )
        
        for backup in backups:
            embed.add_field(
                name=f"ID: {backup['id']}",
                value=f"Дата: {backup['backup_date']}",
                inline=False
            )
        
        view = BackupRestoreView(backups)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📋 Список бекапов", style=discord.ButtonStyle.secondary, row=1)
    async def list_backups(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать список бекапов"""
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
            return
        
        backups = db.get_server_backups(10)
        
        if not backups:
            await interaction.response.send_message("❌ Нет доступных бекапов", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 СПИСОК БЕКАПОВ",
            color=0x7289da,
            timestamp=datetime.now()
        )
        
        for backup in backups:
            embed.add_field(
                name=f"ID: {backup['id']}",
                value=f"Дата: {backup['backup_date']}\nРазмер: {backup.get('backup_size', 'неизвестно')}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class BackupRestoreView(discord.ui.View):
    def __init__(self, backups):
        super().__init__(timeout=60)
        self.backups = backups
    
    @discord.ui.button(label="✅ Подтвердить восстановление", style=discord.ButtonStyle.danger, row=0)
    async def confirm_restore(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RestoreBackupModal(self.backups))


class RestoreBackupModal(discord.ui.Modal, title="🔄 ВОССТАНОВЛЕНИЕ ИЗ БЕКАПА"):
    backup_id = discord.ui.TextInput(
        label="ID бекапа",
        placeholder="Введите ID из списка",
        max_length=10,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            backup_id = int(self.backup_id.value)
            backup_data = db.get_server_backup(backup_id)
            
            if not backup_data:
                await interaction.response.send_message("❌ Бекап не найден", ephemeral=True)
                return
            
            view = ConfirmView(interaction.user.id)
            await interaction.response.send_message(
                "⚠️ **ВНИМАНИЕ!** Восстановление сервера удалит все текущие каналы и роли.\n"
                "Процесс может занять несколько минут.\n\n"
                "Подтвердите действие:",
                view=view,
                ephemeral=True
            )
            
            await view.wait()
            
            if view.confirmed:
                await interaction.followup.send("🔄 Начинаю восстановление сервера...", ephemeral=True)
                
                backup_json = json.loads(backup_data['backup_data'])
                success = await stats_manager.restore_server(interaction, backup_json)
                
                if success:
                    await interaction.followup.send("✅ Сервер успешно восстановлен!", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Ошибка при восстановлении", ephemeral=True)
            else:
                await interaction.followup.send("❌ Восстановление отменено", ephemeral=True)
                
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)