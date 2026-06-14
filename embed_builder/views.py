"""Кнопки для системы создания embed"""
import discord
from embed_builder.base import PermanentView
from embed_builder.modals import CreateEmbedModal, AdvancedEmbedModal, AddFieldModal


class EmbedBuilderPanelView(PermanentView):
    """Главная панель для создания embed"""
    
    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id
    
    @discord.ui.button(
        label="📝 ПРОСТОЙ EMBED",
        style=discord.ButtonStyle.primary,
        emoji="📝",
        row=0,
        custom_id="embed_simple"
    )
    async def simple_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Создать простой embed"""
        await interaction.response.send_modal(CreateEmbedModal(self.channel_id))
    
    @discord.ui.button(
        label="🎨 РАСШИРЕННЫЙ EMBED",
        style=discord.ButtonStyle.success,
        emoji="🎨",
        row=0,
        custom_id="embed_advanced"
    )
    async def advanced_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Создать расширенный embed"""
        await interaction.response.send_modal(AdvancedEmbedModal(self.channel_id))
    
    @discord.ui.button(
        label="➕ EMBED С ПОЛЯМИ",
        style=discord.ButtonStyle.secondary,
        emoji="➕",
        row=1,
        custom_id="embed_fields"
    )
    async def embed_with_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Создать embed с полями"""
        fields = []
        
        async def add_field_callback(interaction: discord.Interaction):
            await interaction.response.send_modal(AddFieldModal(self.channel_id, fields))
        
        async def send_callback(interaction: discord.Interaction):
            await interaction.response.send_modal(SendFieldsEmbedModal(self.channel_id, fields))
        
        view = FieldsBuilderView(fields, self.channel_id)
        embed = discord.Embed(
            title="📋 СОЗДАНИЕ EMBED С ПОЛЯМИ",
            description="Нажмите «➕ Добавить поле» чтобы добавить поля.\nКогда закончите — нажмите «📨 Отправить»",
            color=0x7289da
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class FieldsBuilderView(discord.ui.View):
    def __init__(self, fields: list, channel_id: int):
        super().__init__(timeout=120)
        self.fields = fields
        self.channel_id = channel_id
    
    @discord.ui.button(label="➕ ДОБАВИТЬ ПОЛЕ", style=discord.ButtonStyle.success, emoji="➕", row=0)
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddFieldModal(self.channel_id, self.fields))
    
    @discord.ui.button(label="📨 ОТПРАВИТЬ", style=discord.ButtonStyle.primary, emoji="📨", row=1)
    async def send_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SendFieldsEmbedModal(self.channel_id, self.fields))
    
    @discord.ui.button(label="❌ ОТМЕНА", style=discord.ButtonStyle.danger, emoji="❌", row=1)
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