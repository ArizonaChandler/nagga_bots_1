"""Кнопки для системы TIR"""
import discord
from datetime import datetime
from tier.base import PermanentView
from tier.modals import TierApplicationModal
from tier.manager import tier_manager
from core.config import CONFIG

async def update_tier_embed(bot, tier_info_channel_id: str):
    """Обновить embed с информацией о требованиях к тирам"""
    channel = bot.get_channel(int(tier_info_channel_id))
    if not channel:
        return
    
    # Ищем существующее сообщение
    target_message = None
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.embeds:
            if msg.embeds and "🌟 СИСТЕМА TIR" in msg.embeds[0].title:
                target_message = msg
                break
    
    if not target_message:
        return
    
    # Получаем требования для каждого тира
    tier3_req = tier_manager.get_tier_requirements("tier3") or "Не установлены"
    tier2_req = tier_manager.get_tier_requirements("tier2") or "Не установлены"
    tier1_req = tier_manager.get_tier_requirements("tier1") or "Не установлены"
    
    embed = discord.Embed(
        title="🌟 **СИСТЕМА TIR**",
        description="Повышение уровня в семье",
        color=0xffa500,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="🟤 TIER 3",
        value=f"**Требования:**\n{tier3_req}\n\n**Награда:**\n└ Роль Tier 3",
        inline=False
    )
    
    embed.add_field(
        name="⚪ TIER 2",
        value=f"**Требования:**\n{tier2_req}\n\n**Награда:**\n└ Роль Tier 2\n└ Снятие роли Tier 3",
        inline=False
    )
    
    embed.add_field(
        name="🔴 TIER 1",
        value=f"**Требования:**\n{tier1_req}\n\n**Награда:**\n└ Роль Tier 1\n└ Снятие роли Tier 2",
        inline=False
    )
    
    embed.set_footer(text="Подать заявку можно в канале #заявка-на-tier")
    
    await target_message.edit(embed=embed)


class TierInfoView(PermanentView):
    """Кнопки для информации о тирах"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(
        label="🌟 ПОДАТЬ НА TIER 3", 
        style=discord.ButtonStyle.primary,
        emoji="🌟",
        custom_id="tier_apply_3"
    )
    async def apply_tier3(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Подать заявку на Tier 3"""
        await interaction.response.send_modal(TierApplicationModal("tier3"))
    
    @discord.ui.button(
        label="⚪ ПОДАТЬ НА TIER 2", 
        style=discord.ButtonStyle.secondary,
        emoji="⚪",
        custom_id="tier_apply_2"
    )
    async def apply_tier2(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Подать заявку на Tier 2"""
        await interaction.response.send_modal(TierApplicationModal("tier2"))
    
    @discord.ui.button(
        label="🔴 ПОДАТЬ НА TIER 1", 
        style=discord.ButtonStyle.danger,
        emoji="🔴",
        custom_id="tier_apply_1"
    )
    async def apply_tier1(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Подать заявку на Tier 1"""
        await interaction.response.send_modal(TierApplicationModal("tier1"))


class TierModerationView(discord.ui.View):
    """Кнопки для модерации заявки на тир"""
    
    def __init__(self, application_id: int, target_tier: str):
        super().__init__(timeout=None)
        self.application_id = application_id
        self.target_tier = target_tier
    
    @discord.ui.button(label="✅ ОДОБРИТЬ", style=discord.ButtonStyle.success, row=0)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Одобрить заявку"""
        # Делаем кнопки неактивными
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        
        await self.process_approve(interaction)
    
    @discord.ui.button(label="❌ ОТКЛОНИТЬ", style=discord.ButtonStyle.danger, row=0)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Отклонить заявку"""
        await interaction.response.send_modal(TierRejectReasonModal(self.application_id))
    
    async def process_approve(self, interaction: discord.Interaction):
        """Обработка одобрения заявки"""
        await interaction.response.defer(ephemeral=True)
        
        # Получаем заявку
        app = tier_manager.get_application(self.application_id)
        if not app:
            await interaction.followup.send("❌ Заявка не найдена", ephemeral=True)
            return
        
        # Одобряем заявку
        success = tier_manager.approve_application(
            self.application_id, 
            str(interaction.user.id),
            self.target_tier
        )
        
        if not success:
            await interaction.followup.send("❌ Не удалось одобрить заявку", ephemeral=True)
            return
        
        # Выдаём роль
        guild = interaction.guild
        member = guild.get_member(int(app['user_id']))
        
        if member:
            # Убираем предыдущие роли тиров
            tier1_role_id = CONFIG.get('tier1_role')
            tier2_role_id = CONFIG.get('tier2_role')
            tier3_role_id = CONFIG.get('tier3_role')
            
            old_roles = [tier3_role_id, tier2_role_id, tier1_role_id]
            for role_id in old_roles:
                if role_id:
                    old_role = guild.get_role(int(role_id))
                    if old_role and old_role in member.roles:
                        await member.remove_roles(old_role)
            
            # Выдаём новую роль
            new_role_id = None
            if self.target_tier == "tier3":
                new_role_id = CONFIG.get('tier3_role')
            elif self.target_tier == "tier2":
                new_role_id = CONFIG.get('tier2_role')
            elif self.target_tier == "tier1":
                new_role_id = CONFIG.get('tier1_role')
            
            if new_role_id:
                new_role = guild.get_role(int(new_role_id))
                if new_role:
                    await member.add_roles(new_role)
                    await interaction.followup.send(f"✅ Заявка одобрена! Выдана роль {new_role.mention}", ephemeral=True)
                else:
                    await interaction.followup.send(f"✅ Заявка одобрена, но роль не найдена", ephemeral=True)
        
        # Логируем в канал логов
        log_channel_id = CONFIG.get('tier_log_channel')
        if log_channel_id:
            log_channel = interaction.client.get_channel(int(log_channel_id))
            if log_channel:
                embed = discord.Embed(
                    title="✅ ЗАЯВКА ОДОБРЕНА",
                    description=f"Заявка на **{self.target_tier.upper()}** от <@{app['user_id']}> одобрена",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                embed.add_field(name="👤 Модератор", value=interaction.user.mention)
                await log_channel.send(embed=embed)
        
        # Обновляем сообщение
        embed = interaction.message.embeds[0]
        embed.color = 0x00ff00
        embed.add_field(name="✅ Статус", value=f"Одобрена модератором {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=self)


class TierRejectReasonModal(discord.ui.Modal, title="❌ ПРИЧИНА ОТКАЗА"):
    """Модалка для ввода причины отказа"""
    
    reason = discord.ui.TextInput(
        label="Причина отказа",
        placeholder="Опишите причину отказа",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    
    def __init__(self, application_id: int):
        super().__init__()
        self.application_id = application_id
    
    async def on_submit(self, interaction: discord.Interaction):
        from tier.manager import tier_manager
        
        await interaction.response.defer(ephemeral=True)
        
        success = tier_manager.reject_application(
            self.application_id, 
            str(interaction.user.id), 
            self.reason.value
        )
        
        if not success:
            await interaction.followup.send("❌ Не удалось отклонить заявку", ephemeral=True)
            return
        
        # Получаем заявку
        app = tier_manager.get_application(self.application_id)
        
        if app:
            # Отправляем ЛС пользователю
            try:
                user = await interaction.client.fetch_user(int(app['user_id']))
                if user:
                    embed = discord.Embed(
                        title="❌ ЗАЯВКА ОТКЛОНЕНА",
                        description=f"Ваша заявка на **{app['target_tier'].upper()}** отклонена.\n\n**Причина:** {self.reason.value}",
                        color=0xff0000
                    )
                    await user.send(embed=embed)
            except:
                pass
        
        # Логируем
        log_channel_id = CONFIG.get('tier_log_channel')
        if log_channel_id:
            log_channel = interaction.client.get_channel(int(log_channel_id))
            if log_channel:
                embed = discord.Embed(
                    title="❌ ЗАЯВКА ОТКЛОНЕНА",
                    description=f"Заявка на **{app['target_tier'].upper()}** от <@{app['user_id']}> отклонена",
                    color=0xff0000,
                    timestamp=datetime.now()
                )
                embed.add_field(name="👤 Модератор", value=interaction.user.mention)
                embed.add_field(name="📝 Причина", value=self.reason.value)
                await log_channel.send(embed=embed)
        
        # Обновляем сообщение
        message = interaction.message
        embed = message.embeds[0]
        embed.color = 0xff0000
        embed.add_field(name="❌ Статус", value=f"Отклонена модератором {interaction.user.mention}", inline=False)
        embed.add_field(name="📝 Причина", value=self.reason.value, inline=False)
        
        # Деактивируем кнопки
        for child in message.components[0].children:
            child.disabled = True
        
        await message.edit(embed=embed, view=None)
        await interaction.followup.send("❌ Заявка отклонена", ephemeral=True)