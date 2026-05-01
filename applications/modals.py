"""Модалки для системы заявок"""
import discord
from applications.manager import app_manager
from datetime import datetime
from server_stats.stat_collector import collector

class ApplicationModal(discord.ui.Modal, title="📝 ЗАЯВКА В СЕМЬЮ"):
    """Модалка для создания заявки"""
    
    nickname = discord.ui.TextInput(
        label="🎮 Игровой ник",
        placeholder="Ваш ник в игре",
        max_length=50,
        required=True
    )
    
    static = discord.ui.TextInput(
        label="🎯 Статик на сервере",
        placeholder="Например: #15542",
        max_length=100,
        required=True
    )
    
    previous_families = discord.ui.TextInput(
        label="🏠 Где и в каких семьях играли ранее",
        placeholder="Названия семей, если были",
        max_length=200,
        required=False,
        style=discord.TextStyle.paragraph
    )
    
    prime_time = discord.ui.TextInput(
        label="⏰ Прайм-тайм игры",
        placeholder="Например: 19:00-23:00 МСК",
        max_length=50,
        required=True
    )
    
    hours_per_day = discord.ui.TextInput(
        label="📊 Количество часов в игре в день",
        placeholder="Например: 4-6 часов",
        max_length=30,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        
        print(f"🔍 Начало обработки заявки от {interaction.user.id}")
        
        try:
            # Создаем заявку
            print("📝 Создание заявки в БД...")
            app_id, error = app_manager.create_application(
                user_id=str(interaction.user.id),
                user_name=interaction.user.display_name,
                nickname=self.nickname.value,
                static=self.static.value,
                previous_families=self.previous_families.value or "Не указано",
                prime_time=self.prime_time.value,
                hours_per_day=self.hours_per_day.value
            )
            
            if error:
                print(f"❌ Ошибка создания заявки: {error}")
                await interaction.response.send_message(error, ephemeral=True)
                return
            
            print(f"✅ Заявка создана с ID: {app_id}")
            
            # Увеличиваем счётчик новых заявок в статистике
            from server_stats.stat_collector import collector
            if collector:
                collector.increment_new_applications()
                print(f"📊 Статистика: новая заявка (#{app_id})")
            
            # Отправляем подтверждение пользователю
            embed = discord.Embed(
                title="✅ ЗАЯВКА ОТПРАВЛЕНА",
                description="Ваша заявка принята и передана на рассмотрение. Ожидайте решения.",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            print("✅ Подтверждение отправлено пользователю")
            
            # ===== ОТПРАВЛЯЕМ В КАНАЛ "ЗАЯВКИ В СЕМЬЮ" =====
            print("🔍 Получение настроек...")
            settings = app_manager.get_settings()
            applications_channel_id = settings.get('applications_channel')

            print(f"📢 applications_channel_id: {applications_channel_id}")
            
            if not applications_channel_id:
                print("❌ Канал для анкет не настроен")
                await interaction.followup.send(
                    "❌ Канал для анкет не настроен! Обратитесь к администратору.",
                    ephemeral=True
                )
                return

            applications_channel = interaction.client.get_channel(int(applications_channel_id))
            
            if not applications_channel:
                print(f"❌ Канал {applications_channel_id} не найден")
                await interaction.followup.send(
                    f"❌ Канал для заявок не найден!",
                    ephemeral=True
                )
                return
            
            print(f"✅ Канал найден: #{applications_channel.name}")
            
            # Создаем embed с заявкой
            embed = discord.Embed(
                title="📝 НОВАЯ ЗАЯВКА",
                color=0xffa500,
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Отправитель", value=interaction.user.mention, inline=True)
            embed.add_field(name="🎮 Игровой ник", value=self.nickname.value, inline=True)
            embed.add_field(name="🎯 Статик", value=self.static.value, inline=True)
            embed.add_field(name="🏠 Предыдущие семьи", value=self.previous_families.value or "Нет", inline=False)
            embed.add_field(name="⏰ Прайм-тайм", value=self.prime_time.value, inline=True)
            embed.add_field(name="📊 Часов в день", value=self.hours_per_day.value, inline=True)
            embed.set_footer(text=f"Заявка ID: {app_id}")
            
            # Добавляем тег роли рекрута
            recruit_role_id = settings.get('applications_recruit_role')
            content = None
            if recruit_role_id:
                content = f"<@&{recruit_role_id}>"
                print(f"👥 Тег роли рекрута: {content}")
            
            # Импортируем здесь, чтобы избежать циклического импорта
            from applications.views import ApplicationModerationView
            
            print("📤 Отправка заявки в канал модерации...")
            sent_message = await applications_channel.send(
                content=content,
                embed=embed,
                view=ApplicationModerationView(app_id, str(interaction.user.id))
            )
            
            # Сохраняем ID сообщения для восстановления после перезапуска
            app_manager.save_application_message(
                application_id=app_id,
                channel_id=str(applications_channel.id),
                message_id=str(sent_message.id),
                user_id=str(interaction.user.id)
            )
            print(f"✅ Заявка отправлена и сохранена (message_id: {sent_message.id})")
            
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.followup.send(
                    f"❌ Произошла ошибка: {e}",
                    ephemeral=True
                )
            except:
                pass