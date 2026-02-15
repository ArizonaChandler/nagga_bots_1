"""Event Views - Кнопки для мероприятий"""
import discord
import logging
import traceback
from datetime import datetime, timedelta
import pytz
from core.database import db
from core.config import CONFIG
from core.menus import BaseMenuView

# Настройка логирования
file_logger = logging.getLogger('events_views')
file_logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('events_views.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
file_logger.addHandler(fh)

MSK_TZ = pytz.timezone('Europe/Moscow')

class EventReminderView(discord.ui.View):
    """Кнопка 'Взять МП' с поддержкой нескольких каналов"""
    _instances = {}  # Словарь для хранения всех экземпляров по event_id
    
    def __init__(self, event_id: int, event_name: str, event_time: str, meeting_time: str, guild, reminder_channels=None):
        from datetime import datetime, timedelta
        import pytz
        
        msk_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(msk_tz)
        
        # Парсим время мероприятия
        event_hour, event_min = map(int, event_time.split(':'))
        
        # Создаем datetime для времени мероприятия
        event_datetime = msk_tz.localize(datetime(
            now.year, now.month, now.day,
            event_hour, event_min
        ))
        
        # Если время мероприятия уже прошло - добавляем день
        if event_datetime < now:
            event_datetime += timedelta(days=1)
        
        # Время таймаута (за 10 минут до начала)
        timeout_datetime = event_datetime - timedelta(minutes=10)
        timeout_seconds = max(0, (timeout_datetime - now).total_seconds())
        
        super().__init__(timeout=timeout_seconds)
        
        self.event_id = event_id
        self.event_name = event_name
        self.event_time = event_time
        self.meeting_time = meeting_time
        self.guild = guild
        self.taken = False
        self.messages = {}  # Словарь {channel_id: message}
        self.reminder_channels = reminder_channels or []
        self.timeout_occurred = False
        
        # Регистрируем этот экземпляр в общем словаре
        if event_id not in EventReminderView._instances:
            EventReminderView._instances[event_id] = []
        EventReminderView._instances[event_id].append(self)
        
        file_logger.debug(f"Зарегистрирован экземпляр для event_id {event_id}. Всего: {len(EventReminderView._instances[event_id])}")
    
    def add_message(self, message, channel_id):
        """Добавить сообщение из конкретного канала"""
        self.messages[str(channel_id)] = message
        file_logger.debug(f"Добавлено сообщение для канала {channel_id}")
    
    async def update_all_instances(self, user_id: str, user_name: str, group_code: str, meeting_place: str):
        """Обновить ВСЕ экземпляры этого мероприятия во всех каналах"""
        file_logger.debug(f"Обновление всех экземпляров для event_id {self.event_id}")
        
        # Получаем роли для оповещений
        announce_roles = CONFIG.get('announce_roles', [])
        role_mentions = []
        
        # Получаем сервер
        server_id = CONFIG.get('server_id')
        if server_id:
            guild = self.guild or (list(self.messages.values())[0].guild if self.messages else None)
            if guild:
                for role_id in announce_roles:
                    try:
                        role = guild.get_role(int(role_id))
                        if role:
                            role_mentions.append(role.mention)
                    except:
                        pass
        
        content = ' '.join(role_mentions) if role_mentions else None
        
        embed = discord.Embed(
            title=f"✅ СБОР НА МЕРОПРИЯТИЕ: {self.event_name}",
            description=f"Мероприятие проведёт: <@{user_id}>",
            color=0x00ff00
        )
        
        embed.add_field(
            name="⏱️ Сбор в",
            value=f"**{self.meeting_time}** МСК",
            inline=False
        )
        
        embed.add_field(
            name="📍 Место сбора",
            value=meeting_place,
            inline=True
        )
        
        embed.add_field(
            name="🔢 Код группы",
            value=group_code,
            inline=True
        )
        
        embed.add_field(
            name="Участие:",
            value="Для участия зайди в игру, в войс и приедь на место сбора",
            inline=False
        )
        
        embed.set_footer(text="Unit Management System by Nagga")
        
        # Обновляем ВСЕ экземпляры этого мероприятия
        if self.event_id in EventReminderView._instances:
            for instance in EventReminderView._instances[self.event_id]:
                instance.taken = True
                for child in instance.children:
                    child.disabled = True
                
                # Обновляем все сообщения этого экземпляра
                for channel_id, message in instance.messages.items():
                    try:
                        await message.edit(content=content, embed=embed, view=instance)
                        file_logger.debug(f"Обновлено сообщение в канале {channel_id} (экземпляр {id(instance)})")
                    except Exception as e:
                        file_logger.error(f"Ошибка обновления сообщения в канале {channel_id}: {e}")
        
        file_logger.info(f"✅ Все экземпляры для event_id {self.event_id} обновлены")
    
    @discord.ui.button(label="🎮 ВЗЯТЬ МП", style=discord.ButtonStyle.success, emoji="🎮")
    async def take_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        file_logger.debug("="*50)
        file_logger.debug("take_event CALLED")
        
        if self.timeout_occurred:
            await interaction.response.send_message("⏰ Время на взятие МП истекло!", ephemeral=True)
            return
        
        if self.taken:
            await interaction.response.send_message("❌ Уже взято", ephemeral=True)
            return
        
        today = datetime.now(MSK_TZ).date().isoformat()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT taken_by FROM event_schedule 
                WHERE event_id = ? AND scheduled_date = ?
            ''', (self.event_id, today))
            result = cursor.fetchone()
            
            if result and result[0]:
                self.taken = True
                button.disabled = True
                
                # Обновляем ВСЕ экземпляры
                await self.update_all_instances(
                    result[0],
                    "Пользователь",
                    "Будет указано",
                    "Будет указано"
                )
                
                await interaction.response.send_message(f"❌ Уже взял <@{result[0]}>", ephemeral=True)
                return
        
        from admin.modals import TakeEventModal
        modal = TakeEventModal(
            self.event_id, 
            self.event_name, 
            self.event_time, 
            self.meeting_time,
            self  # Передаем view для обратного вызова
        )
        await interaction.response.send_modal(modal)
    
    async def update_taken_status(self, user_id: str, user_name: str, group_code: str, meeting_place: str):
        """Обновить статус после взятия МП во всех каналах"""
        # Просто вызываем update_all_instances
        await self.update_all_instances(user_id, user_name, group_code, meeting_place)
    
    async def on_timeout(self):
        """Когда время вышло (за 10 минут до начала)"""
        self.timeout_occurred = True
        if not self.taken and self.messages:
            # Отключаем все кнопки
            for child in self.children:
                child.disabled = True
            
            embed = discord.Embed(
                title=f"⏰ ВРЕМЯ ВЫШЛО: {self.event_name}",
                description=f"Мероприятие в **{self.event_time}** не состоялось - никто не взял его вовремя.",
                color=0xff0000
            )
            
            embed.add_field(
                name="⏰ Время начала",
                value=f"**{self.event_time}** МСК",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Сбор был в",
                value=f"**{self.meeting_time}** МСК",
                inline=True
            )
            
            embed.set_footer(text="Unit Management System by Nagga")
            
            # Обновляем все сообщения
            for channel_id, message in self.messages.items():
                try:
                    await message.edit(embed=embed, view=self)
                except Exception as e:
                    file_logger.error(f"Ошибка обновления сообщения в канале {channel_id}: {e}")


class EventInfoView(BaseMenuView):
    """Кнопка информации о мероприятии в !info"""
    def __init__(self, user_id: str, guild, previous_view=None, previous_embed=None):
        super().__init__(user_id, guild, previous_view, previous_embed)
        self.add_item(self.create_today_button())
    
    def create_today_button(self):
        btn = discord.ui.Button(label="📅 Мероприятия сегодня", style=discord.ButtonStyle.primary, emoji="📅")
        async def callback(interaction: discord.Interaction):
            self.clear_items()
            self.add_back_button()
            await self.show_today_events(interaction)
        btn.callback = callback
        return btn
    
    async def show_today_events(self, interaction: discord.Interaction):
        try:
            now = datetime.now(MSK_TZ)
            today = now.date()
            weekday = today.weekday()
            current_time_str = now.strftime("%H:%M")
            
            # Получаем все мероприятия на сегодня
            events = db.get_events(enabled_only=True, weekday=weekday)
            
            if not events:
                await interaction.response.edit_message(
                    content="📅 На сегодня мероприятий нет",
                    embed=None,
                    view=self
                )
                return
            
            # Фильтруем мероприятия
            visible_events = []
            for event in events:
                event_time = event['event_time']
                event_hour, event_min = map(int, event_time.split(':'))
                
                # Создаем datetime для времени мероприятия
                event_datetime = MSK_TZ.localize(datetime(
                    today.year, today.month, today.day,
                    event_hour, event_min
                ))
                
                # Проверяем, взято ли мероприятие
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT taken_by FROM event_schedule 
                        WHERE event_id = ? AND scheduled_date = ?
                    ''', (event['id'], today.isoformat()))
                    result = cursor.fetchone()
                    taken_by = result[0] if result else None
                
                # Показываем если:
                # 1. Мероприятие ещё не началось ИЛИ
                # 2. Мероприятие идёт И ЕГО ВЗЯЛИ (до +1 часа после начала)
                if now < event_datetime:
                    # Будущее мероприятие
                    visible_events.append(event)
                elif taken_by and now <= event_datetime + timedelta(hours=1):
                    # Идущее мероприятие (только если взято)
                    visible_events.append(event)
            
            if not visible_events:
                await interaction.response.edit_message(
                    content="📅 На сегодня нет актуальных мероприятий",
                    embed=None,
                    view=self
                )
                return
            
            # Сортируем по времени
            visible_events.sort(key=lambda x: x['event_time'])
            
            embed = discord.Embed(
                title=f"📅 АКТУАЛЬНЫЕ МЕРОПРИЯТИЯ ({today.strftime('%d.%m.%Y')})",
                description=f"⏰ Текущее время: **{current_time_str}** МСК",
                color=0x7289da
            )
            
            for event in visible_events:
                event_time = event['event_time']
                event_hour, event_min = map(int, event_time.split(':'))
                event_datetime = MSK_TZ.localize(datetime(
                    today.year, today.month, today.day,
                    event_hour, event_min
                ))
                
                # Вычисляем время напоминания (за 1 час)
                reminder_datetime = event_datetime - timedelta(hours=1)
                reminder_time = reminder_datetime.strftime("%H:%M")
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT taken_by, group_code, meeting_place, reminder_sent 
                        FROM event_schedule 
                        WHERE event_id = ? AND scheduled_date = ?
                    ''', (event['id'], today.isoformat()))
                    result = cursor.fetchone()
                
                # Определяем статус
                if result and result[0]:  # Взято
                    if now > event_datetime:
                        # Идёт сейчас
                        status = f"🔴 **Проводит:** <@{result[0]}>\n📍 {result[2]}\n🔢 {result[1]}"
                    else:
                        # Будет
                        status = f"✅ **Проводит:** <@{result[0]}>\n📍 {result[2]}\n🔢 {result[1]}"
                else:
                    # Не взято
                    if now >= reminder_datetime:
                        # Напоминание уже пришло
                        status = "⏳ **Ожидаем информацию от HIGH состава**"
                    else:
                        # Напоминание ещё не пришло
                        minutes_to = int((event_datetime - now).total_seconds() / 60)
                        status = f"🕒 **Начнётся через {minutes_to} мин**"
                
                embed.add_field(
                    name=f"{event_time} — {event['name']}",
                    value=status,
                    inline=False
                )
            
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            file_logger.error(f"Ошибка в show_today_events: {e}")
            await interaction.response.edit_message(
                content=f"❌ Ошибка при загрузке мероприятий",
                embed=None,
                view=self
            )