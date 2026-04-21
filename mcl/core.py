"""DUAL MCL Core - 4 цвета (основные + дополнительные)"""
import aiohttp
import asyncio
import time
import discord
from datetime import datetime
from core.database import db
from core.config import CONFIG

active_mcl_tasks = {}

class CancelView(discord.ui.View):
    """Кнопка отмены отправки (без таймаута)"""
    def __init__(self, task_id: int, user_id: str):
        super().__init__(timeout=None)
        self.task_id = task_id
        self.user_id = user_id
    
    @discord.ui.button(label="❌ ОТМЕНИТЬ", style=discord.ButtonStyle.danger, emoji="🛑")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Только запустивший может отменить", ephemeral=True)
            return
        
        if self.task_id in active_mcl_tasks:
            active_mcl_tasks[self.task_id]['cancelled'] = True
            button.disabled = True
            await interaction.response.edit_message(
                content="🛑 Отправка остановлена",
                embed=None,
                view=None
            )
        else:
            await interaction.response.send_message("❌ Задача уже завершена", ephemeral=True)

class DualMCLCore:
    __slots__ = (
        'sessions', 'session_locks', 'headers_cache', 'last_tokens',
        'payload_cache', 'last_messages', 'last_channel', 
        'stats', 'token_colors', 'token_extra_colors',
        'current_sender', 'sending_lock', 'sender_name', 'sending_active',
        '_connectors_initialized', '_connectors'
    )
    
    def __init__(self):
        self._connectors_initialized = False
        self._connectors = {1: None, 2: None}
        
        self.sessions = {1: None, 2: None}
        self.session_locks = {1: asyncio.Lock(), 2: asyncio.Lock()}
        
        # Блокировка отправки
        self.sending_lock = asyncio.Lock()
        self.current_sender = None
        self.sender_name = None
        self.sending_active = False
        
        self.headers_cache = {1: None, 2: None}
        self.last_tokens = {1: None, 2: None}
        self.payload_cache = {1: None, 2: None}
        self.last_messages = {1: None, 2: None}
        self.last_channel = None
        
        # Статистика для 4 цветов
        self.stats = {
            1: {'main': False, 'extra': False, 'attempts': 0, 'time': 0},
            2: {'main': False, 'extra': False, 'attempts': 0, 'time': 0}
        }
        
        # Цвета (основные и дополнительные)
        self.token_colors = {1: 'Pink', 2: 'Orange'}
        self.token_extra_colors = {1: 'Purple', 2: 'Gold'}  # Дополнительные цвета
        
        print("🎨 DUAL MCL Core (4 COLORS) инициализирован")
    
    async def _ensure_connectors(self):
        if not self._connectors_initialized:
            self._connectors = {
                1: aiohttp.TCPConnector(limit=0, ttl_dns_cache=3600, force_close=False, ssl=False),
                2: aiohttp.TCPConnector(limit=0, ttl_dns_cache=3600, force_close=False, ssl=False)
            }
            self._connectors_initialized = True
    
    async def get_session(self, token_id: int):
        await self._ensure_connectors()
        
        if self.sessions[token_id] and not self.sessions[token_id].closed:
            return self.sessions[token_id]
        
        async with self.session_locks[token_id]:
            if self.sessions[token_id] is None or self.sessions[token_id].closed:
                self.sessions[token_id] = aiohttp.ClientSession(
                    connector=self._connectors[token_id],
                    headers={'User-Agent': 'Mozilla/5.0'},
                    timeout=aiohttp.ClientTimeout(total=10)
                )
            return self.sessions[token_id]
    
    def prepare_headers(self, token_id: int):
        token = CONFIG[f'user_token_{token_id}']
        if self.headers_cache[token_id] and self.last_tokens[token_id] == token:
            return self.headers_cache[token_id]
        
        headers = {'Authorization': token, 'Content-Type': 'application/json'}
        self.headers_cache[token_id] = headers
        self.last_tokens[token_id] = token
        return headers
    
    def prepare_payload(self, token_id: int, is_extra: bool = False):
        family = CONFIG.get('family_name', 'Семья')
        if is_extra:
            msg = f"{family}\n{self.token_extra_colors[token_id]}"
        else:
            msg = f"{family}\n{self.token_colors[token_id]}"
        
        cache_key = f"{token_id}_{is_extra}"
        if (self.last_messages.get(cache_key) == msg and 
            self.last_channel == CONFIG['channel_id'] and 
            self.payload_cache.get(cache_key)):
            return self.payload_cache[cache_key]
        
        payload = {'content': msg, 'tts': False}
        self.payload_cache[cache_key] = payload
        self.last_messages[cache_key] = msg
        self.last_channel = CONFIG['channel_id']
        return payload
    
    async def _send_color(self, token_id: int, is_extra: bool, task_id: int):
        """Отправка конкретного цвета с бесконечными попытками"""
        url = f'https://discord.com/api/v9/channels/{CONFIG["channel_id"]}/messages'
        session = await self.get_session(token_id)
        headers = self.prepare_headers(token_id)
        payload = self.prepare_payload(token_id, is_extra)
        
        color_name = self.token_extra_colors[token_id] if is_extra else self.token_colors[token_id]
        attempt = 0
        start_time = time.time()
        
        while True:
            if task_id in active_mcl_tasks and active_mcl_tasks[task_id].get('cancelled', False):
                return False, attempt, time.time() - start_time, color_name
            
            attempt += 1
            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        elapsed = time.time() - start_time
                        return True, attempt, elapsed, color_name
                    
                    elif resp.status == 429:
                        data = await resp.json()
                        retry_after = float(data.get('retry_after', 1))
                        await asyncio.sleep(retry_after)
                    else:
                        await asyncio.sleep(0.1)
                        
            except Exception as e:
                await asyncio.sleep(0.1)
    
    async def send_dual(self, interaction):
        """Отправка 4 цветов с максимальной скоростью"""
        user_id = str(interaction.user.id)
        
        async with self.sending_lock:
            if self.sending_active:
                if self.current_sender:
                    await interaction.response.send_message(
                        f"❌ MCL **УЖЕ ЗАПУЩЕН** пользователем <@{self.current_sender}>\n"
                        f"👤 Отправитель: {self.sender_name}",
                        ephemeral=True
                    )
                return False
            
            self.sending_active = True
            self.current_sender = user_id
            self.sender_name = interaction.user.display_name
        
        task_id = id(asyncio.current_task())
        active_mcl_tasks[task_id] = {'cancelled': False, 'user': user_id}
        overall_start = time.time()
        
        try:
            if not CONFIG['user_token_1'] or not CONFIG['user_token_2']:
                await interaction.response.send_message("❌ Нужны 2 токена", ephemeral=True)
                return False
            
            if not CONFIG['channel_id']:
                await interaction.response.send_message("❌ Канал не настроен", ephemeral=True)
                return False
            
            # Отправляем начальное сообщение
            embed = discord.Embed(
                title="🎨 DUAL MCL - 4 ЦВЕТА",
                description=f"**Запущено:** {interaction.user.mention}\n"
                        f"**Статус:** Ожидание отправки цветов...\n"
                        f"🎨 Токен 1: {self.token_colors[1]} + {self.token_extra_colors[1]}\n"
                        f"🎨 Токен 2: {self.token_colors[2]} + {self.token_extra_colors[2]}",
                color=0xffa500
            )
            cancel_view = CancelView(task_id, user_id)
            await interaction.response.send_message(embed=embed, view=cancel_view, ephemeral=True)
            
            # Запускаем ВСЕ 4 цвета ПАРАЛЛЕЛЬНО
            tasks = [
                self._send_color(1, False, task_id),  # Токен 1 основной
                self._send_color(1, True, task_id),   # Токен 1 дополнительный
                self._send_color(2, False, task_id),  # Токен 2 основной
                self._send_color(2, True, task_id)    # Токен 2 дополнительный
            ]
            
            # Ждем все результаты
            results = await asyncio.gather(*tasks)
            
            # Распаковываем результаты
            main1_success, main1_attempts, main1_time, main1_color = results[0]
            extra1_success, extra1_attempts, extra1_time, extra1_color = results[1]
            main2_success, main2_attempts, main2_time, main2_color = results[2]
            extra2_success, extra2_attempts, extra2_time, extra2_color = results[3]
            
            total_elapsed = time.time() - overall_start
            
            # Проверяем отмену
            if task_id in active_mcl_tasks and active_mcl_tasks[task_id].get('cancelled', False):
                result_embed = discord.Embed(
                    title="🛑 ОТПРАВКА ОСТАНОВЛЕНА",
                    description=f"Пользователь {interaction.user.mention} остановил отправку",
                    color=0xff0000,
                    timestamp=datetime.now()
                )
            else:
                # Формируем результат
                result_embed = discord.Embed(
                    title="✅ DUAL MCL - ВСЕ ЦВЕТА ОТПРАВЛЕНЫ",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                
                # Токен 1
                token1_text = f"🎨 **{main1_color}** ({'✅' if main1_success else '❌'}, {main1_attempts} поп.)\n"
                token1_text += f"🎨 **{extra1_color}** ({'✅' if extra1_success else '❌'}, {extra1_attempts} поп.)"
                result_embed.add_field(
                    name=f"🤖 Токен 1",
                    value=token1_text,
                    inline=True
                )
                
                # Токен 2
                token2_text = f"🎨 **{main2_color}** ({'✅' if main2_success else '❌'}, {main2_attempts} поп.)\n"
                token2_text += f"🎨 **{extra2_color}** ({'✅' if extra2_success else '❌'}, {extra2_attempts} поп.)"
                result_embed.add_field(
                    name=f"🤖 Токен 2",
                    value=token2_text,
                    inline=True
                )
                
                result_embed.add_field(
                    name="⚡ Статистика",
                    value=f"⏱️ Общее время: {total_elapsed:.2f}с\n"
                          f"📨 Всего попыток: {main1_attempts + extra1_attempts + main2_attempts + extra2_attempts}",
                    inline=False
                )
            
            await interaction.edit_original_response(embed=result_embed, view=None)
            return True
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ ОШИБКА",
                description=str(e),
                color=0xff0000
            )
            await interaction.edit_original_response(embed=error_embed, view=None)
            return False
        finally:
            if task_id in active_mcl_tasks:
                del active_mcl_tasks[task_id]
            async with self.sending_lock:
                self.sending_active = False
                self.current_sender = None
                self.sender_name = None

dual_mcl_core = DualMCLCore()