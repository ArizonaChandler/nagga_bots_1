"""Кнопки для морского боя"""
import discord
import json
import logging
from core.database import db
from games.battleship.embeds import get_top_embed

logger = logging.getLogger(__name__)


class GameLobbyView(discord.ui.View):
    """Постоянная панель лобби"""

    def __init__(self):
        super().__init__(timeout=None)
        logger.info("🎮 GameLobbyView создан")
        self.add_join_button()

    def add_join_button(self):
        self.clear_items()
        btn = discord.ui.Button(
            label="✅ ВОЙТИ В ОЧЕРЕДЬ",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id="game_lobby_join"
        )
        btn.callback = self.toggle_queue
        self.add_item(btn)

    async def toggle_queue(self, interaction: discord.Interaction):
        logger.info(f"🔘 Нажата кнопка 'ВОЙТИ В ОЧЕРЕДЬ' от {interaction.user.name}")

        try:
            from games.manager import game_manager

            if not db.get_game_enabled("battleship"):
                await interaction.response.send_message("❌ Игра временно отключена администратором!", ephemeral=True)
                return

            # Проверка, не в игре ли уже
            if game_manager.get_player_game(str(interaction.user.id)):
                await interaction.response.send_message("❌ Вы уже участвуете в игре!", ephemeral=True)
                return

            # Проверка ЛС
            try:
                await interaction.user.send("✅ Бот может отправлять вам сообщения")
            except Exception:
                await interaction.response.send_message(
                    "❌ Бот не может отправить вам личное сообщение.\nПожалуйста, откройте ЛС с ботом.",
                    ephemeral=True
                )
                return

            waiting = game_manager.waiting_players.get("battleship", [])
            
            # Проверка, не в очереди ли уже
            if interaction.user in waiting:
                waiting.remove(interaction.user)
                await interaction.response.send_message("✅ Вы вышли из очереди!", ephemeral=True)
                await game_manager.log(f"🚪 {interaction.user.display_name} вышел из очереди")
            else:
                waiting.append(interaction.user)
                await interaction.response.send_message("✅ Вы добавлены в очередь!", ephemeral=True)
                await game_manager.log(f"👤 {interaction.user.display_name} вошёл в очередь")

            game_manager.waiting_players["battleship"] = waiting

            # Проверяем, есть ли пара
            if len(waiting) >= 2:
                player1 = waiting.pop(0)
                player2 = waiting.pop(0)
                game_manager.waiting_players["battleship"] = waiting

                success = await game_manager.create_game("battleship", player1, player2)
                if success:
                    await player1.send("🎮 **Соперник найден!** Игра начинается...")
                    await player2.send("🎮 **Соперник найден!** Игра начинается...")
                    logger.info(f"Игра создана: {player1.name} vs {player2.name}")
                else:
                    await player1.send("❌ Не удалось создать игру. Попробуйте позже.")
                    await player2.send("❌ Не удалось создать игру. Попробуйте позже.")
                    waiting.append(player1)
                    waiting.append(player2)
                    game_manager.waiting_players["battleship"] = waiting

            # Обновляем кнопку
            self.add_join_button()
            await interaction.message.edit(view=self)

        except Exception as e:
            logger.error(f"ОШИБКА в toggle_queue: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


class BattleshipView(discord.ui.View):
    """View для управления игрой в ЛС"""

    def __init__(self, game, player):
        super().__init__(timeout=90)
        self.game = game
        self.player = player
        self.current_row = 0  # 0-9 (A-J)
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()

        is_my_turn = self.game.current_turn.id == self.player.id
        is_game_over = self.game.game_over
        
        # Статус
        if is_game_over:
            status_text = "🏆 ИГРА ЗАВЕРШЕНА 🏆"
            status_style = discord.ButtonStyle.secondary
        elif is_my_turn:
            status_text = "🎯 ВАШ ХОД"
            status_style = discord.ButtonStyle.success
        else:
            status_text = "⏳ ХОД ПРОТИВНИКА"
            status_style = discord.ButtonStyle.secondary
        
        status_btn = discord.ui.Button(label=status_text, style=status_style, disabled=True)
        self.add_item(status_btn)

        # Текущий ряд
        row_letter = chr(65 + self.current_row)  # A-J
        row_btn = discord.ui.Button(label=f"📌 Ряд: {row_letter}", style=discord.ButtonStyle.primary, disabled=True)
        self.add_item(row_btn)

        # Кнопки навигации по рядам
        up_btn = discord.ui.Button(label="⬆️", style=discord.ButtonStyle.secondary, disabled=is_game_over or not is_my_turn)
        up_btn.callback = self.previous_row
        self.add_item(up_btn)

        down_btn = discord.ui.Button(label="⬇️", style=discord.ButtonStyle.secondary, disabled=is_game_over or not is_my_turn)
        down_btn.callback = self.next_row
        self.add_item(down_btn)

        # Кнопки для колонок 1-10
        for col in range(10):
            btn = discord.ui.Button(
                label=str(col + 1), 
                style=discord.ButtonStyle.success if (is_my_turn and not is_game_over) else discord.ButtonStyle.secondary,
                disabled=is_game_over or not is_my_turn
            )
            btn.callback = self.create_shot_callback(self.current_row, col)
            self.add_item(btn)

        # Кнопка пропуска
        skip_btn = discord.ui.Button(
            label="⏭️ Пропустить ход", 
            style=discord.ButtonStyle.danger,
            disabled=is_game_over or not is_my_turn
        )
        skip_btn.callback = self.skip_turn
        self.add_item(skip_btn)

    async def previous_row(self, interaction: discord.Interaction):
        self.current_row = (self.current_row - 1) % 10
        self._build_buttons()
        await interaction.response.edit_message(view=self)

    async def next_row(self, interaction: discord.Interaction):
        self.current_row = (self.current_row + 1) % 10
        self._build_buttons()
        await interaction.response.edit_message(view=self)

    def create_shot_callback(self, row, col):
        async def callback(interaction: discord.Interaction):
            from games.manager import game_manager
            
            # Двойная проверка — что это именно тот игрок и его ход
            if self.game.game_over:
                await interaction.response.send_message("❌ Игра уже закончена!", ephemeral=True)
                return
                
            if self.game.current_turn.id != self.player.id:
                await interaction.response.send_message("❌ Сейчас не ваш ход!", ephemeral=True)
                return
            
            # Делаем ход
            await game_manager.make_move(self.player, self.game.game_id, {'row': row, 'col': col})
            await interaction.response.defer()
        return callback

    async def skip_turn(self, interaction: discord.Interaction):
        from games.manager import game_manager

        if self.game.game_over:
            await interaction.response.send_message("❌ Игра уже закончена!", ephemeral=True)
            return

        if self.game.current_turn.id != self.player.id:
            await interaction.response.send_message("❌ Сейчас не ваш ход!", ephemeral=True)
            return

        passes = self.game.passes.get(str(self.player.id), 0) + 1

        if passes >= 3:
            self.game.game_over = True
            self.game.winner = self.game.get_opponent(self.player)
            await game_manager.end_game(self.game.game_id, self.game.winner, self.player)
            await interaction.response.send_message("❌ Вы проиграли из-за трёх пропусков!", ephemeral=True)
        else:
            self.game.passes[str(self.player.id)] = passes
            self.game.current_turn = self.game.get_opponent(self.player)

            # Сохраняем состояние
            db.save_active_game(
                game_id=self.game.game_id,
                game_type="battleship",
                channel_id=str(self.game.channel.id),
                player1_id=str(self.game.player1.id),
                player2_id=str(self.game.player2.id),
                game_data=json.dumps(self.game.get_state()),
                current_turn=str(self.game.current_turn.id)
            )

            await interaction.response.send_message(f"⏭️ Вы пропустили ход! Осталось пропусков: {3 - passes}")

            # Обновляем интерфейс обоим игрокам
            await game_manager.send_game_interface(self.player, self.game, is_update=True)
            await game_manager.send_game_interface(self.game.get_opponent(self.player), self.game, is_update=True)

        self._build_buttons()

    async def on_timeout(self):
        if not self.game.game_over:
            from games.manager import game_manager
            self.game.game_over = True
            self.game.winner = self.game.get_opponent(self.player)
            await game_manager.end_game(self.game.game_id, self.game.winner, self.player)