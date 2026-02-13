"""Admin Views - Единое меню с навигацией"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import format_mention, get_server_name, is_super_admin, has_access
from core.menus import BaseMenuView
from capt.modals import CaptModal
from mcl.core import dual_mcl_core
from mcl.modals import SetMclChannelModal, SetDualColorModal
from admin.modals import *
from files.core import file_manager
from files.views import FilesView
from events.views import EventInfoView


class MainView(BaseMenuView):
    """Главное меню !info"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        # Кнопка файлов
        files_btn = discord.ui.Button(
            label="📁 Полезные файлы",
            style=discord.ButtonStyle.secondary,
            emoji="📁",
            row=0
        )
        async def files_cb(i):
            files, total = file_manager.get_files(page=1)
            
            if total == 0:
                await i.response.send_message("📁 **Пока нет доступных файлов**", ephemeral=True)
                return
            
            view = FilesView(str(i.user.id), page=1, previous_view=self, previous_embed=self.get_current_embed())
            await view.send_initial(i)
        files_btn.callback = files_cb
        self.add_item(files_btn)
        
        # Кнопка мероприятий
        events_btn = discord.ui.Button(
            label="📅 Мероприятия",
            style=discord.ButtonStyle.secondary,
            emoji="📅",
            row=0
        )
        async def events_cb(i):
            view = EventInfoView(self.user_id, self.guild, self, self.get_current_embed())
            embed = discord.Embed(
                title="📅 **МЕРОПРИЯТИЯ**",
                description="Информация о сегодняшних мероприятиях",
                color=0x7289da
            )
            await i.response.edit_message(embed=embed, view=view)
        events_btn.callback = events_cb
        self.add_item(events_btn)
        
        # Кнопки для пользователей с доступом
        if db.user_exists(user_id):
            capt_btn = discord.ui.Button(
                label="🚨 CAPT",
                style=discord.ButtonStyle.danger,
                emoji="🚨",
                row=1
            )
            async def capt_cb(i):
                await i.response.send_modal(CaptModal())
            capt_btn.callback = capt_cb
            self.add_item(capt_btn)
            
            mcl_btn = discord.ui.Button(
                label="🎨 DUAL MCL",
                style=discord.ButtonStyle.primary,
                emoji="🎨",
                row=1
            )
            async def mcl_cb(i):
                if not await has_access(str(i.user.id)):
                    return
                if not CONFIG['channel_id']:
                    await i.response.send_message("❌ Канал MCL не настроен", ephemeral=True)
                    return
                await dual_mcl_core.send_dual(i)
            mcl_btn.callback = mcl_cb
            self.add_item(mcl_btn)
    
    def get_current_embed(self):
        embed = discord.Embed(
            title="🤖 **UNIT MANAGEMENT SYSTEM**",
            color=0x7289da
        )
        embed.set_footer(text="📁 Полезные файлы доступны всем")
        return embed


class SettingsView(BaseMenuView):
    """Главное меню настроек (!settings)"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        capt_btn = discord.ui.Button(label="🚨 CAPT", style=discord.ButtonStyle.secondary, emoji="🚨", row=0)
        async def capt_cb(i):
            view = CaptSettingsView(self.user_id, self.guild, self, self.get_current_embed())
            embed = discord.Embed(
                title="🚨 **НАСТРОЙКИ CAPT**",
                description=f"**Текущие настройки:**\n"
                           f"🎭 Роль: {format_mention(self.guild, CONFIG.get('capt_role_id'), 'role')}\n"
                           f"💬 Чат ошибок: {format_mention(self.guild, CONFIG.get('capt_channel_id'), 'channel')}",
                color=0xff0000
            )
            await i.response.edit_message(embed=embed, view=view)
        capt_btn.callback = capt_cb
        self.add_item(capt_btn)
        
        mcl_btn = discord.ui.Button(label="🎨 MCL", style=discord.ButtonStyle.secondary, emoji="🎨", row=0)
        async def mcl_cb(i):
            view = MclSettingsView(self.user_id, self.guild, self, self.get_current_embed())
            colors = db.get_dual_colors()
            embed = discord.Embed(
                title="🎨 **НАСТРОЙКИ DUAL MCL**",
                description=f"**Текущие настройки:**\n"
                           f"💬 Канал: {format_mention(self.guild, CONFIG.get('channel_id'), 'channel')}\n"
                           f"🎨 Цвета: `{colors[0]}/{colors[1]}`",
                color=0x00ff00
            )
            await i.response.edit_message(embed=embed, view=view)
        mcl_btn.callback = mcl_cb
        self.add_item(mcl_btn)
        
        global_btn = discord.ui.Button(label="🌍 Глобальные", style=discord.ButtonStyle.secondary, emoji="🌍", row=0)
        async def global_cb(i):
            view = GlobalSettingsView(self.user_id, self.guild, self, self.get_current_embed())
            server_name = await get_server_name(self.guild, CONFIG.get('server_id'))
            embed = discord.Embed(
                title="🌍 **ГЛОБАЛЬНЫЕ НАСТРОЙКИ**",
                description=f"**Текущие настройки:**\n"
                           f"🌍 Сервер: {server_name}",
                color=0x7289da
            )
            await i.response.edit_message(embed=embed, view=view)
        global_btn.callback = global_cb
        self.add_item(global_btn)
        
        # ✅ КНОПКА "НАЗАД" - ВОЗВРАТ В ГЛАВНОЕ МЕНЮ АДМИНКИ
        back_btn = discord.ui.Button(
            label="◀ Назад",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=4
        )
        async def back_cb(i):
            # Возвращаемся в главное меню админки (AdminSettingsView)
            from commands.settings import AdminSettingsView
            embed = discord.Embed(
                title="⚙️ **ПАНЕЛЬ АДМИНИСТРАТОРА**",
                description="Выберите раздел для настройки:",
                color=0x7289da,
                timestamp=datetime.now()
            )
            view = AdminSettingsView(self.user_id, self.guild)
            await i.response.edit_message(embed=embed, view=view)
        back_btn.callback = back_cb
        self.add_item(back_btn)
    
    def get_current_embed(self):
        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКИ СИСТЕМЫ**",
            description="Выберите раздел для настройки:",
            color=0x7289da
        )
        return embed


class CaptSettingsView(BaseMenuView):
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        role_btn = discord.ui.Button(label="🎭 Установить роль", style=discord.ButtonStyle.secondary)
        async def role_cb(i):
            await i.response.send_modal(SetRoleModal())
        role_btn.callback = role_cb
        self.add_item(role_btn)
        
        channel_btn = discord.ui.Button(label="💬 Установить чат ошибок", style=discord.ButtonStyle.secondary)
        async def channel_cb(i):
            await i.response.send_modal(SetCaptChannelModal())
        channel_btn.callback = channel_cb
        self.add_item(channel_btn)
        
        self.add_back_button()


class MclSettingsView(BaseMenuView):
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        channel_btn = discord.ui.Button(label="💬 Установить канал", style=discord.ButtonStyle.secondary)
        async def channel_cb(i):
            await i.response.send_modal(SetMclChannelModal())
        channel_btn.callback = channel_cb
        self.add_item(channel_btn)
        
        color_btn = discord.ui.Button(label="🎨 Установить цвета", style=discord.ButtonStyle.secondary)
        async def color_cb(i):
            await i.response.send_modal(SetDualColorModal())
        color_btn.callback = color_cb
        self.add_item(color_btn)
        
        self.add_back_button()


class GlobalSettingsView(BaseMenuView):
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        server_btn = discord.ui.Button(label="🌍 Установить сервер", style=discord.ButtonStyle.secondary)
        async def server_cb(i):
            await i.response.send_modal(SetServerModal())
        server_btn.callback = server_cb
        self.add_item(server_btn)
        
        users_btn = discord.ui.Button(label="👥 Управление доступом", style=discord.ButtonStyle.secondary)
        async def users_cb(i):
            view = AccessView(self.user_id, self.guild, self, await self.get_current_embed())
            embed = discord.Embed(title="👥 **УПРАВЛЕНИЕ ДОСТУПОМ**", color=0x7289da)
            await i.response.edit_message(embed=embed, view=view)
        users_btn.callback = users_cb
        self.add_item(users_btn)
        
        admin_btn = discord.ui.Button(label="👑 Управление админами", style=discord.ButtonStyle.secondary)
        async def admin_cb(i):
            if not await is_super_admin(str(i.user.id)):
                await i.response.send_message("❌ Только супер-администратор", ephemeral=True)
                return
            view = AdminView(self.user_id, self.guild, self, await self.get_current_embed())
            embed = discord.Embed(title="👑 **УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ**", color=0xffd700)
            await i.response.edit_message(embed=embed, view=view)
        admin_btn.callback = admin_cb
        self.add_item(admin_btn)
        
        alarm_btn = discord.ui.Button(
            label="🔔 Настройка оповещений",
            style=discord.ButtonStyle.secondary,
            emoji="🔔",
            row=1
        )
        async def alarm_cb(i):
            view = EventSettingsView(self.user_id, self.guild, self, await self.get_current_embed())
            embed = discord.Embed(
                title="🔔 **СИСТЕМА ОПОВЕЩЕНИЙ**",
                description="Управление автоматическими напоминаниями о мероприятиях",
                color=0xffa500
            )
            
            alarm_channel = CONFIG.get('alarm_channel_id')
            channel_info = format_mention(self.guild, alarm_channel, 'channel') if alarm_channel else "`Не установлен`"
            embed.add_field(name="🔔 Чат напоминаний", value=channel_info, inline=False)
            
            announce_channel = CONFIG.get('announce_channel_id')
            channel_info2 = format_mention(self.guild, announce_channel, 'channel') if announce_channel else "`Не установлен (используется чат напоминаний)`"
            embed.add_field(name="📢 Канал оповещений", value=channel_info2, inline=False)
            
            events = db.get_events(enabled_only=True)
            embed.add_field(name="📅 Активных мероприятий", value=f"`{len(events)}`", inline=True)
            
            await i.response.edit_message(embed=embed, view=view)
        alarm_btn.callback = alarm_cb
        self.add_item(alarm_btn)
        
        self.add_back_button()
    
    async def get_current_embed(self):
        server_name = await get_server_name(self.guild, CONFIG.get('server_id'))
        embed = discord.Embed(
            title="🌍 **ГЛОБАЛЬНЫЕ НАСТРОЙКИ**",
            description=f"**Текущие настройки:**\n🌍 Сервер: {server_name}",
            color=0x7289da
        )
        return embed


class AccessView(BaseMenuView):
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        add_btn = discord.ui.Button(label="➕ Добавить пользователя", style=discord.ButtonStyle.success)
        async def add_cb(i):
            await i.response.send_modal(AddUserModal())
        add_btn.callback = add_cb
        self.add_item(add_btn)
        
        remove_btn = discord.ui.Button(label="➖ Удалить пользователя", style=discord.ButtonStyle.danger)
        async def remove_cb(i):
            await i.response.send_modal(RemoveUserModal())
        remove_btn.callback = remove_cb
        self.add_item(remove_btn)
        
        list_btn = discord.ui.Button(label="📋 Список пользователей", style=discord.ButtonStyle.secondary)
        async def list_cb(i):
            users = db.get_users_with_details()
            embed = discord.Embed(
                title="📋 **ПОЛЬЗОВАТЕЛИ С ДОСТУПОМ**",
                color=0x7289da,
                timestamp=datetime.now()
            )
            
            if users:
                lines = []
                for uid, username, added_by, added_at, last_used, is_admin, is_super in users[:25]:
                    mention = format_mention(self.guild, uid, 'user')
                    if is_super:
                        icon = "👑👑"
                        role = "**Супер-админ**"
                    elif is_admin:
                        icon = "👑"
                        role = "Админ"
                    else:
                        icon = "👤"
                        role = "Пользователь"
                    lines.append(f"{icon} {mention} • {role}")
                
                embed.description = "\n".join(lines)
                total = len(users)
                admins_count = sum(1 for u in users if u[5])
                supers_count = sum(1 for u in users if u[6])
                embed.set_footer(text=f"Всего: {total} • Админов: {admins_count} • Супер-админов: {supers_count}")
            else:
                embed.description = "❌ Нет пользователей с доступом"
            
            await i.response.edit_message(embed=embed, view=self)
        list_btn.callback = list_cb
        self.add_item(list_btn)
        
        self.add_back_button()


class AdminView(BaseMenuView):
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        add_btn = discord.ui.Button(label="➕ Добавить администратора", style=discord.ButtonStyle.success)
        async def add_cb(i):
            await i.response.send_modal(AddAdminModal())
        add_btn.callback = add_cb
        self.add_item(add_btn)
        
        remove_btn = discord.ui.Button(label="➖ Удалить администратора", style=discord.ButtonStyle.danger)
        async def remove_cb(i):
            await i.response.send_modal(RemoveAdminModal())
        remove_btn.callback = remove_cb
        self.add_item(remove_btn)
        
        list_btn = discord.ui.Button(label="📋 Список админов", style=discord.ButtonStyle.secondary)
        async def list_cb(i):
            admins = db.get_admins()
            embed = discord.Embed(
                title="👑 **АДМИНИСТРАТОРЫ**",
                color=0xffd700,
                timestamp=datetime.now()
            )
            
            if admins:
                lines = []
                for admin_id, added_by, added_at, is_super, username in admins:
                    mention = format_mention(self.guild, admin_id, 'user')
                    if is_super:
                        lines.append(f"👑👑 {mention} • **Супер-админ**")
                    else:
                        lines.append(f"👑 {mention}")
                embed.description = "\n".join(lines)
                embed.set_footer(text=f"Всего: {len(admins)}")
            else:
                embed.description = "❌ Нет администраторов"
            
            await i.response.edit_message(embed=embed, view=self)
        list_btn.callback = list_cb
        self.add_item(list_btn)
        
        self.add_back_button()


class EventSettingsView(BaseMenuView):
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        
        channel_btn = discord.ui.Button(label="🔔 Чат напоминаний", style=discord.ButtonStyle.primary, emoji="🔔", row=0)
        async def channel_cb(i):
            await i.response.send_modal(SetAlarmChannelModal())
        channel_btn.callback = channel_cb
        self.add_item(channel_btn)
        
        announce_btn = discord.ui.Button(label="📢 Канал оповещений", style=discord.ButtonStyle.primary, emoji="📢", row=0)
        async def announce_cb(i):
            await i.response.send_modal(SetAnnounceChannelModal())
        announce_btn.callback = announce_cb
        self.add_item(announce_btn)
        
        add_btn = discord.ui.Button(label="➕ Добавить МП", style=discord.ButtonStyle.success, emoji="➕", row=1)
        async def add_cb(i):
            await i.response.send_modal(AddEventModal())
        add_btn.callback = add_cb
        self.add_item(add_btn)
        
        list_btn = discord.ui.Button(label="📋 Список МП", style=discord.ButtonStyle.secondary, emoji="📋", row=1)
        async def list_cb(i):
            view = EventsListView(self.user_id, self.guild, page=1, previous_view=self, previous_embed=await self.get_current_embed())
            await view.send_initial(i)
        list_btn.callback = list_cb
        self.add_item(list_btn)
        
        stats_btn = discord.ui.Button(label="📊 Статистика", style=discord.ButtonStyle.secondary, emoji="📊", row=2)
        async def stats_cb(i):
            await send_event_stats(i, self.guild, self, await self.get_current_embed())
        stats_btn.callback = stats_cb
        self.add_item(stats_btn)
        
        one_time_btn = discord.ui.Button(label="📅 Разовое МП", style=discord.ButtonStyle.secondary, emoji="📅", row=2)
        async def one_time_cb(i):
            from events.modals import ScheduleEventModal
            await i.response.send_modal(ScheduleEventModal())
        one_time_btn.callback = one_time_cb
        self.add_item(one_time_btn)
        
        self.add_back_button()
    
    async def get_current_embed(self):
        embed = discord.Embed(
            title="🔔 **СИСТЕМА ОПОВЕЩЕНИЙ**",
            description="Управление автоматическими напоминаниями о мероприятиях",
            color=0xffa500
        )
        return embed


class EventsListView(BaseMenuView):
    """Список мероприятий с пагинацией"""
    def __init__(self, user_id: str, guild, page: int = 1, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        self.page = page
        self.message = None
        self.events = []
        self.max_page = 1
        self.load_events()
        self.update_buttons()
    
    def load_events(self):
        """Загрузка мероприятий с пагинацией"""
        per_page = 5
        offset = (self.page - 1) * per_page
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM events')
            total = cursor.fetchone()[0]
            self.max_page = (total + per_page - 1) // per_page if total > 0 else 1
            
            cursor.execute('''
                SELECT id, name, weekday, event_time, 
                       CASE WHEN enabled = 1 THEN '✅' ELSE '❌' END as status
                FROM events
                ORDER BY weekday, event_time
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            self.events = []
            for row in rows:
                self.events.append(dict(zip(columns, row)))
    
    def update_buttons(self):
        """Обновить кнопки навигации и мероприятий"""
        self.clear_items()
        days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        
        # Кнопки для каждого мероприятия
        for event in self.events:
            btn = discord.ui.Button(
                label=f"{event['status']} {event['name'][:20]}... | {days[event['weekday']]} {event['event_time']}",
                style=discord.ButtonStyle.secondary
            )
            async def callback(interaction, eid=event['id'], ename=event['name'], 
                             ewday=event['weekday'], etime=event['event_time']):
                view = EventDetailView(
                    self.user_id, 
                    self.guild, 
                    eid, 
                    ename, 
                    ewday, 
                    etime, 
                    self, 
                    self.create_embed()
                )
                embed = discord.Embed(title=f"📋 {ename}", color=0x7289da)
                embed.add_field(name="🆔 ID", value=f"`{eid}`", inline=True)
                embed.add_field(name="📅 День", value=days[ewday], inline=True)
                embed.add_field(name="⏰ Время", value=etime, inline=True)
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT COUNT(*) FROM event_takes 
                        WHERE event_id = ? AND event_date >= date('now', '-30 days')
                    ''', (eid,))
                    takes_30d = cursor.fetchone()[0]
                embed.add_field(name="📊 За 30 дней", value=f"`{takes_30d}` взятий", inline=True)
                
                await interaction.response.edit_message(embed=embed, view=view)
            btn.callback = callback
            self.add_item(btn)
        
        # Кнопки пагинации
        if self.page > 1:
            prev_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
            async def prev_cb(i):
                self.page -= 1
                self.load_events()
                self.update_buttons()
                await i.response.edit_message(embed=self.create_embed(), view=self)
            prev_btn.callback = prev_cb
            self.add_item(prev_btn)
        
        if self.page < self.max_page:
            next_btn = discord.ui.Button(label="Вперёд ▶", style=discord.ButtonStyle.secondary)
            async def next_cb(i):
                self.page += 1
                self.load_events()
                self.update_buttons()
                await i.response.edit_message(embed=self.create_embed(), view=self)
            next_btn.callback = next_cb
            self.add_item(next_btn)
        
        # Кнопка "Назад" в меню настроек оповещений
        self.add_back_button(row=4)
    
    def add_back_button(self, row=4):
        """Добавить кнопку "Назад" если есть предыдущее меню"""
        if self.previous_view:
            back_btn = discord.ui.Button(
                label="◀ Назад",
                style=discord.ButtonStyle.secondary,
                emoji="◀",
                row=row
            )
            async def back_callback(i):
                await i.response.edit_message(
                    content=None,
                    embed=self.previous_embed,
                    view=self.previous_view
                )
            back_btn.callback = back_callback
            self.add_item(back_btn)
    
    def create_embed(self):
        """Создать embed для списка мероприятий"""
        embed = discord.Embed(
            title="📋 **СПИСОК МЕРОПРИЯТИЙ**",
            description=f"Страница {self.page}/{self.max_page}",
            color=0x7289da
        )
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        lines = []
        for event in self.events:
            lines.append(f"`{event['id']:03d}` {event['status']} **{event['name']}** — {days[event['weekday']]} {event['event_time']}")
        embed.description = "\n".join(lines) if lines else "Нет мероприятий"
        embed.set_footer(text=f"Всего: {len(self.events)} на странице")
        return embed
    
    async def send_initial(self, interaction):
        """Отправить начальное сообщение"""
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        self.message = await interaction.original_response()


class EventDetailView(BaseMenuView):
    def __init__(self, user_id: str, guild, event_id: int, event_name: str, 
                 weekday: int, event_time: str, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        self.event_id = event_id
        self.event_name = event_name
        self.weekday = weekday
        self.event_time = event_time
        
        # Определяем текст кнопки в зависимости от состояния
        event = db.get_event(self.event_id)
        toggle_text = "🔴 Выключить" if event and event['enabled'] else "🟢 Включить"
        toggle_style = discord.ButtonStyle.danger if event and event['enabled'] else discord.ButtonStyle.success
        
        toggle_btn = discord.ui.Button(label=toggle_text, style=toggle_style, emoji="🔴" if event and event['enabled'] else "🟢", row=0)
        async def toggle_cb(i):
            event = db.get_event(self.event_id)
            if event and event['enabled']:
                db.update_event(self.event_id, enabled=0)
                db.log_event_action(self.event_id, "disabled", str(i.user.id))
                # Возвращаемся к списку
                from admin.views import EventsListView
                view = EventsListView(
                    self.user_id, 
                    self.guild, 
                    page=1, 
                    previous_view=self.previous_view, 
                    previous_embed=self.previous_embed
                )
                embed = view.create_embed()
                await i.response.edit_message(embed=embed, view=view)
            else:
                db.update_event(self.event_id, enabled=1)
                db.log_event_action(self.event_id, "enabled", str(i.user.id))
                # Возвращаемся к списку
                from admin.views import EventsListView
                view = EventsListView(
                    self.user_id, 
                    self.guild, 
                    page=1, 
                    previous_view=self.previous_view, 
                    previous_embed=self.previous_embed
                )
                embed = view.create_embed()
                await i.response.edit_message(embed=embed, view=view)
        toggle_btn.callback = toggle_cb
        self.add_item(toggle_btn)
        
        edit_btn = discord.ui.Button(label="✏️ Редактировать", style=discord.ButtonStyle.primary, emoji="✏️", row=0)
        async def edit_cb(i):
            await i.response.send_modal(EditEventModal(self.event_id, self.event_name, self.weekday, self.event_time))
        edit_btn.callback = edit_cb
        self.add_item(edit_btn)
        
        delete_btn = discord.ui.Button(label="🗑️ Удалить", style=discord.ButtonStyle.danger, emoji="🗑️", row=0)
        async def delete_cb(i):
            confirm_view = ConfirmDeleteView(self.user_id, self.event_id, self.event_name, self, self.previous_embed)
            await i.response.edit_message(
                content=f"❓ Ты уверен, что хочешь удалить **{self.event_name}**?",
                embed=None,
                view=confirm_view
            )
        delete_btn.callback = delete_cb
        self.add_item(delete_btn)
        
        self.add_back_button(row=4)

class ConfirmDeleteView(BaseMenuView):
    def __init__(self, user_id: str, event_id: int, event_name: str, previous_view=None, previous_embed=None):
        super().__init__(user_id, None, previous_view, previous_embed)
        self.event_id = event_id
        self.event_name = event_name
    
    @discord.ui.button(label="✅ Да, удалить", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Полное удаление из БД (не soft delete)
        success = db.delete_event(self.event_id, soft=False)
        
        if success:
            db.log_event_action(self.event_id, "deleted", str(interaction.user.id))
            
            # Сначала возвращаемся в EventSettingsView
            from admin.views import EventSettingsView
            settings_view = EventSettingsView(
                self.user_id,
                interaction.guild,
                None,  # previous_view
                None   # previous_embed
            )
            
            # Затем показываем список мероприятий
            from admin.views import EventsListView
            list_view = EventsListView(
                self.user_id,
                interaction.guild,
                page=1,
                previous_view=settings_view,
                previous_embed=discord.Embed(
                    title="🔔 **СИСТЕМА ОПОВЕЩЕНИЙ**",
                    description="Управление автоматическими напоминаниями о мероприятиях",
                    color=0xffa500
                )
            )
            embed = list_view.create_embed()
            await interaction.response.edit_message(embed=embed, view=list_view)
        else:
            await interaction.response.edit_message(
                content="❌ Не удалось удалить мероприятие",
                embed=None,
                view=None
            )
    
    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Возвращаемся к деталям мероприятия
        await interaction.response.edit_message(
            embed=self.previous_embed,
            view=self.previous_view
        )

class ConfirmDeleteView(BaseMenuView):
    def __init__(self, user_id: str, event_id: int, event_name: str, previous_view=None, previous_embed=None):
        super().__init__(user_id, None, previous_view, previous_embed)
        self.event_id = event_id
        self.event_name = event_name
        self.message = None  # для сохранения сообщения
    
    @discord.ui.button(label="✅ Да, удалить", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Полное удаление из БД
        success = db.delete_event(self.event_id, soft=False)
        
        if success:
            db.log_event_action(self.event_id, "deleted", str(interaction.user.id))
            
            # Создаём свежее меню списка мероприятий
            from admin.views import EventsListView, EventSettingsView
            
            # Сначала создаём SettingsView как предыдущее меню
            settings_view = EventSettingsView(
                self.user_id,
                interaction.guild,
                None,
                None
            )
            settings_embed = discord.Embed(
                title="🔔 **СИСТЕМА ОПОВЕЩЕНИЙ**",
                description="Управление автоматическими напоминаниями о мероприятиях",
                color=0xffa500
            )
            
            # Затем создаём список мероприятий
            list_view = EventsListView(
                self.user_id,
                interaction.guild,
                page=1,
                previous_view=settings_view,
                previous_embed=settings_embed
            )
            
            # Получаем embed для списка
            embed = list_view.create_embed()
            
            # Редактируем сообщение - полностью заменяем контент
            await interaction.response.edit_message(
                content=None,  # Убираем текст подтверждения
                embed=embed,
                view=list_view
            )
        else:
            await interaction.response.edit_message(
                content="❌ Не удалось удалить мероприятие",
                embed=None,
                view=None
            )
    
    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Возвращаемся к деталям мероприятия
        await interaction.response.edit_message(
            content=None,  # Убираем текст подтверждения
            embed=self.previous_embed,
            view=self.previous_view
        )

async def send_event_stats(interaction, guild, previous_view=None, previous_embed=None):
    """Отправка статистики по мероприятиям"""
    top = db.get_top_organizers(10, days=30)  # За последние 30 дней
    stats = db.get_event_stats_summary()
    
    embed = discord.Embed(
        title="📊 **СТАТИСТИКА МЕРОПРИЯТИЙ**",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    # Топ организаторов за 30 дней
    if top:
        top_text = ""
        for i, row in enumerate(top[:5], 1):
            user_id, user_name, count = row
            # Пытаемся получить упоминание, если не получается - используем имя
            try:
                user = await guild.fetch_member(int(user_id))
                mention = user.mention
            except:
                mention = f"**{user_name}**"
            top_text += f"{i}. {mention} — **{count}** МП\n"
        
        embed.add_field(name="🏆 Топ организаторов (30 дней)", value=top_text or "Нет данных", inline=False)
    else:
        embed.add_field(name="🏆 Топ организаторов", value="Нет данных за 30 дней", inline=False)
    
    # Общая статистика
    embed.add_field(
        name="📅 Мероприятия",
        value=f"Всего: `{stats['total_events']}`\nАктивных: `{stats['active_events']}`",
        inline=True
    )
    
    embed.add_field(
        name="✅ Проведено",
        value=f"За всё время: `{stats['total_takes']}`\nЗа 30 дней: `{stats['takes_30d']}`\nСегодня: `{stats['takes_today']}`",
        inline=True
    )
    
    class StatsView(BaseMenuView):
        def __init__(self):
            super().__init__(str(interaction.user.id), guild, previous_view, previous_embed)
            self.add_back_button()
    
    await interaction.response.edit_message(embed=embed, view=StatsView())