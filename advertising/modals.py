"""Auto Advertising Modals - Настройка авто-рекламы"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG
from core.utils import is_admin

class SetAdMessageModal(discord.ui.Modal, title="📢 НАСТРОЙКА РЕКЛАМЫ"):
    def __init__(self):
        super().__init__()
        
        # Загружаем настройки сразу для предзаполнения
        settings = db.get_active_ad()
        
        # Поле для текста сообщения
        self.message_text = discord.ui.TextInput(
            label="📝 Текст сообщения",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True,
            default=settings.get('message_text', '') if settings else ''
        )
        
        # Поле для URL картинки (опционально)
        self.image_url = discord.ui.TextInput(
            label="🖼️ URL картинки (необязательно)",
            placeholder="https://i.imgur.com/example.jpg",
            max_length=500,
            required=False,
            default=settings.get('image_url', '') if settings else ''
        )
        
        # Поле для ID канала
        self.channel_id = discord.ui.TextInput(
            label="📢 ID канала",
            placeholder="123456789012345678",
            max_length=20,
            required=True,
            default=settings.get('channel_id', '') if settings else ''
        )
        
        # Поле для интервала
        default_interval = str(settings.get('interval_minutes', 65)) if settings else '65'
        self.interval = discord.ui.TextInput(
            label="⏱️ Интервал (минуты)",
            placeholder="65",
            max_length=5,
            required=True,
            default=default_interval
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        # ШАГ 1: Проверка прав
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        # ШАГ 2: Получаем сервер
        server_id = CONFIG.get('server_id')
        if not server_id:
            await interaction.response.send_message(
                "❌ Сначала установите ID сервера в Глобальных настройках",
                ephemeral=True
            )
            return
        
        guild = interaction.client.get_guild(int(server_id))
        if not guild:
            await interaction.response.send_message(
                f"❌ Сервер с ID {server_id} не найден. Бот не добавлен на сервер?",
                ephemeral=True
            )
            return
        
        # ШАГ 3: Проверка канала
        try:
            channel_id = int(self.channel_id.value)
            channel = guild.get_channel(channel_id)
            
            # Проверяем существование канала
            if not channel:
                # Пробуем найти через бота
                channel = interaction.client.get_channel(channel_id)
            
            if not channel:
                await interaction.response.send_message(
                    f"❌ Канал с ID {channel_id} не найден на сервере {guild.name}\n"
                    f"Убедитесь что:\n"
                    f"1. ID канала правильный\n"
                    f"2. Бот имеет доступ к каналу\n"
                    f"3. Канал существует",
                    ephemeral=True
                )
                return
            
            # Проверяем права бота в канале
            permissions = channel.permissions_for(guild.me)
            if not permissions.send_messages:
                await interaction.response.send_message(
                    f"❌ У бота нет прав на отправку сообщений в канал {channel.mention}",
                    ephemeral=True
                )
                return
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Неверный формат ID канала. ID должен состоять только из цифр",
                ephemeral=True
            )
            return
        
        # ШАГ 4: Проверка интервала
        try:
            interval = int(self.interval.value)
            if interval < 1:
                await interaction.response.send_message(
                    "❌ Интервал должен быть больше 0 минут",
                    ephemeral=True
                )
                return
            if interval > 1440:
                await interaction.response.send_message(
                    "❌ Интервал не может быть больше 24 часов (1440 минут)",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "❌ Интервал должен быть целым числом",
                ephemeral=True
            )
            return
        
        # ШАГ 5: Проверка URL картинки (если указана)
        if self.image_url.value:
            if not (self.image_url.value.startswith('http://') or self.image_url.value.startswith('https://')):
                await interaction.response.send_message(
                    "❌ URL картинки должен начинаться с http:// или https://",
                    ephemeral=True
                )
                return
            
            # Простая проверка расширения
            if not any(self.image_url.value.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                await interaction.response.send_message(
                    "⚠️ URL может не быть картинкой. Поддерживаемые форматы: JPG, PNG, GIF, WEBP",
                    ephemeral=True
                )
                # Не возвращаем ошибку, только предупреждение
        
        # ШАГ 6: Проверка текста
        if len(self.message_text.value) < 10:
            await interaction.response.send_message(
                "❌ Текст сообщения слишком короткий (минимум 10 символов)",
                ephemeral=True
            )
            return
        
        # ШАГ 7: Получаем текущие настройки для сохранения времени сна
        current_settings = db.get_active_ad()
        sleep_start = current_settings.get('sleep_start', '02:00') if current_settings else '02:00'
        sleep_end = current_settings.get('sleep_end', '06:30') if current_settings else '06:30'
        
        # ШАГ 8: Сохраняем в БД
        try:
            success = db.save_ad_settings(
                message_text=self.message_text.value,
                image_url=self.image_url.value if self.image_url.value else None,
                channel_id=str(channel_id),  # Сохраняем как строку
                interval=interval,
                sleep_start=sleep_start,
                sleep_end=sleep_end,
                updated_by=str(interaction.user.id)
            )
            
            if success:
                # Формируем красивое сообщение об успехе
                embed = discord.Embed(
                    title="✅ Настройки рекламы сохранены",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="📢 Канал",
                    value=channel.mention,
                    inline=True
                )
                
                embed.add_field(
                    name="⏱️ Интервал",
                    value=f"{interval} мин",
                    inline=True
                )
                
                embed.add_field(
                    name="😴 Режим сна",
                    value=f"{sleep_start} - {sleep_end}",
                    inline=True
                )
                
                # Добавляем предпросмотр текста
                text_preview = self.message_text.value[:100]
                if len(self.message_text.value) > 100:
                    text_preview += "..."
                embed.add_field(
                    name="📝 Текст (предпросмотр)",
                    value=text_preview,
                    inline=False
                )
                
                # Если есть картинка
                if self.image_url.value:
                    embed.add_field(
                        name="🖼️ Картинка",
                        value="✅ добавлена",
                        inline=True
                    )
                    # Показываем картинку в embed
                    embed.set_image(url=self.image_url.value)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    "❌ Ошибка сохранения в базу данных",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ошибка базы данных: {str(e)}",
                ephemeral=True
            )


class SetSleepTimeModal(discord.ui.Modal, title="😴 НАСТРОЙКА РЕЖИМА СНА"):
    def __init__(self):
        super().__init__()
        
        settings = db.get_active_ad()
        
        self.sleep_start = discord.ui.TextInput(
            label="⏰ Начало сна (ЧЧ:ММ)",
            placeholder="02:00",
            max_length=5,
            required=True,
            default=settings.get('sleep_start', '02:00') if settings else '02:00'
        )
        
        self.sleep_end = discord.ui.TextInput(
            label="⏰ Конец сна (ЧЧ:ММ)",
            placeholder="06:30",
            max_length=5,
            required=True,
            default=settings.get('sleep_end', '06:30') if settings else '06:30'
        )
    
    async def on_submit(self, interaction: discord.Interaction):
        # ШАГ 1: Проверка прав
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы", ephemeral=True)
            return
        
        # ШАГ 2: Проверка формата времени
        try:
            from datetime import datetime
            
            # Проверяем оба времени
            start_time = datetime.strptime(self.sleep_start.value, "%H:%M")
            end_time = datetime.strptime(self.sleep_end.value, "%H:%M")
            
            # Проверяем что время в пределах суток
            if start_time.hour > 23 or start_time.minute > 59:
                raise ValueError
            if end_time.hour > 23 or end_time.minute > 59:
                raise ValueError
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Неверный формат времени. Используйте ЧЧ:ММ (например 02:00)",
                ephemeral=True
            )
            return
        
        # ШАГ 3: Проверка что интервал не слишком большой
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        
        if start_minutes == end_minutes:
            await interaction.response.send_message(
                "❌ Время начала и конца не может совпадать",
                ephemeral=True
            )
            return
        
        # ШАГ 4: Получаем текущие настройки
        settings = db.get_active_ad()
        if not settings:
            await interaction.response.send_message(
                "❌ Сначала настройте основную рекламу (текст, канал, интервал)",
                ephemeral=True
            )
            return
        
        # ШАГ 5: Сохраняем
        try:
            success = db.save_ad_settings(
                message_text=settings['message_text'],
                image_url=settings.get('image_url'),
                channel_id=settings['channel_id'],
                interval=settings['interval_minutes'],
                sleep_start=self.sleep_start.value,
                sleep_end=self.sleep_end.value,
                updated_by=str(interaction.user.id)
            )
            
            if success:
                # Вычисляем длительность сна
                if start_minutes < end_minutes:
                    duration = end_minutes - start_minutes
                else:
                    duration = (24*60 - start_minutes) + end_minutes
                
                hours = duration // 60
                minutes = duration % 60
                
                embed = discord.Embed(
                    title="😴 Режим сна настроен",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                embed.add_field(
                    name="Время сна",
                    value=f"С {self.sleep_start.value} до {self.sleep_end.value}",
                    inline=True
                )
                embed.add_field(
                    name="Длительность",
                    value=f"{hours}ч {minutes}м",
                    inline=True
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    "❌ Ошибка сохранения",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ошибка: {str(e)}",
                ephemeral=True
            )