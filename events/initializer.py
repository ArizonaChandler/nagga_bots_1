"""Инициализация каналов системы мероприятий"""
import discord
import logging
from datetime import datetime
from core.database import db
from core.config import CONFIG
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
        
        if self.moderation_channel_id:
            await self._init_moderation_channel()
        
        if self.participant_channel_id:
            await self._init_participant_channel()
        
        if self.settings_channel_id:
            await self._init_settings_channel()
        
        # Восстанавливаем активные сессии
        await self._restore_sessions()
        
        # Запускаем еженедельную статистику
        self.stats = EventStats(self.bot)
        await self.stats.start()
        print("📊 [EVENTS] Еженедельная статистика запущена")
        
        logger.info("✅ Инициализация системы мероприятий завершена")
        print("🎯 [EVENTS] Инициализация завершена")
    
    async def _init_moderation_channel(self):
        """Канал модерации — кнопка создания МП и статистика"""
        try:
            channel = self.bot.get_channel(int(self.moderation_channel_id))
            if not channel:
                logger.error(f"❌ Канал модерации {self.moderation_channel_id} не найден")
                return
        except (ValueError, TypeError):
            logger.error(f"❌ Неверный ID канала модерации: {self.moderation_channel_id}")
            return
        
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.delete()
        
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
        await channel.send(embed=embed, view=view)
        print(f"🎯 [EVENTS] Создана панель модерации в #{channel.name}")
    
    async def _init_participant_channel(self):
        """Канал сбора участников — очистка"""
        try:
            channel = self.bot.get_channel(int(self.participant_channel_id))
            if not channel:
                logger.error(f"❌ Канал сбора участников {self.participant_channel_id} не найден")
                return
        except (ValueError, TypeError):
            logger.error(f"❌ Неверный ID канала сбора: {self.participant_channel_id}")
            return
        
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.delete()
        
        print(f"🎯 [EVENTS] Канал сбора участников очищен: #{channel.name}")
    
    async def _init_settings_channel(self):
        """Канал настроек"""
        try:
            channel = self.bot.get_channel(int(self.settings_channel_id))
            if not channel:
                logger.error(f"❌ Канал настроек {self.settings_channel_id} не найден")
                return
        except (ValueError, TypeError):
            logger.error(f"❌ Неверный ID канала настроек: {self.settings_channel_id}")
            return
        
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.delete()
        
        embed = discord.Embed(
            title="⚙️ **НАСТРОЙКА МЕРОПРИЯТИЙ**",
            description="Настройка системы мероприятий",
            color=0x00ff00
        )
        await channel.send(embed=embed, view=EventsSettingsView())
        print(f"🎯 [EVENTS] Создана панель настроек в #{channel.name}")
    
    async def _restore_sessions(self):
        """Восстановить активные сессии после перезапуска"""
        sessions = db.get_active_event_sessions()
        
        if not sessions:
            return
        
        print(f"🎯 [EVENTS] Восстановление {len(sessions)} активных сессий...")
        
        for session in sessions:
            session_id = session['id']
            participants = db.get_event_participants(session_id)
            
            # Восстанавливаем в память
            events_manager.active_sessions[session_id] = session
            events_manager.participants[session_id] = [p['user_id'] for p in participants]
            
            # Обновляем сообщение в канале сбора
            participant_channel_id = db.get_setting('events_participant_channel')
            if participant_channel_id:
                channel = self.bot.get_channel(int(participant_channel_id))
                if channel and session.get('message_id'):
                    try:
                        msg = await channel.fetch_message(int(session['message_id']))
                        # Обновляем список участников
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
        """Остановка модуля"""
        if self.stats:
            await self.stats.stop()
        await events_manager.stop()
        print("🎯 [EVENTS] Система остановлена")


class ModerationMainView(discord.ui.View):
    """Главное меню модерации"""
    
    def __init__(self, templates: list):
        super().__init__(timeout=None)
        self.templates = templates
    
    @discord.ui.button(label="➕ СОЗДАТЬ МП", style=discord.ButtonStyle.success, emoji="➕", row=0)
    async def create_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Создать новое мероприятие"""
        if not self.templates:
            await interaction.response.send_message(
                "❌ Нет доступных шаблонов мероприятий.\n"
                "Создайте шаблоны в планировщике мероприятий.",
                ephemeral=True
            )
            return
        
        await interaction.response.send_modal(CreateEventWithTemplateModal(self.templates))
    
    @discord.ui.button(label="📊 СТАТИСТИКА", style=discord.ButtonStyle.secondary, emoji="📊", row=0)
    async def show_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать статистику"""
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
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


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
        """Обработка выбора шаблона"""
        self.selected_template_id = int(self.template_select.values[0])
        await interaction.response.defer()
        
        modal = CreateEventModal(self.templates)
        modal.selected_template_id = self.selected_template_id
        await interaction.followup.send_modal(modal)


# ========== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР И ФУНКЦИЯ SETUP ==========

initializer = None

async def setup(bot):
    global initializer
    initializer = EventsInitializer(bot)
    await initializer.initialize_all()
    return initializer