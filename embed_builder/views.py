"""Кнопки для системы создания embed"""
import discord
from embed_builder.base import PermanentView
from embed_builder.modals import CreateEmbedModal, AdvancedEmbedModal, AddFieldModal
from embed_builder.manager import embed_builder_manager


class EmbedBuilderPanelView(PermanentView):
    """Главная панель для создания embed"""
    
    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id
        self._add_buttons()
    
    def _add_buttons(self):
        self.clear_items()
        
        simple_btn = discord.ui.Button(
            label="📝 ПРОСТОЙ EMBED",
            style=discord.ButtonStyle.primary,
            emoji="📝",
            row=0,
            custom_id="embed_simple"
        )
        simple_btn.callback = self.simple_embed
        self.add_item(simple_btn)
        
        advanced_btn = discord.ui.Button(
            label="🎨 РАСШИРЕННЫЙ EMBED",
            style=discord.ButtonStyle.success,
            emoji="🎨",
            row=0,
            custom_id="embed_advanced"
        )
        advanced_btn.callback = self.advanced_embed
        self.add_item(advanced_btn)
        
        fields_btn = discord.ui.Button(
            label="➕ EMBED С ПОЛЯМИ",
            style=discord.ButtonStyle.secondary,
            emoji="➕",
            row=1,
            custom_id="embed_fields"
        )
        fields_btn.callback = self.embed_with_fields
        self.add_item(fields_btn)
        
        # 🔥 КНОПКА "НАЗАД"
        back_btn = discord.ui.Button(
            label="◀ Назад в настройки",
            style=discord.ButtonStyle.secondary,
            emoji="◀",
            row=2,
            custom_id="embed_back"
        )
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    async def simple_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Создать простой embed"""
        await interaction.response.send_modal(CreateEmbedModal(self.channel_id))
    
    async def advanced_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Создать расширенный embed"""
        await interaction.response.send_modal(AdvancedEmbedModal(self.channel_id))
    
    async def embed_with_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Создать embed с полями"""
        fields = []
        
        view = FieldsBuilderView(fields, self.channel_id, self)
        embed = discord.Embed(
            title="📋 СОЗДАНИЕ EMBED С ПОЛЯМИ",
            description="Нажмите «➕ Добавить поле» чтобы добавить поля.\nКогда закончите — нажмите «📨 Отправить»",
            color=0x7289da
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Вернуться в панель настроек"""
        from embed_builder.settings_view import EmbedBuilderSettingsView
        
        embed = discord.Embed(
            title="📦 **СОЗДАНИЕ EMBED**",
            description="Настройка системы создания embed сообщений",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=EmbedBuilderSettingsView())


class FieldsBuilderView(discord.ui.View):
    def __init__(self, fields: list, channel_id: int, parent_view: EmbedBuilderPanelView):
        super().__init__(timeout=120)
        self.fields = fields
        self.channel_id = channel_id
        self.parent_view = parent_view
    
    @discord.ui.button(label="➕ ДОБАВИТЬ ПОЛЕ", style=discord.ButtonStyle.success, emoji="➕", row=0)
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddFieldModal(self.channel_id, self.fields))
    
    @discord.ui.button(label="📨 ОТПРАВИТЬ", style=discord.ButtonStyle.primary, emoji="📨", row=1)
    async def send_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SendFieldsEmbedModal(self.channel_id, self.fields))
    
    @discord.ui.button(label="◀ НАЗАД", style=discord.ButtonStyle.secondary, emoji="◀", row=1)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Вернуться к выбору типа embed"""
        embed = discord.Embed(
            title="📝 **СОЗДАНИЕ EMBED**",
            description="Выберите тип embed для создания",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=self.parent_view)
    
    @discord.ui.button(label="❌ ОТМЕНА", style=discord.ButtonStyle.danger, emoji="❌", row=2)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Создание отменено", embed=None, view=None)


class SendFieldsEmbedModal(discord.ui.Modal, title="📨 ОТПРАВКА EMBED"):
    
    title = discord.ui.TextInput(
        label="Заголовок",
        placeholder="Введите заголовок embed",
        max_length=256,
        required=False
    )
    
    description = discord.ui.TextInput(
        label="Текст",
        placeholder="Введите основной текст embed",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=True
    )
    
    color = discord.ui.TextInput(
        label="Цвет (HEX)",
        placeholder="#00ff00",
        max_length=7,
        required=False,
        default="#00ff00"
    )
    
    image_url = discord.ui.TextInput(
        label="Ссылка на изображение",
        placeholder="https://example.com/image.png",
        max_length=500,
        required=False
    )
    
    footer = discord.ui.TextInput(
        label="Футер",
        placeholder="Текст внизу embed",
        max_length=2048,
        required=False
    )
    
    def __init__(self, channel_id: int, fields: list):
        super().__init__()
        self.channel_id = channel_id
        self.fields = fields
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            color_val = self.color.value
            if not color_val:
                color_val = "#00ff00"
            
            if color_val.startswith('#'):
                color_val = int(color_val[1:], 16)
            elif color_val.startswith('0x'):
                color_val = int(color_val, 16)
            else:
                color_val = int(color_val, 16) if color_val else 0x00ff00
        except:
            color_val = 0x00ff00
        
        success, msg = await embed_builder_manager.send_embed(
            channel_id=self.channel_id,
            title=self.title.value,
            description=self.description.value,
            color=color_val,
            image_url=self.image_url.value if self.image_url.value else None,
            footer=self.footer.value if self.footer.value else None,
            fields=self.fields
        )
        
        await interaction.response.send_message(msg, ephemeral=True)