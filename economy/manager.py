"""Менеджер экономической системы"""
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG


class EconomyManager:
    def __init__(self):
        self.bot = None
        self._load_settings()
        self._balance_cache = {}
        self._voice_tracker = {}
    
    def set_bot(self, bot):
        self.bot = bot
    
    def _load_settings(self):
        """Загрузка настроек из БД"""
        self.settings = {
            'voice_points_per_minute': int(db.get_setting('eco_voice_points') or 1),
            'voice_max_per_day': int(db.get_setting('eco_voice_max_per_day') or 100),
            'capt_main_points': int(db.get_setting('eco_capt_main_points') or 50),
            'capt_reserve_points': int(db.get_setting('eco_capt_reserve_points') or 25),
            'mcl_main_points': int(db.get_setting('eco_mcl_main_points') or 75),
            'mcl_reserve_points': int(db.get_setting('eco_mcl_reserve_points') or 35),
            'event_points': int(db.get_setting('eco_event_points') or 30),
            'application_points': int(db.get_setting('eco_application_points') or 100),
            'tier3_points': int(db.get_setting('eco_tier3_points') or 50),
            'tier2_points': int(db.get_setting('eco_tier2_points') or 100),
            'tier1_points': int(db.get_setting('eco_tier1_points') or 200),
            'daily_bonus_base': int(db.get_setting('eco_daily_bonus') or 25),
            'daily_bonus_increment': int(db.get_setting('eco_daily_increment') or 5),
            'daily_bonus_limit': int(db.get_setting('eco_daily_limit') or 30),
        }
    
    # ==================== БАЛАНСЫ ====================
    
    async def get_balance(self, user_id: int) -> int:
        user_id_str = str(user_id)
        if user_id_str in self._balance_cache:
            return self._balance_cache[user_id_str]
        
        balance = db.get_user_balance(user_id_str)
        if balance is None:
            balance = 0
            db.init_user_balance(user_id_str)
        
        self._balance_cache[user_id_str] = balance
        return balance
    
    async def add_points(self, user_id: int, amount: int, reason: str, awarded_by: str = None) -> bool:
        if amount <= 0:
            return False
        
        user_id_str = str(user_id)
        new_balance = db.add_user_balance(user_id_str, amount, reason, awarded_by)
        
        if new_balance is not None:
            self._balance_cache[user_id_str] = new_balance
            return True
        return False
    
    async def remove_points(self, user_id: int, amount: int, reason: str, removed_by: str = None) -> bool:
        if amount <= 0:
            return False
        
        current = await self.get_balance(user_id)
        if current < amount:
            return False
        
        user_id_str = str(user_id)
        new_balance = db.remove_user_balance(user_id_str, amount, reason, removed_by)
        
        if new_balance is not None:
            self._balance_cache[user_id_str] = new_balance
            return True
        return False
    
    # ==================== ЕЖЕДНЕВНЫЙ БОНУС ====================
    
    async def claim_daily_bonus(self, user_id: int) -> tuple:
        user_id_str = str(user_id)
        last_claim = db.get_last_daily_claim(user_id_str)
        
        now = datetime.now()
        today = now.date()
        
        if last_claim:
            last_date = datetime.fromisoformat(last_claim).date()
            if last_date == today:
                return False, "❌ Вы уже получили бонус сегодня", 0
            
            if (today - last_date).days == 1:
                streak = db.get_daily_streak(user_id_str) + 1
                if streak > self.settings['daily_bonus_limit']:
                    streak = self.settings['daily_bonus_limit']
                bonus = self.settings['daily_bonus_base'] + (streak // 2) * self.settings['daily_bonus_increment']
            else:
                streak = 1
                bonus = self.settings['daily_bonus_base']
        else:
            streak = 1
            bonus = self.settings['daily_bonus_base']
        
        await self.add_points(user_id, bonus, f"Ежедневный бонус (день {streak})")
        db.update_daily_claim(user_id_str, streak)
        
        return True, f"✅ +{bonus} баллов! День {streak}", bonus
    
    # ==================== НАЧИСЛЕНИЯ ЗА ДЕЙСТВИЯ ====================
    
    async def award_capt(self, user_id: int, is_main: bool):
        points = self.settings['capt_main_points'] if is_main else self.settings['capt_reserve_points']
        if points > 0:
            await self.add_points(user_id, points, f"Участие в CAPT ({'основной' if is_main else 'резерв'})")
    
    async def award_mcl(self, user_id: int, is_main: bool):
        points = self.settings['mcl_main_points'] if is_main else self.settings['mcl_reserve_points']
        if points > 0:
            await self.add_points(user_id, points, f"Участие в MCL/ВЗМ ({'основной' if is_main else 'резерв'})")
    
    async def award_event(self, user_id: int):
        points = self.settings['event_points']
        if points > 0:
            await self.add_points(user_id, points, "Взятие мероприятия")
    
    async def award_application(self, user_id: int):
        points = self.settings['application_points']
        if points > 0:
            await self.add_points(user_id, points, "Принятие заявки")
    
    async def award_tier(self, user_id: int, tier: str):
        points = self.settings.get(f'{tier}_points', 0)
        if points > 0:
            tier_names = {'tier3': 'Tier 3 🟤', 'tier2': 'Tier 2 ⚪', 'tier1': 'Tier 1 🔴'}
            await self.add_points(user_id, points, f"Повышение до {tier_names.get(tier, tier)}")
    
    # ==================== МАГАЗИН ====================
    
    def get_shop_items(self):
        return db.get_shop_items(active_only=True)
    
    def get_shop_item(self, item_id: int):
        return db.get_shop_item(item_id)
    
    async def add_shop_item(self, name: str, description: str, price: int, emoji: str, limited_quantity: int = 0, created_by: str = None) -> tuple:
        if price < 0:
            return False, "❌ Цена не может быть отрицательной"
        item_id = db.add_shop_item(name, description, price, emoji, limited_quantity, created_by)
        if item_id:
            return True, f"✅ Товар добавлен! ID: {item_id}"
        return False, "❌ Ошибка при добавлении"
    
    async def remove_shop_item(self, item_id: int) -> tuple:
        if db.remove_shop_item(item_id):
            return True, f"✅ Товар ID {item_id} удалён"
        return False, f"❌ Товар ID {item_id} не найден"
    
    async def buy_item(self, user_id: int, item_id: int) -> tuple:
        item = self.get_shop_item(item_id)
        if not item or not item.get('is_active'):
            return False, "❌ Товар не найден"
        
        if item['limited_quantity'] > 0 and item['sold_count'] >= item['limited_quantity']:
            return False, "❌ Товар закончился"
        
        balance = await self.get_balance(user_id)
        if balance < item['price']:
            return False, f"❌ Недостаточно баллов! Нужно: {item['price']}"
        
        if db.purchase_item(str(user_id), item_id, item['price']):
            await self.remove_points(user_id, item['price'], f"Покупка: {item['name']}")
            
            # ========== ЛОГ ПОКУПКИ В ОТДЕЛЬНЫЙ КАНАЛ ==========
            logs_channel_id = CONFIG.get("economy_logs_channel")
            if logs_channel_id and logs_channel_id != "null" and self.bot:
                channel = self.bot.get_channel(int(logs_channel_id))
                if channel:
                    embed = discord.Embed(
                        title="🛒 НОВАЯ ПОКУПКА",
                        color=0x00ff00,
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="👤 Покупатель", value=f"<@{user_id}>", inline=True)
                    embed.add_field(name="🛍️ Товар", value=f"{item['emoji']} **{item['name']}**", inline=True)
                    embed.add_field(name="💰 Цена", value=f"{item['price']} баллов", inline=True)
                    embed.add_field(name="📦 Осталось", value=f"{item['limited_quantity'] - (item['sold_count'] + 1)}" if item['limited_quantity'] > 0 else "∞", inline=True)
                    embed.set_footer(text=f"ID товара: {item_id}")
                    await channel.send(embed=embed)
            
            return True, f"✅ Вы купили {item['emoji']} **{item['name']}** за {item['price']} баллов!"
        return False, "❌ Ошибка при покупке"
    
    def get_user_purchases(self, user_id: int, limit: int = 10):
        return db.get_user_purchases(str(user_id), limit)
    
    def get_top_users(self, limit: int = 10):
        return db.get_top_balance_users(limit)

    # ==================== ГОЛОСОВОЙ ОНЛАЙН ====================

    async def process_voice_update(self, member: discord.Member, before, after):
        """Обработка изменения голосового статуса"""
        user_id_str = str(member.id)
        
        # Пользователь зашёл в голосовой канал
        if after.channel and (not before.channel or before.channel != after.channel):
            self._voice_tracker[user_id_str] = {
                'joined_at': datetime.now(),
                'channel_id': str(after.channel.id)
            }
            print(f"🎙️ [VOICE] {member.name} зашёл в войс, начат отсчёт")
        
        # Пользователь вышел из голосового канала
        elif before.channel and not after.channel:
            if user_id_str in self._voice_tracker:
                joined = self._voice_tracker[user_id_str]['joined_at']
                now = datetime.now()
                minutes = int((now - joined).total_seconds() / 60)
                
                if minutes > 0:
                    # Проверка лимита за день
                    today_earned = db.get_daily_voice_earned(user_id_str)
                    max_per_day = self.settings['voice_max_per_day']
                    
                    points_to_add = minutes * self.settings['voice_points_per_minute']
                    if today_earned + points_to_add > max_per_day:
                        points_to_add = max(0, max_per_day - today_earned)
                        print(f"⚠️ [VOICE] {member.name} достиг лимита {max_per_day} баллов в день")
                    
                    if points_to_add > 0:
                        await self.add_points(member.id, points_to_add, f"{minutes} мин в голосовом канале")
                        db.update_daily_voice_earned(user_id_str, points_to_add)
                        print(f"💰 [VOICE] {member.name} +{points_to_add} баллов за {minutes} мин")
                    else:
                        print(f"⚠️ [VOICE] {member.name} лимит исчерпан, баллы не начислены")
                
                del self._voice_tracker[user_id_str]
                print(f"🎙️ [VOICE] {member.name} вышел из войса, начислено {points_to_add if minutes > 0 else 0} баллов")


economy_manager = EconomyManager()