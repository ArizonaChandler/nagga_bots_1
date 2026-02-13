"""Admin Views - Кнопочный интерфейс для администраторов"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import format_mention, get_server_name, is_super_admin, has_access
from capt.modals import CaptModal
from mcl.core import dual_mcl_core
from mcl.modals import SetMclChannelModal, SetDualColorModal
from admin.modals import *
from files.core import file_manager
from files.views import FilesView
from events.views import EventInfoView

class MainView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        
        # ✅ 1. КНОПКА ФАЙЛОВ - ВИДНА ВСЕМ!
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
            
            description = f"**📊 Всего доступно файлов: {total}**\n\n"
            
            for idx, (file_id, name, desc, size, uploader, uploaded_at, downloads) in enumerate(files[:5], 1):
                size_str = f"{size / 1024:.1f} КБ" if size < 1024*1024 else f"{size / (1024*1024):.1f} МБ"
                date_str = uploaded_at[:10] if uploaded_at else "?"
                description += f"**{idx}. {name}**\n"
                description += f"   📝 {desc[:100]}{'...' if len(desc) > 100 else ''}\n"
                description += f"   📦 {size_str} | ⬇️ {downloads} | 📅 {date_str}\n\n"
            
            embed = discord.Embed(
                title="📁 **ПОЛЕЗНЫЕ ФАЙЛЫ**",
                description=description,
                color=0x00ff00
            )
            embed.set_footer(text=f"Страница 1/{((total-1)//5)+1} • Нажмите кнопку для скачивания")
            
            view = FilesView(str(i.user.id), page=1)
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        
        files_btn.callback = files_cb
        self.add_item(files_btn)
        
        # ✅ 2. КНОПКА МЕРОПРИЯТИЙ - ТОЖЕ ВИДНА ВСЕМ!
        events_btn = discord.ui.Button(
            label="📅 Мероприятия",
            style=discord.ButtonStyle.secondary,
            emoji="📅",
            row=0
        )
        async def events_cb(i):
            view = EventInfoView()
            embed = discord.Embed(
                title="📅 **МЕРОПРИЯТИЯ**",
                description="Информация о сегодняшних мероприятиях",
                color=0x7289da
            )
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        events_btn.callback = events_cb
        self.add_item(events_btn)
        
        # ✅ 3. КНОПКИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ С ДОСТУПОМ
        if db.user_exists(user_id):
            # CAPT
            capt_btn = discord.ui.Button(
                label="🚨 CAPT",
                style=discord.ButtonStyle.danger,
                emoji="🚨",
                row=1
            )
            async def capt_cb(i):
                if await has_access(str(i.user.id)):
                    await i.response.send_modal(CaptModal())
            capt_btn.callback = capt_cb
            self.add_item(capt_btn)
            
            # DUAL MCL
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
        
        # КНОПКА НАСТРОЕК УБРАНА - теперь только через !settings


class SettingsView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
        capt_btn = discord.ui.Button(label="🚨 CAPT", style=discord.ButtonStyle.secondary, emoji="🚨", row=0)
        async def capt_cb(i):
            view = CaptSettingsView(self.user_id, self.guild)
            embed = discord.Embed(
                title="🚨 **НАСТРОЙКИ CAPT**",
                description=f"**Текущие настройки:**\n"
                           f"🎭 Роль: {format_mention(self.guild, CONFIG.get('capt_role_id'), 'role')}\n"
                           f"💬 Чат ошибок: {format_mention(self.guild, CONFIG.get('capt_channel_id'), 'channel')}",
                color=0xff0000
            )
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        capt_btn.callback = capt_cb
        self.add_item(capt_btn)
        
        mcl_btn = discord.ui.Button(label="🎨 MCL", style=discord.ButtonStyle.secondary, emoji="🎨", row=0)
        async def mcl_cb(i):
            view = MclSettingsView(self.user_id, self.guild)
            colors = db.get_dual_colors()
            embed = discord.Embed(
                title="🎨 **НАСТРОЙКИ DUAL MCL**",
                description=f"**Текущие настройки:**\n"
                           f"💬 Канал: {format_mention(self.guild, CONFIG.get('channel_id'), 'channel')}\n"
                           f"🎨 Цвета: `{colors[0]}/{colors[1]}`",
                color=0x00ff00
            )
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        mcl_btn.callback = mcl_cb
        self.add_item(mcl_btn)
        
        global_btn = discord.ui.Button(label="🌍 Глобальные", style=discord.ButtonStyle.secondary, emoji="🌍", row=0)
        async def global_cb(i):
            view = GlobalSettingsView(self.user_id, self.guild)
            server_name = await get_server_name(self.guild, CONFIG.get('server_id'))
            embed = discord.Embed(
                title="🌍 **ГЛОБАЛЬНЫЕ НАСТРОЙКИ**",
                description=f"**Текущие настройки:**\n"
                           f"🌍 Сервер: {server_name}",
                color=0x7289da
            )
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        global_btn.callback = global_cb
        self.add_item(global_btn)


class CaptSettingsView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
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


class MclSettingsView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
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


class GlobalSettingsView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
        server_btn = discord.ui.Button(label="🌍 Установить сервер", style=discord.ButtonStyle.secondary)
        async def server_cb(i):
            await i.response.send_modal(SetServerModal())
        server_btn.callback = server_cb
        self.add_item(server_btn)
        
        users_btn = discord.ui.Button(label="👥 Управление доступом", style=discord.ButtonStyle.secondary)
        async def users_cb(i):
            view = AccessView(self.user_id, self.guild)
            embed = discord.Embed(title="👥 **УПРАВЛЕНИЕ ДОСТУПОМ**", color=0x7289da)
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        users_btn.callback = users_cb
        self.add_item(users_btn)
        
        admin_btn = discord.ui.Button(label="👑 Управление админами", style=discord.ButtonStyle.secondary)
        async def admin_cb(i):
            if not await is_super_admin(str(i.user.id)):
                await i.response.send_message("❌ Только супер-администратор", ephemeral=True)
                return
            view = AdminView(self.user_id, self.guild)
            embed = discord.Embed(title="👑 **УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ**", color=0xffd700)
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        admin_btn.callback = admin_cb
        self.add_item(admin_btn)
        
        # 🔔 НОВАЯ КНОПКА - Настройка оповещений
        alarm_btn = discord.ui.Button(
            label="🔔 Настройка оповещений",
            style=discord.ButtonStyle.secondary,
            emoji="🔔",
            row=1
        )
        async def alarm_cb(i):
            view = EventSettingsView(self.user_id, self.guild)
            embed = discord.Embed(
                title="🔔 **СИСТЕМА ОПОВЕЩЕНИЙ**",
                description="Управление автоматическими напоминаниями о мероприятиях",
                color=0xffa500
            )
            
            # Текущий канал напоминаний
            alarm_channel = CONFIG.get('alarm_channel_id')
            channel_info = format_mention(self.guild, alarm_channel, 'channel') if alarm_channel else "`Не установлен`"
            embed.add_field(name="🔔 Чат напоминаний", value=channel_info, inline=False)
            
            # Текущий канал оповещений
            announce_channel = CONFIG.get('announce_channel_id')
            channel_info2 = format_mention(self.guild, announce_channel, 'channel') if announce_channel else "`Не установлен (используется чат напоминаний)`"
            embed.add_field(name="📢 Канал оповещений", value=channel_info2, inline=False)
            
            # Количество активных мероприятий
            events = db.get_events(enabled_only=True)
            embed.add_field(name="📅 Активных мероприятий", value=f"`{len(events)}`", inline=True)
            
            await i.response.send_message(embed=embed, view=view, ephemeral=True)
        alarm_btn.callback = alarm_cb
        self.add_item(alarm_btn)


class AccessView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
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
            
            await i.response.send_message(embed=embed, ephemeral=True)
        list_btn.callback = list_cb
        self.add_item(list_btn)


class AdminView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
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
            
            await i.response.send_message(embed=embed, ephemeral=True)
        list_btn.callback = list_cb
        self.add_item(list_btn)


# ===== НОВЫЕ VIEWS ДЛЯ СИСТЕМЫ ОПОВЕЩЕНИЙ =====

class EventSettingsView(discord.ui.View):
    def __init__(self, user_id: str, guild):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        
        # Установить чат напоминаний
        channel_btn = discord.ui.Button(
            label="🔔 Чат напоминаний",
            style=discord.ButtonStyle.primary,
            emoji="🔔",
            row=0
        )
        async def channel_cb(i):
            await i.response.send_modal(SetAlarmChannelModal())
        channel_btn.callback = channel_cb
        self.add_item(channel_btn)
        
        # Установить канал оповещений
        announce_btn = discord.ui.Button(
            label="📢 Канал оповещений",
            style=discord.ButtonStyle.primary,
            emoji="📢",
            row=0
        )
        async def announce_cb(i):
            await i.response.send_modal(SetAnnounceChannelModal())
        announce_btn.callback = announce_cb
        self.add_item(announce_btn)
        
        # Добавить мероприятие
        add_btn = discord.ui.Button(
            label="➕ Добавить МП",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=1
        )
        async def add_cb(i):
            await i.response.send_modal(AddEventModal())
        add_btn.callback = add_cb
        self.add_item(add_btn)
        
        # Список мероприятий
        list_btn = discord.ui.Button(
            label="📋 Список МП",
            style=discord.ButtonStyle.secondary,
            emoji="📋",
            row=1
        )
        async def list_cb(i):
            view = EventsListView(self.user_id, self.guild, page=1)
            await view.send_initial(i)
        list_btn.callback = list_cb
        self.add_item(list_btn)
        
        # Статистика
        stats_btn = discord.ui.Button(
            label="📊 Статистика",
            style=discord.ButtonStyle.secondary,
            emoji="📊",
            row=2
        )
        async def stats_cb(i):
            await send_event_stats(i, self.guild)
        stats_btn.callback = stats_cb
        self.add_item(stats_btn)
        
        # Разовое мероприятие
        one_time_btn = discord.ui.Button(
            label="📅 Разовое МП",
            style=discord.ButtonStyle.secondary,
            emoji="📅",
            row=2
        )
        async def one_time_cb(i):
            from events.modals import ScheduleEventModal
            await i.response.send_modal(ScheduleEventModal())
        one_time_btn.callback = one_time_cb
        self.add_item(one_time_btn)


class EventsListView(discord.ui.View):
    """Список мероприятий с пагинацией - одно сообщение"""
    def __init__(self, user_id: str, guild, page: int = 1, message=None):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        self.page = page
        self.message = message
        self.events = []
        self.max_page = 1
        self.load_events()
        self.update_buttons()
    
    def load_events(self):
        per_page = 5
        offset = (self.page - 1) * per_page
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # ПОКАЗЫВАЕМ ВСЕ МЕРОПРИЯТИЯ, даже отключенные
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
        """Обновить состояние кнопок навигации"""
        self.clear_items()
        
        days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        
        # Кнопки мероприятий
        for event in self.events:
            event_id = event['id']
            name = event['name']
            weekday = event['weekday']
            event_time = event['event_time']
            status = event['status']
            
            btn = discord.ui.Button(
                label=f"{status} {name[:20]}... | {days[weekday]} {event_time}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"event_{event_id}"
            )
            
            async def callback(interaction, eid=event_id, ename=name, ewday=weekday, etime=event_time):
                view = EventDetailView(self.user_id, self.guild, eid, ename, ewday, etime)
                embed = discord.Embed(
                    title=f"📋 {ename}",
                    color=0x7289da
                )
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
                
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            btn.callback = callback
            self.add_item(btn)
        
        # Кнопки навигации
        if self.page > 1:
            prev_btn = discord.ui.Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
            async def prev_cb(i):
                self.page -= 1
                self.load_events()
                self.update_buttons()
                embed = self.create_embed()
                await i.response.edit_message(embed=embed, view=self)
            prev_btn.callback = prev_cb
            self.add_item(prev_btn)
        
        if self.page < self.max_page:
            next_btn = discord.ui.Button(label="Вперёд ▶", style=discord.ButtonStyle.secondary)
            async def next_cb(i):
                self.page += 1
                self.load_events()
                self.update_buttons()
                embed = self.create_embed()
                await i.response.edit_message(embed=embed, view=self)
            next_btn.callback = next_cb
            self.add_item(next_btn)
    
    def create_embed(self):
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
        embed = self.create_embed()
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        self.message = await interaction.original_response()
    
    async def interaction_check(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Это меню вызвано другим пользователем", ephemeral=True)
            return False
        return True


class EventDetailView(discord.ui.View):
    def __init__(self, user_id: str, guild, event_id: int, event_name: str, weekday: int, event_time: str):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.guild = guild
        self.event_id = event_id
        self.event_name = event_name
        self.weekday = weekday
        self.event_time = event_time
        
        # Включить/выключить
        toggle_btn = discord.ui.Button(
            label="🔴 Выключить",
            style=discord.ButtonStyle.danger,
            emoji="🔴",
            row=0
        )
        async def toggle_cb(i):
            event = db.get_event(self.event_id)
            if event and event['enabled']:
                db.update_event(self.event_id, enabled=0)
                db.log_event_action(self.event_id, "disabled", str(i.user.id))
                await i.response.send_message(f"❌ Мероприятие **{self.event_name}** отключено", ephemeral=True)
            else:
                db.update_event(self.event_id, enabled=1)
                db.log_event_action(self.event_id, "enabled", str(i.user.id))
                await i.response.send_message(f"✅ Мероприятие **{self.event_name}** включено", ephemeral=True)
        toggle_btn.callback = toggle_cb
        self.add_item(toggle_btn)
        
        # Редактировать
        edit_btn = discord.ui.Button(
            label="✏️ Редактировать",
            style=discord.ButtonStyle.primary,
            emoji="✏️",
            row=0
        )
        async def edit_cb(i):
            await i.response.send_modal(EditEventModal(
                self.event_id, 
                self.event_name, 
                self.weekday, 
                self.event_time
            ))
        edit_btn.callback = edit_cb
        self.add_item(edit_btn)
        
        # Удалить
        delete_btn = discord.ui.Button(
            label="🗑️ Удалить",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=0
        )
        async def delete_cb(i):
            confirm_view = ConfirmDeleteView(self.user_id, self.event_id, self.event_name)
            await i.response.send_message(
                f"❓ Ты уверен, что хочешь удалить **{self.event_name}**?",
                view=confirm_view,
                ephemeral=True
            )
        delete_btn.callback = delete_cb
        self.add_item(delete_btn)


class ConfirmDeleteView(discord.ui.View):
    def __init__(self, user_id: str, event_id: int, event_name: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.event_id = event_id
        self.event_name = event_name
    
    @discord.ui.button(label="✅ Да, удалить", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        db.delete_event(self.event_id)
        db.log_event_action(self.event_id, "deleted", str(interaction.user.id))
        await interaction.response.edit_message(
            content=f"🗑️ Мероприятие **{self.event_name}** удалено",
            view=None
        )
    
    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Удаление отменено", view=None)
    
    async def interaction_check(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню", ephemeral=True)
            return False
        return True


async def send_event_stats(interaction, guild):
    """Отправка статистики по мероприятиям"""
    top = db.get_top_organizers(10)
    takes = db.get_event_takes(days=30)
    events = db.get_events(enabled_only=False)
    
    embed = discord.Embed(
        title="📊 **СТАТИСТИКА МЕРОПРИЯТИЙ**",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    # Топ организаторов
    if top:
        top_text = "\n".join([f"{i+1}. <@{row[0]}> — **{row[2]}** МП" for i, row in enumerate(top[:5])])
        embed.add_field(name="🏆 Топ организаторов (30 дней)", value=top_text, inline=False)
    
    # Общая статистика
    active = sum(1 for e in events if e['enabled'])
    embed.add_field(name="📅 Всего МП", value=f"`{len(events)}` (активных: `{active}`)", inline=True)
    embed.add_field(name="✅ Проведено (30д)", value=f"`{len(takes)}`", inline=True)
    
    # Статистика по дням недели
    days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    day_counts = [0] * 7
    for event in events:
        if event['enabled']:
            day_counts[event['weekday']] += 1
    
    days_text = ", ".join([f"{days[i]}:{day_counts[i]}" for i in range(7) if day_counts[i] > 0])
    embed.add_field(name="📆 Распределение", value=days_text or "Нет данных", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)