"""Модалки для системы TIR"""
import discord
from tier.manager import tier_manager

class TierApplicationModal(discord.ui.Modal, title="🌟 ЗАЯВКА НА TIR"):
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
    
    def __init__(self, target_tier: str):
        super().__init__()
        self.target_tier = target_tier
    
    async def on_submit(self, interaction: discord.Interaction):
        from tier.views import update_tier_embed
        
        # Проверяем текущий тир пользователя
        current_tier = tier_manager.get_user_current_tier(str(interaction.user.id), interaction.guild)
        
        # Определяем, на какой тир можно подать
        if self.target_tier == "tier3":
            if current_tier is not None:
                await interaction.response.send_message("❌ У вас уже есть тир! Вы можете подать заявку только на следующий уровень.", ephemeral=True)
                return
        elif self.target_tier == "tier2":
            if current_tier != "tier3":
                await interaction.response.send_message("❌ Для подачи на Tier 2 нужно сначала получить Tier 3!", ephemeral=True)
                return
        elif self.target_tier == "tier1":
            if current_tier != "tier2":
                await interaction.response.send_message("❌ Для подачи на Tier 1 нужно сначала получить Tier 2!", ephemeral=True)
                return
        
        # Создаем заявку
        app_id, error = tier_manager.create_application(
            user_id=str(interaction.user.id),
            user_name=interaction.user.display_name,
            nickname=self.nickname.value,
            arena_link=self.arena_link.value,
            screenshots=self.screenshots.value,
            additional=self.additional.value or "Нет",
            target_tier=self.target_tier
        )
        
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return
        
        # Отправляем подтверждение
        embed = discord.Embed(
            title="✅ ЗАЯВКА ОТПРАВЛЕНА",
            description=f"Ваша заявка на **{self.target_tier.upper()}** принята и передана на рассмотрение.",
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
                    title=f"🌟 НОВАЯ ЗАЯВКА НА {self.target_tier.upper()}",
                    color=0xffa500,
                    timestamp=datetime.now()
                )
                embed.add_field(name="👤 Отправитель", value=interaction.user.mention, inline=True)
                embed.add_field(name="🎮 Игровой ник", value=self.nickname.value, inline=True)
                embed.add_field(name="🏆 Откат с арены", value=self.arena_link.value, inline=False)
                embed.add_field(name="📸 Скриншоты", value=self.screenshots.value[:200], inline=False)
                embed.add_field(name="📝 Дополнительно", value=self.additional.value or "Нет", inline=False)
                embed.set_footer(text=f"Заявка ID: {app_id}")
                
                await channel.send(embed=embed, view=TierModerationView(app_id, self.target_tier))