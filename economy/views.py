"""КНОПКИ для магазина (никаких команд!)"""
import discord
from datetime import datetime
from economy.base import PermanentView, ConfirmView
from economy.manager import economy_manager
from core.database import db
from core.config import CONFIG
from core.utils import is_admin


class EconomyPanelView(PermanentView):
    """Главная панель магазина"""
    
    bot = None
    
    def __init__(self):
        super().__init__()
    
    async def get_shop_embed(self) -> discord.Embed:
        """Создать embed с актуальным списком товаров"""
        items = economy_manager.get_shop_items()
        
        embed = discord.Embed(
            title="🛒 МАГАЗИН БАЛЛОВ",
            color=0xffa500
        )
        
        if not items:
            embed.description = "*В магазине пока нет товаров*\nДобавьте товары через админ-панель."
        else:
            for item in items:
                stock = f" (осталось: {item['limited_quantity'] - item['sold_count']})" if item['limited_quantity'] > 0 else ""
                embed.add_field(
                    name=f"{item['emoji']} **{item['name']}** {stock}",
                    value=f"💰 Цена: `{item['price']}` баллов\n📝 {item['description'][:60]}\n`ID: {item['id']}`",
                    inline=False
                )
        
        embed.set_footer(text="Используйте кнопку «Купить» и введите ID товара")
        return embed
    
    @discord.ui.button(label="💰 Купить товар", style=discord.ButtonStyle.success, row=0, custom_id="eco_buy")
    async def buy_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Открыть меню покупки"""
        await interaction.response.send_modal(BuyItemModal(interaction.user.id))
    
    @discord.ui.button(label="💰 Мой баланс", style=discord.ButtonStyle.secondary, row=0, custom_id="eco_balance")
    async def show_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать баланс"""
        balance = await economy_manager.get_balance(interaction.user.id)
        total_earned = db.get_user_total_earned(str(interaction.user.id))
        total_spent = db.get_user_total_spent(str(interaction.user.id))
        
        embed = discord.Embed(title="💰 ВАШ БАЛАНС", color=0x00ff00)
        embed.add_field(name="Доступно", value=f"**{balance}**", inline=True)
        embed.add_field(name="Заработано", value=f"**{total_earned}**", inline=True)
        embed.add_field(name="Потрачено", value=f"**{total_spent}**", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🎁 Ежедневный бонус", style=discord.ButtonStyle.primary, row=1, custom_id="eco_daily")
    async def claim_daily(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Получить ежедневный бонус"""
        success, msg, points = await economy_manager.claim_daily_bonus(interaction.user.id)
        
        if success:
            embed = discord.Embed(title="🎁 ЕЖЕДНЕВНЫЙ БОНУС", color=0x00ff00)
            embed.description = msg
            embed.add_field(name="Баланс", value=f"**{await economy_manager.get_balance(interaction.user.id)}**")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(label="📜 История покупок", style=discord.ButtonStyle.secondary, row=1, custom_id="eco_history")
    async def purchase_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать историю покупок"""
        purchases = economy_manager.get_user_purchases(interaction.user.id, 10)
        
        if not purchases:
            embed = discord.Embed(title="📜 ИСТОРИЯ", description="У вас пока нет покупок", color=0x7289da)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(title="📜 ПОСЛЕДНИЕ ПОКУПКИ", color=0x7289da)
        for p in purchases:
            embed.add_field(name=f"{p['item_emoji']} {p['item_name']}", value=f"💰 {p['price']} | {p['purchased_at'][:16]}", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🏆 Топ по баллам", style=discord.ButtonStyle.secondary, row=2, custom_id="eco_top")
    async def show_top(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать топ пользователей"""
        top = economy_manager.get_top_users(10)
        
        embed = discord.Embed(title="🏆 ТОП ПО БАЛЛАМ", color=0xffd700)
        
        if top:
            desc = ""
            for i, (user_id, balance, _) in enumerate(top, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                desc += f"{medal} <@{user_id}> — **{balance}**\n"
            embed.description = desc
        else:
            embed.description = "Нет данных"
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def update_shop_embed(self, channel):
        """Обновить embed магазина (вызывается при изменении товаров)"""
        async for msg in channel.history(limit=10):
            if msg.author == self.bot and msg.embeds:
                embed = await self.get_shop_embed()
                await msg.edit(embed=embed)
                return


class AdminEconomyView(PermanentView):
    """Панель управления экономикой (только для админов БД)"""
    
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(label="➕ Выдать баллы", style=discord.ButtonStyle.success, row=0, custom_id="eco_admin_give")
    async def give_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(AdminGiveModal())
    
    @discord.ui.button(label="📤 Снять баллы", style=discord.ButtonStyle.danger, row=0, custom_id="eco_admin_remove")
    async def remove_points(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(AdminRemoveModal())
    
    @discord.ui.button(label="🛒 Управление товарами", style=discord.ButtonStyle.primary, row=1, custom_id="eco_admin_shop")
    async def manage_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        embed = discord.Embed(title="🛒 УПРАВЛЕНИЕ МАГАЗИНОМ", color=0x7289da)
        items = economy_manager.get_shop_items()
        
        if items:
            for item in items:
                embed.add_field(name=f"{item['emoji']} {item['name']}", value=f"ID: `{item['id']}` | Цена: `{item['price']}` | Продано: {item['sold_count']}/{item['limited_quantity'] if item['limited_quantity'] > 0 else '∞'}", inline=False)
        else:
            embed.description = "Нет товаров"
        
        view = ShopManageView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📊 Текущие настройки", style=discord.ButtonStyle.secondary, row=1, custom_id="eco_admin_settings")
    async def show_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показать текущие настройки начислений"""
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        settings = economy_manager.settings
        
        embed = discord.Embed(title="📊 ТЕКУЩИЕ НАСТРОЙКИ ЭКОНОМИКИ", color=0x00ff00)
        embed.add_field(name="🎙️ Голосовой канал (балл/мин)", value=f"`{settings['voice_points_per_minute']}`", inline=True)
        embed.add_field(name="📊 Максимум баллов в день за войс", value=f"`{settings['voice_max_per_day']}`", inline=True)
        embed.add_field(name="🎯 CAPT (основной/резерв)", value=f"`{settings['capt_main_points']}` / `{settings['capt_reserve_points']}`", inline=True)
        embed.add_field(name="🎯 MCL/ВЗМ (основной/резерв)", value=f"`{settings['mcl_main_points']}` / `{settings['mcl_reserve_points']}`", inline=True)
        embed.add_field(name="📅 Взятие МП", value=f"`{settings['event_points']}`", inline=True)
        embed.add_field(name="📝 Принятие заявки", value=f"`{settings['application_points']}`", inline=True)
        embed.add_field(name="🌟 Повышение Tier", value=f"T3: `{settings['tier3_points']}` | T2: `{settings['tier2_points']}` | T1: `{settings['tier1_points']}`", inline=False)
        embed.add_field(name="📅 Ежедневный бонус", value=f"База: `{settings['daily_bonus_base']}` | +`{settings['daily_bonus_increment']}`/2дня | Лимит: `{settings['daily_bonus_limit']}`", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📊 Баланс пользователя", style=discord.ButtonStyle.secondary, row=2, custom_id="eco_admin_balance")
    async def check_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        await interaction.response.send_modal(AdminBalanceModal())
    
    @discord.ui.button(label="📋 Логи операций", style=discord.ButtonStyle.secondary, row=2, custom_id="eco_admin_logs")
    async def show_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await is_admin(str(interaction.user.id)):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        
        logs = db.get_recent_economy_transactions(20)
        embed = discord.Embed(title="📋 ПОСЛЕДНИЕ ОПЕРАЦИИ", color=0x7289da)
        
        if logs:
            desc = ""
            for log in logs:
                emoji = "➕" if log['action'] == 'earn' else "➖"
                desc += f"{emoji} <@{log['user_id']}> | {log['amount']} | {log['reason'][:30]}\n"
            embed.description = desc
        else:
            embed.description = "Нет операций"
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ShopManageView(PermanentView):
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(label="➕ Добавить товар", style=discord.ButtonStyle.success, row=0, custom_id="eco_shop_add")
    async def add_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddItemModal())
    
    @discord.ui.button(label="🗑️ Удалить товар", style=discord.ButtonStyle.danger, row=0, custom_id="eco_shop_remove")
    async def remove_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveItemModal())
    
    @discord.ui.button(label="◀ Назад", style=discord.ButtonStyle.secondary, row=1, custom_id="eco_shop_back")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="⚙️ АДМИН-ПАНЕЛЬ ЭКОНОМИКИ", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=AdminEconomyView())


class BuyItemModal(discord.ui.Modal, title="🛒 ПОКУПКА"):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.item_id_input = discord.ui.TextInput(label="ID товара", placeholder="Введите ID из списка", required=True)
        self.add_item(self.item_id_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Чужая покупка", ephemeral=True)
            return
        
        try:
            item_id = int(self.item_id_input.value)
            item = economy_manager.get_shop_item(item_id)
            
            if not item:
                await interaction.response.send_message("❌ Товар не найден", ephemeral=True)
                return
            
            if item['limited_quantity'] > 0 and item['sold_count'] >= item['limited_quantity']:
                await interaction.response.send_message("❌ Товар закончился", ephemeral=True)
                return
            
            balance = await economy_manager.get_balance(self.user_id)
            if balance < item['price']:
                await interaction.response.send_message(f"❌ Не хватает! Нужно: {item['price']}", ephemeral=True)
                return
            
            embed = discord.Embed(title="🛒 ПОДТВЕРЖДЕНИЕ", color=0xffa500)
            embed.add_field(name="Товар", value=f"{item['emoji']} **{item['name']}**")
            embed.add_field(name="Цена", value=f"💰 {item['price']}")
            embed.add_field(name="Баланс после", value=f"**{balance - item['price']}**")
            
            view = ConfirmView(self.user_id, item_id, item['price'])
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            await view.wait()
            
            if view.confirmed:
                success, msg = await economy_manager.buy_item(self.user_id, item_id)
                await interaction.edit_original_response(content=msg, embed=None, view=None)
            else:
                await interaction.edit_original_response(content="❌ Отменено", embed=None, view=None)
        except ValueError:
            await interaction.response.send_message("❌ Введите число", ephemeral=True)


class AddItemModal(discord.ui.Modal, title="➕ ДОБАВИТЬ ТОВАР"):
    name = discord.ui.TextInput(label="Название", max_length=100, required=True)
    price = discord.ui.TextInput(label="Цена", required=True)
    emoji = discord.ui.TextInput(label="Эмодзи", max_length=10, required=False, default="🛒")
    desc = discord.ui.TextInput(label="Описание", required=False, max_length=200, style=discord.TextStyle.paragraph)
    limit = discord.ui.TextInput(label="Лимит (0=безлимит)", required=False, default="0")
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.price.value)
            if price <= 0:
                await interaction.response.send_message("❌ Цена > 0", ephemeral=True)
                return
            limit = int(self.limit.value) if self.limit.value else 0
            if limit < 0:
                await interaction.response.send_message("❌ Лимит >= 0", ephemeral=True)
                return
            
            success, msg = await economy_manager.add_shop_item(
                self.name.value, self.desc.value or "Нет описания", price,
                self.emoji.value or "🛒", limit, str(interaction.user.id)
            )
            await interaction.response.send_message(msg, ephemeral=True)
            
            if success:
                await self.update_shop_embed(interaction)
                
        except ValueError:
            await interaction.response.send_message("❌ Числа", ephemeral=True)
    
    async def update_shop_embed(self, interaction: discord.Interaction):
        """Обновить embed магазина в публичном канале"""
        channel_id = CONFIG.get("economy_channel")
        if channel_id and channel_id != "null":
            channel = interaction.client.get_channel(int(channel_id))
            if channel:
                async for msg in channel.history(limit=10):
                    if msg.author == interaction.client.user and msg.embeds:
                        view = EconomyPanelView()
                        embed = await view.get_shop_embed()
                        await msg.edit(embed=embed)
                        break


class RemoveItemModal(discord.ui.Modal, title="🗑️ УДАЛИТЬ ТОВАР"):
    item_id = discord.ui.TextInput(label="ID товара", required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            item_id = int(self.item_id.value)
            success, msg = await economy_manager.remove_shop_item(item_id)
            await interaction.response.send_message(msg, ephemeral=True)
            
            if success:
                await self.update_shop_embed(interaction)
                
        except ValueError:
            await interaction.response.send_message("❌ Число", ephemeral=True)
    
    async def update_shop_embed(self, interaction: discord.Interaction):
        """Обновить embed магазина в публичном канале"""
        channel_id = CONFIG.get("economy_channel")
        if channel_id and channel_id != "null":
            channel = interaction.client.get_channel(int(channel_id))
            if channel:
                async for msg in channel.history(limit=10):
                    if msg.author == interaction.client.user and msg.embeds:
                        view = EconomyPanelView()
                        embed = await view.get_shop_embed()
                        await msg.edit(embed=embed)
                        break


class AdminGiveModal(discord.ui.Modal, title="➕ ВЫДАТЬ БАЛЛЫ"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)
    amount = discord.ui.TextInput(label="Количество", placeholder="100", required=True)
    reason = discord.ui.TextInput(label="Причина", required=False, max_length=200)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value)
            amount = int(self.amount.value)
            if amount <= 0:
                await interaction.response.send_message("❌ Положительное число", ephemeral=True)
                return
            
            if await economy_manager.add_points(uid, amount, self.reason.value or "Выдача админом", str(interaction.user.id)):
                await interaction.response.send_message(f"✅ +{amount} <@{uid}>", ephemeral=True)
                try:
                    user = await interaction.client.fetch_user(uid)
                    await user.send(f"🎁 +{amount} баллов!\nПричина: {self.reason.value or 'Выдача админом'}")
                except:
                    pass
            else:
                await interaction.response.send_message("❌ Ошибка", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Ошибка", ephemeral=True)


class AdminRemoveModal(discord.ui.Modal, title="📤 СНЯТЬ БАЛЛЫ"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)
    amount = discord.ui.TextInput(label="Количество", placeholder="100", required=True)
    reason = discord.ui.TextInput(label="Причина", required=False, max_length=200)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value)
            amount = int(self.amount.value)
            if amount <= 0:
                await interaction.response.send_message("❌ Положительное число", ephemeral=True)
                return
            
            if await economy_manager.remove_points(uid, amount, self.reason.value or "Снятие админом", str(interaction.user.id)):
                await interaction.response.send_message(f"✅ -{amount} <@{uid}>", ephemeral=True)
                try:
                    user = await interaction.client.fetch_user(uid)
                    await user.send(f"📤 -{amount} баллов!\nПричина: {self.reason.value or 'Снятие админом'}")
                except:
                    pass
            else:
                await interaction.response.send_message("❌ Недостаточно баллов", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Ошибка", ephemeral=True)


class AdminBalanceModal(discord.ui.Modal, title="📊 ПРОВЕРКА БАЛАНСА"):
    user_id = discord.ui.TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value)
            balance = await economy_manager.get_balance(uid)
            earned = db.get_user_total_earned(str(uid))
            spent = db.get_user_total_spent(str(uid))
            
            embed = discord.Embed(title="💰 БАЛАНС", color=0x00ff00)
            embed.add_field(name="Пользователь", value=f"<@{uid}>")
            embed.add_field(name="Доступно", value=f"**{balance}**")
            embed.add_field(name="Заработано", value=f"**{earned}**")
            embed.add_field(name="Потрачено", value=f"**{spent}**")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Ошибка", ephemeral=True)