"""Кнопки для системы дней рождения"""
import discord
from datetime import datetime
from core.database import db
from birthday.manager import birthday_manager
from birthday.base import PermanentView


class BirthdayModal(discord.ui.Modal, title="🎂 УКАЗАТЬ ДЕНЬ РОЖДЕНИЯ"):
    date = discord.ui.TextInput(
        label="Дата рождения",
        placeholder="ДД.ММ (например 15.05)",
        max_length=5,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        success, msg = birthday_manager.set_birthday(
            str(interaction.user.id),
            interaction.user.display_name,
            self.date.value
        )
        await interaction.response.send_message(msg, ephemeral=True)
        
        if success:
            channel_id = db.get_setting('birthday_channel')
            if channel_id:
                from birthday.views import update_birthday_embed
                await update_birthday_embed(interaction.client, channel_id)


class RemoveBirthdayModal(discord.ui.Modal, title="🗑️ УДАЛИТЬ ДЕНЬ РОЖДЕНИЯ"):
    confirm = discord.ui.TextInput(
        label="Введите 'УДАЛИТЬ' для подтверждения",
        placeholder="УДАЛИТЬ",
        max_length=10,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value != "УДАЛИТЬ":
            await interaction.response.send_message("❌ Неверное подтверждение", ephemeral=True)
            return
        
        success, msg = birthday_manager.remove_birthday(str(interaction.user.id))
        await interaction.response.send_message(msg, ephemeral=True)
        
        if success:
            channel_id = db.get_setting('birthday_channel')
            if channel_id:
                from birthday.views import update_birthday_embed
                await update_birthday_embed(interaction.client, channel_id)


class BirthdayPublicView(PermanentView):
    """Постоянные кнопки в публичном канале"""

    def __init__(self):
        super().__init__()

    @discord.ui.button(
        label="🎂 УКАЗАТЬ ДЕНЬ РОЖДЕНИЯ",
        style=discord.ButtonStyle.success,
        emoji="🎂",
        custom_id="birthday_set"
    )
    async def set_birthday(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BirthdayModal())

    @discord.ui.button(
        label="🗑️ УДАЛИТЬ ДЕНЬ РОЖДЕНИЯ",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
        custom_id="birthday_remove"
    )
    async def remove_birthday(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveBirthdayModal())

    @discord.ui.button(
        label="📅 ВСЕ ДНИ РОЖДЕНИЯ",
        style=discord.ButtonStyle.secondary,
        emoji="📅",
        custom_id="birthday_list"
    )
    async def list_birthdays(self, interaction: discord.Interaction, button: discord.ui.Button):
        birthdays = birthday_manager.get_all_birthdays()
        
        if not birthdays:
            await interaction.response.send_message("📭 Никто ещё не указал день рождения", ephemeral=True)
            return
        
        months = {
            '01': 'Январь', '02': 'Февраль', '03': 'Март', '04': 'Апрель',
            '05': 'Май', '06': 'Июнь', '07': 'Июль', '08': 'Август',
            '09': 'Сентябрь', '10': 'Октябрь', '11': 'Ноябрь', '12': 'Декабрь'
        }
        
        grouped = {month: [] for month in months}
        for bd in birthdays:
            month = bd['birthday_date'][3:5]
            grouped[month].append(bd)
        
        embed = discord.Embed(
            title="📅 **ВСЕ ДНИ РОЖДЕНИЯ**",
            color=0xffa500,
            timestamp=datetime.now()
        )
        
        for month, name in months.items():
            bds = grouped.get(month, [])
            if bds:
                text = ""
                for bd in bds:
                    text += f"• <@{bd['user_id']}> — {bd['birthday_date']}\n"
                embed.add_field(name=f"📆 {name}", value=text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def update_birthday_embed(bot, channel_id: str):
    """Обновить embed с именинниками текущего месяца"""
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    
    now = datetime.now()
    current_month = now.strftime("%m")
    
    birthdays = birthday_manager.get_birthdays_by_month(current_month)
    birthdays.sort(key=lambda x: int(x['birthday_date'][:2]))
    
    months = {
        '01': 'Январе', '02': 'Феврале', '03': 'Марте', '04': 'Апреле',
        '05': 'Мае', '06': 'Июне', '07': 'Июле', '08': 'Августе',
        '09': 'Сентябре', '10': 'Октябре', '11': 'Ноябре', '12': 'Декабре'
    }
    
    embed = discord.Embed(
        title="🎂 **ДНИ РОЖДЕНИЯ**",
        description=f"Именинники в **{months.get(current_month, 'этом месяце')}**:",
        color=0xffa500,
        timestamp=now
    )
    
    if birthdays:
        text = ""
        for bd in birthdays:
            day = bd['birthday_date'][:2]
            if bd['birthday_date'] == now.strftime("%d.%m"):
                text += f"🎉 **<@{bd['user_id']}> — {day} числа (СЕГОДНЯ!)** 🎉\n"
            else:
                text += f"• <@{bd['user_id']}> — {day} числа\n"
        embed.description += f"\n\n{text}"
    else:
        embed.description += "\n\n✨ В этом месяце пока нет именинников"
    
    embed.set_footer(text="Нажмите кнопку, чтобы указать свой день рождения")
    
    # Ищем существующее сообщение бота
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and msg.embeds:
            if msg.embeds and "ДНИ РОЖДЕНИЯ" in msg.embeds[0].title:
                await msg.edit(embed=embed)
                return
    
    # Если не нашли — создаём новое
    await channel.send(embed=embed, view=BirthdayPublicView())