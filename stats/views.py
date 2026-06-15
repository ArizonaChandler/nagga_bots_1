"""Кнопки для статистики и бекапа"""
import discord
import json
import io  # ← ДОБАВИТЬ ЭТУ СТРОКУ
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
        print("📊 [STATS] StatsPanelView создан")
    
    @discord.ui.button(label="📊 Статистика сегодня", style=discord.ButtonStyle.primary, row=0, custom_id="stats_today")
    async def today_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать статистику за сегодня"""
        print("📊 [STATS] today_stats нажата")
        await interaction.response.defer(ephemeral=True)
        
        today = datetime.now().date().isoformat()
        stats = db.get_stats_for_date(today)
        
        if not stats:
            await interaction.followup.send("❌ Статистика за сегодня ещё не собрана", ephemeral=True)
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
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🏆 Топ участников", style=discord.ButtonStyle.primary, row=0, custom_id="stats_top")
    async def top_users(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать топ участников"""
        print("📊 [STATS] top_users нажата")
        await interaction.response.defer(ephemeral=True)
        
        top = db.get_top_balance_users(10)
        
        if not top:
            await interaction.followup.send("🏆 Нет данных для топа", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 ТОП ПО БАЛЛАМ",
            color=0xffd700,
            timestamp=datetime.now()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        for i, (user_id, balance, earned) in enumerate(top, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            embed.add_field(
                name=f"{medal} <@{user_id}>",
                value=f"💰 Баланс: **{balance}**\n📈 Заработано: **{earned}**",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📜 История по дням", style=discord.ButtonStyle.secondary, row=1, custom_id="stats_history")
    async def history_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать историю статистики"""
        print("📊 [STATS] history_stats нажата")
        await interaction.response.send_modal(StatsHistoryModal())
    
    @discord.ui.button(label="👤 Статистика пользователя", style=discord.ButtonStyle.secondary, row=1, custom_id="stats_user")
    async def user_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Статистика по пользователю"""
        print("📊 [STATS] user_stats нажата")
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
        print("📊 [STATS] BackupPanelView создан")
    
    @discord.ui.button(label="💾 Создать бекап", style=discord.ButtonStyle.success, row=0, custom_id="backup_create")
    async def create_backup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Создать бекап сервера"""
        print("📊 [STATS] create_backup нажата")
        
        if not await is_super_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только супер-администратор!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            backup = await stats_manager.create_backup(interaction.guild, str(interaction.user.id))
            
            # Отправляем JSON файл
            backup_json = json.dumps(backup, ensure_ascii=False, indent=2)
            file = discord.File(
                io.BytesIO(backup_json.encode('utf-8')),
                filename=f"backup_{interaction.guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            await interaction.followup.send(
                content=f"✅ Бекап создан!\n📅 {backup['timestamp']}",
                file=file,
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)
    
    @discord.ui.button(label="📋 Список бекапов", style=discord.ButtonStyle.secondary, row=1, custom_id="backup_list")
    async def list_backups(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать список бекапов"""
        print("📊 [STATS] list_backups нажата")
        
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
                value=f"📅 Дата: {backup['backup_date']}\n📦 Размер: {backup.get('backup_size', 'неизвестно')}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)