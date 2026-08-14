"""Инициализация каналов системы мероприятий"""
import discord
import logging
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import is_admin
from events.manager import events_manager
from events.settings_view import EventsSettingsView
from events.templates import get_event_templates, format_templates_for_select
from events.modals import CreateEventModal
from events.stats import EventStats

logger = logging.getLogger(__name__)


class EventsInitializer:
    
    def __init__(self, bot):
        self.bot = bot
        self.stats = None
    
    async def initialize_all(self):
        logger.info("🔄 Инициализация системы мероприятий...")
        print("🎯 [EVENTS] Инициализация системы мероприятий...")
        
        events_manager.set_bot(self.bot)
        
        self.moderation_channel_id = db.get_setting('events_moderation_channel')
        self.participant_channel_id = db.get_setting('events_participant_channel')
        self.log_channel_id = db.get_setting('events_log_channel')
        self.settings_channel_id = db.get_setting('events_settings_channel')
        
        # Очищаем от 'null'
        if self.settings_channel_id == 'null' or self.settings_channel_id is None:
            self.settings_channel_id = None
        
        if self.moderation_channel_id:
            await self._init_moderation_channel()
        
        if self.participant_channel_id:
            await self._init_participant_channel()
        
        if self.settings_channel_id:
            await self._init_settings_channel()
        
        await self._restore_sessions()
        
        self.stats = EventStats(self.bot)
        await self.stats.start()
        print("📊 [EVENTS] Еженедельная статистика запущена")
        
        logger.info("✅ Инициализация системы мероприятий завершена")
        print("🎯 [EVENTS] Инициализация завершена")
    
    async def _init_moderation_channel(self):
        try:
            channel = self.bot.get_channel(int(self.moderation_channel_id))
            if not channel:
                logger.error(f"❌ Канал модерации {self.moderation_channel_id} не найден")
                return
        except (ValueError, TypeError):
            logger.error(f"❌ Неверный ID канала модерации: {self.moderation_channel_id}")
            return
        
        templates = get_event_templates()
        embed = discord.Embed(
            title="🎯 **ПАНЕЛЬ УПРАВЛЕНИЯ МЕРОПРИЯТИЯМИ**",
            description="Создание и управление мероприятиями\n\n"
                        f"📋 **Доступно шаблонов:** {len(templates)}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Нажмите кнопку «➕ СОЗДАТЬ МП» чтобы начать",
            color=0x00bfff
        )
        
        view = ModerationMainView(templates)
        
        found = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "ПАНЕЛЬ УПРАВЛЕНИЯ МЕРОПРИЯТИЯМИ" in msg.embeds[0].title:
                    await msg.edit(embed=embed, view=view)
                    found = True
                    print(f"🎯 [EVENTS] Обновлена панель модерации в #{channel.name}")
                    break
        
        if not found:
            await channel.send(embed=embed, view=view)
            print(f"🎯 [EVENTS] Создана панель модерации в #{channel.name}")
    
    async def _init_participant_channel(self):
        try:
            channel = self.bot.get_channel(int(self.participant_channel_id))
            if not channel:
                logger.error(f"❌ Канал сбора участников {self.participant_channel_id} не найден")
                return
        except (ValueError, TypeError):
            logger.error(f"❌ Неверный ID канала сбора: {self.participant_channel_id}")
            return
        
        print(f"🎯 [EVENTS] Канал сбора участников готов: #{channel.name}")
    
    async def _init_settings_channel(self):
        try:
            if not self.settings_channel_id:
                return
            channel = self.bot.get_channel(int(self.settings_channel_id))
            if not channel:
                logger.error(f"❌ Канал настроек {self.settings_channel_id} не найден")
                return
        except (ValueError, TypeError):
            logger.error(f"❌ Неверный ID канала настроек: {self.settings_channel_id}")
            return
        
        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКА МЕРОПРИЯТИЙ**",
            description="Настройка системы мероприятий",
            color=0x00ff00
        )
        
        view = EventsSettingsView()
        
        found = False
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds and "НАСТРОЙКА МЕРОПРИЯТИЙ" in msg.embeds[0].title:
                    await msg.edit(embed=embed, view=view)
                    found = True
                    print(f"🎯 [EVENTS] Обновлена панель настроек в #{channel.name}")
                    break
        
        if not found:
            await channel.send(embed=embed, view=view)
            print(f"🎯 [EVENTS] Создана панель настроек в #{channel.name}")
    
    async def _restore_sessions(self):
        sessions = db.get_active_event_sessions()
        
        if not sessions:
            return
        
        print(f"🎯 [EVENTS] Восстановление {len(sessions)} активных сессий...")
        
        for session in sessions:
            session_id = session['id']
            participants = db.get_event_participants(session_id)
            
            events_manager.active_sessions[session_id] = session
            events_manager.participants[session_id] = [p['user_id'] for p in participants]
            
            participant_channel_id = db.get_setting('events_participant_channel')
            if participant_channel_id:
                channel = self.bot.get_channel(int(participant_channel_id))
                if channel and session.get('message_id'):
                    try:
                        msg = await channel.fetch_message(int(session['message_id']))
                        content = self._build_participants_content(session, participants)
                        await msg.edit(content=content)
                    except:
                        pass
            
            print(f"🎯 [EVENTS] Восстановлена сессия #{session_id}, участников: {len(participants)}")
    
    def _build_participants_content(self, session: dict, participants: list) -> str:
        content = f"@everyone **🎯 МЕРОПРИЯТИЕ!**\n\n"
        content += f"👤 Организатор: <@{session['creator_id']}>\n"
        content += f"⏰ Начало: {session['event_time']} МСК\n"
        if session.get('additional_info'):
            content += f"📝 {session['additional_info']}\n"
        content += f"\n**Участники ({len(participants)}):**\n"
        if participants:
            for p in participants:
                content += f"└ <@{p['user_id']}>\n"
        else:
            content += "└ *Пока никого нет*"
        return content
    
    async def stop(self):
        if self.stats:
            await self.stats.stop()
        await events_manager.stop()
        print("🎯 [EVENTS] Система остановлена")


class ModerationMainView(discord.ui.View):
    """Главное меню модерации"""
    
    def __init__(self, templates: list):
        super().__init__(timeout=None)
        self.templates = templates
    
    @discord.ui.button(
        label="СОЗДАТЬ МП",
        style=discord.ButtonStyle.success,
        emoji="➕",
        row=0,
        custom_id="events_create"
    )
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.templates:
            await interaction.response.send_message(
                "❌ Нет доступных шаблонов мероприятий.\n"
                "Создайте шаблоны в планировщике мероприятий.",
                ephemeral=True
            )
            return
        
        await interaction.response.send_modal(CreateEventWithTemplateModal(self.templates))
    
    @discord.ui.button(
        label="ШАБЛОНЫ МП",
        style=discord.ButtonStyle.primary,
        emoji="📋",
        row=0,
        custom_id="events_templates"
    )
    async def manage_templates(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы могут управлять шаблонами!", ephemeral=True)
            return
        
        view = TemplateManagementView()
        embed = discord.Embed(
            title="📋 УПРАВЛЕНИЕ ШАБЛОНАМИ МЕРОПРИЯТИЙ",
            description="Создание и удаление шаблонов для мероприятий",
            color=0x00bfff
        )
        # Отправляем НОВОЕ сообщение (не редактируем)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(
        label="СТАТИСТИКА",
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        row=1,
        custom_id="events_stats"
    )
    async def show_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📊 СТАТИСТИКА МЕРОПРИЯТИЙ",
            color=0x00bfff,
            timestamp=datetime.now()
        )
        
        org_stats = db.get_event_organizer_stats(7)
        if org_stats:
            text = ""
            for i, stat in enumerate(org_stats[:5], 1):
                text += f"{i}. <@{stat['user_id']}> — **{stat['count']}** МП\n"
            embed.add_field(name="🏆 Топ организаторов (7 дней)", value=text, inline=False)
        else:
            embed.add_field(name="🏆 Топ организаторов", value="Нет данных", inline=False)
        
        total_sessions = len(db.get_active_event_sessions()) + len(db.get_all_event_sessions())
        embed.add_field(name="📋 Всего сессий", value=f"**{total_sessions}**", inline=True)
        
        view = StatsMenuView()
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(
        label="СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ",
        style=discord.ButtonStyle.primary,
        emoji="👤",
        row=1,
        custom_id="events_user_stats"
    )
    async def user_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UserStatsModal())


class StatsMenuView(discord.ui.View):
    """Дополнительные кнопки для статистики"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Топ организаторов (все время)",
        style=discord.ButtonStyle.secondary,
        emoji="📊",
        row=0,
        custom_id="stats_all_time"
    )
    async def all_time_orgs(self, interaction: discord.Interaction, button: discord.ui.Button):
        stats = db.get_event_organizer_stats(9999)
        
        embed = discord.Embed(
            title="🏆 ТОП ОРГАНИЗАТОРОВ (ВСЕ ВРЕМЯ)",
            color=0xffd700,
            timestamp=datetime.now()
        )
        
        if stats:
            text = ""
            medals = ["🥇", "🥈", "🥉"]
            for i, stat in enumerate(stats[:10], 1):
                medal = medals[i-1] if i <= 3 else f"{i}."
                text += f"{medal} <@{stat['user_id']}> — **{stat['count']}** МП\n"
            embed.description = text
        else:
            embed.description = "Нет данных"
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(
        label="Все сессии",
        style=discord.ButtonStyle.secondary,
        emoji="📋",
        row=1,
        custom_id="stats_all_sessions"
    )
    async def all_sessions(self, interaction: discord.Interaction, button: discord.ui.Button):
        sessions = db.get_all_event_sessions()
        
        if not sessions:
            await interaction.response.send_message("📭 Нет завершённых сессий", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 ВСЕ СЕССИИ МЕРОПРИЯТИЙ",
            color=0x7289da,
            timestamp=datetime.now()
        )
        
        for session in sessions[:10]:
            participants = db.get_event_participants(session['id'])
            embed.add_field(
                name=f"ID: {session['id']} | {session['event_time']}",
                value=f"👤 Организатор: <@{session['creator_id']}>\n👥 Участников: {len(participants)}",
                inline=False
            )
        
        if len(sessions) > 10:
            embed.set_footer(text=f"Показано 10 из {len(sessions)} сессий")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(
        label="Назад",
        style=discord.ButtonStyle.secondary,
        emoji="◀",
        row=2,
        custom_id="stats_back"
    )
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        templates = get_event_templates()
        embed = discord.Embed(
            title="🎯 **ПАНЕЛЬ УПРАВЛЕНИЯ МЕРОПРИЯТИЯМИ**",
            description="Создание и управление мероприятиями\n\n"
                        f"📋 **Доступно шаблонов:** {len(templates)}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Нажмите кнопку «➕ СОЗДАТЬ МП» чтобы начать",
            color=0x00bfff
        )
        await interaction.response.edit_message(embed=embed, view=ModerationMainView(templates))


class TemplateManagementView(discord.ui.View):
    """Управление шаблонами мероприятий"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Создать шаблон",
        style=discord.ButtonStyle.success,
        emoji="➕",
        row=0,
        custom_id="template_create"
    )
    async def create_template(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        # 🔥 ПРЯМО ОТПРАВЛЯЕМ МОДАЛКУ
        from event_scheduler.modals import AddEventSettingsModal
        await interaction.response.send_modal(AddEventSettingsModal())
    
    @discord.ui.button(
        label="Список шаблонов",
        style=discord.ButtonStyle.secondary,
        emoji="📋",
        row=0,
        custom_id="template_list"
    )
    async def list_templates(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        templates = get_event_templates(enabled_only=False)
        
        if not templates:
            await interaction.response.send_message("📭 Нет созданных шаблонов", ephemeral=True)
            return
        
        days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        embed = discord.Embed(
            title="📋 ШАБЛОНЫ МЕРОПРИЯТИЙ",
            color=0x00bfff,
            timestamp=datetime.now()
        )
        
        text = ""
        for t in templates:
            status = "✅" if t['enabled'] else "❌"
            text += f"{status} **{t['name']}** — {days[t['weekday']]} {t['event_time']}\n"
        
        embed.description = text
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(
        label="Назад",
        style=discord.ButtonStyle.secondary,
        emoji="◀",
        row=1,
        custom_id="template_back"
    )
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        templates = get_event_templates()
        embed = discord.Embed(
            title="🎯 **ПАНЕЛЬ УПРАВЛЕНИЯ МЕРОПРИЯТИЯМИ**",
            description="Создание и управление мероприятиями\n\n"
                        f"📋 **Доступно шаблонов:** {len(templates)}\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"Нажмите кнопку «➕ СОЗДАТЬ МП» чтобы начать",
            color=0x00bfff
        )
        await interaction.response.edit_message(embed=embed, view=ModerationMainView(templates))


class CreateEventWithTemplateModal(discord.ui.Modal, title="🎯 СОЗДАНИЕ МП"):
    """Модалка с выбором шаблона"""
    
    def __init__(self, templates: list):
        super().__init__()
        self.templates = templates
        
        self.template_select = discord.ui.Select(
            placeholder="Выберите шаблон мероприятия",
            options=format_templates_for_select(templates)
        )
        self.template_select.callback = self.select_template
        self.add_item(self.template_select)
    
    async def select_template(self, interaction: discord.Interaction):
        self.selected_template_id = int(self.template_select.values[0])
        await interaction.response.defer()
        
        modal = CreateEventModal(self.templates)
        modal.selected_template_id = self.selected_template_id
        await interaction.followup.send_modal(modal)


class UserStatsModal(discord.ui.Modal, title="👤 СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ"):
    user_id = discord.ui.TextInput(
        label="ID пользователя",
        placeholder="Введите ID пользователя",
        max_length=20,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = self.user_id.value
            
            org_stats = db.get_event_organizer_stats_by_user(uid, 30)
            part_stats = db.get_user_event_participations(uid, 30)
            
            embed = discord.Embed(
                title=f"👤 СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ",
                description=f"<@{uid}>",
                color=0x00bfff,
                timestamp=datetime.now()
            )
            
            if org_stats:
                embed.add_field(
                    name="📋 Организовал МП (30 дней)",
                    value=f"**{org_stats}** МП",
                    inline=True
                )
            else:
                embed.add_field(name="📋 Организовал МП", value="0", inline=True)
            
            if part_stats:
                embed.add_field(
                    name="✅ Участвовал в МП (30 дней)",
                    value=f"**{len(part_stats)}** МП",
                    inline=True
                )
                
                text = ""
                for stat in part_stats[:5]:
                    text += f"• {stat['event_time']} — ID: {stat['session_id']}\n"
                if len(part_stats) > 5:
                    text += f"*и ещё {len(part_stats) - 5}*"
                embed.add_field(name="📝 Участия", value=text or "Нет данных", inline=False)
            else:
                embed.add_field(name="✅ Участвовал в МП", value="0", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


initializer = None

async def setup(bot):
    global initializer
    initializer = EventsInitializer(bot)
    await initializer.initialize_all()
    return initializer