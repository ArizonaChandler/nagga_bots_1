"""Модалки для системы заявок"""
import discord
from applications.manager import app_manager
from datetime import datetime

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
        placeholder="Например: фарм, пвп, квиз и т.д.",
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
        
        # Создаем заявку
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
            await interaction.response.send_message(error, ephemeral=True)
            return
        
        # Отправляем подтверждение
        embed = discord.Embed(
            title="✅ ЗАЯВКА ОТПРАВЛЕНА",
            description="Ваша заявка принята и передана на рассмотрение. Ожидайте решения.",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Отправляем заявку в канал модерации
        settings = app_manager.get_settings()
        channel_id = settings.get('applications_channel')
        
        if channel_id:
            channel = interaction.client.get_channel(int(channel_id))
            if channel:
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
                
                from applications.views import ApplicationModerationView
                await channel.send(embed=embed, view=ApplicationModerationView(app_id))