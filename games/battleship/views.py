"""Кнопки для морского боя"""
import discord
import json
from core.database import db
from games.battleship.embeds import get_top_embed


class GameLobbyView(discord.ui.View):
    """Постоянная панель лобби"""

    def __init__(self):
        super().__init__(timeout=None)
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
        from games.manager import game_manager  # ← ЛОКАЛЬНЫЙ ИМПОРТ
        
        if not db.get_game_enabled("battleship"):
            await interaction.response.send_message("❌ Игра временно отключена администратором!", ephemeral=True)
            return

        if game_manager.get_player_game(str(interaction.user.id)):
            await interaction.response.send_message("❌ Вы уже участвуете в игре!", ephemeral=True)
            return

        try:
            await interaction.user.send("✅ Бот может отправлять вам сообщения")
        except:
            await interaction.response.send_message(
                "❌ Бот не может отправить вам личное сообщение.\nПожалуйста, откройте ЛС с ботом.",
                ephemeral=True
            )
            return

        waiting = game_manager.waiting_players.get("battleship", [])

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
            else:
                await player1.send("❌ Не удалось создать игру.")
                await player2.send("❌ Не удалось создать игру.")
                waiting.append(player1)
                waiting.append(player2)
                game_manager.waiting_players["battleship"] = waiting

        # Обновляем кнопку
        self.add_join_button()
        await interaction.message.edit(view=self)

    async def interaction_check(self, interaction):
        return True


class BattleshipView(discord.ui.View):
    """View для управления игрой в ЛС"""

    def __init__(self, game, player):
        super().__init__(timeout=90)
        self.game = game
        self.player = player
        self.current_row = 0
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()

        is_my_turn = self.game.current_turn.id == self.player.id
        turn_text = f"🎯 Ход: {'ВАШ' if is_my_turn else 'ПРОТИВНИКА'}"
        self.add_item(discord.ui.Button(label=turn_text, style=discord.ButtonStyle.secondary, disabled=True))

        self.add_item(discord.ui.Button(label=f"📌 Ряд: {chr(65 + self.current_row)}",
                                        style=discord.ButtonStyle.primary, disabled=True))

        up = discord.ui.Button(label="⬆️", style=discord.ButtonStyle.secondary)
        up.callback = self.previous_row
        self.add_item(up)

        down = discord.ui.Button(label="⬇️", style=discord.ButtonStyle.secondary)
        down.callback = self.next_row
        self.add_item(down)

        for col in range(10):
            btn = discord.ui.Button(label=str(col + 1), style=discord.ButtonStyle.success if is_my_turn else discord.ButtonStyle.secondary)
            btn.callback = self.create_shot_callback(self.current_row, col)
            if not is_my_turn:
                btn.disabled = True
            self.add_item(btn)

        skip = discord.ui.Button(label="⏭️ Пропустить", style=discord.ButtonStyle.danger)
        skip.callback = self.skip_turn
        if not is_my_turn:
            skip.disabled = True
        self.add_item(skip)

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
            from games.manager import game_manager  # ← ЛОКАЛЬНЫЙ ИМПОРТ
            await game_manager.make_move(self.player, self.game.game_id, {'row': row, 'col': col})
            await interaction.response.defer()
        return callback

    async def skip_turn(self, interaction: discord.Interaction):
        from games.manager import game_manager  # ← ЛОКАЛЬНЫЙ ИМПОРТ

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

            db.save_active_game(
                game_id=self.game.game_id,
                game_type="battleship",
                channel_id=str(self.game.channel.id),
                player1_id=str(self.game.player1.id),
                player2_id=str(self.game.player2.id),
                game_data=json.dumps(self.game.get_state()),
                current_turn=str(self.game.current_turn.id)
            )

            await interaction.response.send_message(f"⏭️ Вы пропустили ход! Осталось: {3 - passes}")

            await game_manager.send_game_interface(self.player, self.game)
            await game_manager.send_game_interface(self.game.get_opponent(self.player), self.game)

        self._build_buttons()

    async def on_timeout(self):
        if not self.game.game_over:
            from games.manager import game_manager  # ← ЛОКАЛЬНЫЙ ИМПОРТ
            self.game.game_over = True
            self.game.winner = self.game.get_opponent(self.player)
            await game_manager.end_game(self.game.game_id, self.game.winner, self.player)