"""Кнопки для просмотра логов"""
import discord
from datetime import datetime
from action_logs.base import PermanentView
from action_logs.manager import action_logs_manager


class ActionLogsPanelView(PermanentView):
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="📋 ПОСЛЕДНИЕ ЛОГИ",
        style=discord.ButtonStyle.primary,
        emoji="📋",
        row=0,
        custom_id="logs_recent"
    )
    async def recent_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        logs = action_logs_manager.get_logs(str(interaction.guild.id), limit=30)
        
        if not logs:
            await interaction.response.send_message("📭 Нет записей в логах", ephemeral=True)
            return
        
        event_names = {
            'voice_join': '🎙️ Вошёл в войс',
            'voice_leave': '🎙️ Вышел из войса',
            'voice_move': '🎙️ Перемещён',
            'message_edit': '✏️ Редактирование',
            'message_delete': '🗑️ Удаление',
            'channel_create': '📝 Создание канала',
            'channel_delete': '📝 Удаление канала',
            'role_grant': '🎭 Выдана роль',
            'role_revoke': '🎭 Снята роль',
            'role_create': '🎭 Создана роль',
            'role_delete': '🎭 Удалена роль',
            'member_join': '👤 Присоединился',
            'member_leave': '👤 Покинул',
            'member_update': '👤 Изменён профиль',
        }
        
        embed = discord.Embed(
            title="📋 ПОСЛЕДНИЕ ДЕЙСТВИЯ НА СЕРВЕРЕ",
            color=0x7289da,
            timestamp=datetime.now()
        )
        
        for log in logs[:20]:
            time_str = log['timestamp'][:16] if log['timestamp'] else "?"
            event_icon = event_names.get(log['event_type'], log['event_type'])
            embed.add_field(
                name=f"[{time_str}] {event_icon}",
                value=f"👤 <@{log['user_id']}>\n📝 {log['details'][:80] if log['details'] else '-'}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(
        label="🔍 ПОИСК ПО ПОЛЬЗОВАТЕЛЮ",
        style=discord.ButtonStyle.secondary,
        emoji="🔍",
        row=0,
        custom_id="logs_search_user"
    )
    async def search_by_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SearchByUserModal())
    
    @discord.ui.button(
        label="🎯 ПОИСК ПО СОБЫТИЮ",
        style=discord.ButtonStyle.secondary,
        emoji="🎯",
        row=1,
        custom_id="logs_search_event"
    )
    async def search_by_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        events = action_logs_manager.get_event_types(str(interaction.guild.id))
        
        if not events:
            await interaction.response.send_message("📭 Нет зарегистрированных событий", ephemeral=True)
            return
        
        view = SelectEventView(events)
        embed = discord.Embed(
            title="🎯 ВЫБЕРИТЕ СОБЫТИЕ",
            description="Выберите тип события для поиска",
            color=0x7289da
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(
        label="📊 СТАТИСТИКА",
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        row=1,
        custom_id="logs_stats"
    )
    async def show_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        stats = action_logs_manager.get_stats(str(interaction.guild.id), days=30)
        
        event_names = {
            'voice_join': '🎙️ Вход в войс',
            'voice_leave': '🎙️ Выход из войса',
            'message_edit': '✏️ Редактирование',
            'message_delete': '🗑️ Удаление',
            'channel_create': '📝 Создание каналов',
            'role_grant': '🎭 Выдача ролей',
            'role_revoke': '🎭 Снятие ролей',
            'member_join': '👤 Присоединения',
            'member_leave': '👤 Уходы',
        }
        
        embed = discord.Embed(
            title="📊 СТАТИСТИКА ЛОГОВ (30 дней)",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.add_field(name="📝 Всего записей", value=f"**{stats['total']}**", inline=True)
        embed.add_field(name="👥 Уникальных пользователей", value=f"**{stats['unique_users']}**", inline=True)
        
        if stats['top_events']:
            top_text = ""
            for e in stats['top_events'][:8]:
                name = event_names.get(e['event_type'], e['event_type'])
                top_text += f"• {name}: {e['count']}\n"
            embed.add_field(name="🏆 Топ событий", value=top_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SearchByUserModal(discord.ui.Modal, title="🔍 ПОИСК ПО ПОЛЬЗОВАТЕЛЮ"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678", max_length=20, required=True)
    days = discord.ui.TextInput(label="За сколько дней", placeholder="7", default="30", max_length=3, required=False)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = self.user_id.value
            days = int(self.days.value) if self.days.value else 30
            
            logs = action_logs_manager.get_logs(str(interaction.guild.id), limit=50, user_id=uid, days=days)
            
            if not logs:
                await interaction.response.send_message(f"📭 Нет действий от пользователя <@{uid}> за {days} дней", ephemeral=True)
                return
            
            event_names = {
                'voice_join': '🎙️ Вход в войс',
                'voice_leave': '🎙️ Выход из войса',
                'message_edit': '✏️ Редактирование',
                'message_delete': '🗑️ Удаление',
                'role_grant': '🎭 Выдача роли',
                'role_revoke': '🎭 Снятие роли',
            }
            
            embed = discord.Embed(
                title=f"🔍 ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ",
                description=f"<@{uid}> за последние {days} дней",
                color=0x7289da,
                timestamp=datetime.now()
            )
            
            for log in logs[:20]:
                time_str = log['timestamp'][:16] if log['timestamp'] else "?"
                event_name = event_names.get(log['event_type'], log['event_type'])
                embed.add_field(
                    name=f"[{time_str}] {event_name}",
                    value=f"📝 {log['details'][:100] if log['details'] else '-'}",
                    inline=False
                )
            
            if len(logs) > 20:
                embed.set_footer(text=f"Показано 20 из {len(logs)} записей")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Введите корректный ID пользователя", ephemeral=True)


class SelectEventView(discord.ui.View):
    def __init__(self, events):
        super().__init__(timeout=60)
        
        event_names = {
            'voice_join': '🎙️ Вход в войс',
            'voice_leave': '🎙️ Выход из войса',
            'voice_move': '🎙️ Перемещение',
            'message_edit': '✏️ Редактирование',
            'message_delete': '🗑️ Удаление',
            'channel_create': '📝 Создание канала',
            'channel_delete': '📝 Удаление канала',
            'role_grant': '🎭 Выдача роли',
            'role_revoke': '🎭 Снятие роли',
            'role_create': '🎭 Создание роли',
            'role_delete': '🎭 Удаление роли',
            'member_join': '👤 Присоединение',
            'member_leave': '👤 Уход',
            'member_update': '👤 Изменение профиля',
        }
        
        select = discord.ui.Select(
            placeholder="Выберите событие",
            options=[
                discord.SelectOption(label=event_names.get(e, e), value=e)
                for e in events[:25]
            ]
        )
        
        async def select_callback(interaction: discord.Interaction):
            event_type = select.values[0]
            logs = action_logs_manager.get_logs(str(interaction.guild.id), limit=50, event_type=event_type)
            
            if not logs:
                await interaction.response.send_message(f"📭 Нет записей с событием '{event_type}'", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"🎯 СОБЫТИЕ: {event_names.get(event_type, event_type)}",
                color=0x7289da,
                timestamp=datetime.now()
            )
            
            for log in logs[:20]:
                time_str = log['timestamp'][:16] if log['timestamp'] else "?"
                embed.add_field(
                    name=f"[{time_str}]",
                    value=f"👤 <@{log['user_id']}>\n📝 {log['details'][:100] if log['details'] else '-'}",
                    inline=False
                )
            
            if len(logs) > 20:
                embed.set_footer(text=f"Показано 20 из {len(logs)} записей")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        select.callback = select_callback
        self.add_item(select)
        
        cancel_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        async def cancel_callback(interaction: discord.Interaction):
            embed = discord.Embed(title="📋 **ЛОГИ ДЕЙСТВИЙ**", color=0x7289da)
            await interaction.response.edit_message(embed=embed, view=ActionLogsPanelView())
        cancel_btn.callback = cancel_callback
        self.add_item(cancel_btn)