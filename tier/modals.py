"""Модалки для системы TIER"""
import discord
from tier.manager import tier_manager
from datetime import datetime


class TierApplicationModal(discord.ui.Modal, title="🌟 ЗАЯВКА НА TIER"):
    """Модалка для подачи заявки на повышение"""
    
    nickname = discord.ui.TextInput(
        label="🎮 Игровой ник",
        placeholder="Ваш ник в игре",
        max_length=50,
        required=True
    )
    
    arena_link = discord.ui.TextInput(
        label="🏆 Ссылка на откат с арены",
        placeholder="Ссылка на видео/откат",
        max_length=200,
        required=True
    )
    
    screenshots = discord.ui.TextInput(
        label="📸 Ссылки на скриншоты (мин. 5)",
        placeholder="Ссылка1, ссылка2, ссылка3...",
        max_length=500,
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    additional = discord.ui.TextInput(
        label="📝 Дополнительная информация",
        placeholder="Любая дополнительная информация",
        max_length=500,
        required=False,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Определяем текущий тир пользователя (для информации, но не для ограничения)
        current_tier = tier_manager.get_user_current_tier(str(interaction.user.id), interaction.guild)
        
        # Создаём заявку (без указания target_tier, модератор сам выберет)
        app_id, error = tier_manager.create_application(
            user_id=str(interaction.user.id),
            user_name=interaction.user.display_name,
            nickname=self.nickname.value,
            arena_link=self.arena_link.value,
            screenshots=self.screenshots.value,
            additional=self.additional.value or "Нет",
            target_tier="pending"  # временное значение
        )
        
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return
        
        # Отправляем подтверждение
        embed = discord.Embed(
            title="✅ ЗАЯВКА ОТПРАВЛЕНА",
            description=f"Ваша заявка принята и передана на рассмотрение.",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Отправляем заявку в канал модерации
        settings = tier_manager.get_settings()
        applications_channel_id = settings.get('tier_applications_channel')
        
        if applications_channel_id:
            channel = interaction.client.get_channel(int(applications_channel_id))
            if channel:
                from tier.views import TierModerationView
                
                embed = discord.Embed(
                    title="🌟 НОВАЯ ЗАЯВКА НА TIER",
                    color=0xffa500,
                    timestamp=datetime.now()
                )
                embed.add_field(name="👤 Отправитель", value=interaction.user.mention, inline=True)
                embed.add_field(name="🎮 Игровой ник", value=self.nickname.value, inline=True)
                embed.add_field(name="🏆 Откат с арены", value=self.arena_link.value, inline=False)
                embed.add_field(name="📸 Скриншоты", value=self.screenshots.value[:200], inline=False)
                embed.add_field(name="📝 Дополнительно", value=self.additional.value or "Нет", inline=False)
                embed.set_footer(text=f"Заявка ID: {app_id}")
                
                # Отправляем сообщение с кнопками
                sent_message = await channel.send(embed=embed, view=TierModerationView(app_id))
                
                # ===== СОХРАНЯЕМ ID СООБЩЕНИЯ ДЛЯ ВОССТАНОВЛЕНИЯ =====
                tier_manager.save_application_message(
                    application_id=app_id,
                    channel_id=str(channel.id),
                    message_id=str(sent_message.id),
                    user_id=str(interaction.user.id)
                )
                print(f"✅ Заявка TIER отправлена и сохранена (message_id: {sent_message.id})")
                # ===== КОНЕЦ СОХРАНЕНИЯ =====