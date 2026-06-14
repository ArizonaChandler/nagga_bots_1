"""Модальные окна для создания embed"""
import discord
from embed_builder.manager import embed_builder_manager


class CreateEmbedModal(discord.ui.Modal, title="📝 СОЗДАНИЕ EMBED"):
    
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
        placeholder="#00ff00 или 0x00ff00",
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
        label="Футер (нижний текст)",
        placeholder="Текст внизу embed",
        max_length=2048,
        required=False
    )
    
    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id
        print(f"📦 [EMBED_BUILDER] CreateEmbedModal создан, channel_id={channel_id}")
    
    async def on_submit(self, interaction: discord.Interaction):
        print(f"📦 [EMBED_BUILDER] CreateEmbedModal.on_submit вызван")
        
        try:
            # Преобразуем цвет
            color_val = self.color.value
            if not color_val:
                color_val = "#00ff00"
            
            if color_val.startswith('#'):
                color_val = int(color_val[1:], 16)
            elif color_val.startswith('0x'):
                color_val = int(color_val, 16)
            else:
                color_val = int(color_val, 16) if color_val else 0x00ff00
        except Exception as e:
            print(f"❌ Ошибка преобразования цвета: {e}")
            color_val = 0x00ff00
        
        print(f"📦 [EMBED_BUILDER] Отправка embed в канал {self.channel_id}")
        
        success, msg = await embed_builder_manager.send_embed(
            channel_id=self.channel_id,
            title=self.title.value,
            description=self.description.value,
            color=color_val,
            image_url=self.image_url.value if self.image_url.value else None,
            footer=self.footer.value if self.footer.value else None
        )
        
        await interaction.response.send_message(msg, ephemeral=True)


class AdvancedEmbedModal(discord.ui.Modal, title="🎨 РАСШИРЕННОЕ СОЗДАНИЕ EMBED"):
    
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
        label="Ссылка на изображение (основное)",
        placeholder="https://example.com/image.png",
        max_length=500,
        required=False
    )
    
    thumbnail_url = discord.ui.TextInput(
        label="Ссылка на миниатюру (иконка)",
        placeholder="https://example.com/icon.png",
        max_length=500,
        required=False
    )
    
    footer = discord.ui.TextInput(
        label="Футер",
        placeholder="Текст внизу embed",
        max_length=2048,
        required=False
    )
    
    author_name = discord.ui.TextInput(
        label="Автор (имя)",
        placeholder="Имя автора",
        max_length=256,
        required=False
    )
    
    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id
        print(f"📦 [EMBED_BUILDER] AdvancedEmbedModal создан, channel_id={channel_id}")
    
    async def on_submit(self, interaction: discord.Interaction):
        print(f"📦 [EMBED_BUILDER] AdvancedEmbedModal.on_submit вызван")
        
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
        except Exception as e:
            print(f"❌ Ошибка преобразования цвета: {e}")
            color_val = 0x00ff00
        
        print(f"📦 [EMBED_BUILDER] Отправка расширенного embed в канал {self.channel_id}")
        
        success, msg = await embed_builder_manager.send_embed(
            channel_id=self.channel_id,
            title=self.title.value,
            description=self.description.value,
            color=color_val,
            image_url=self.image_url.value if self.image_url.value else None,
            thumbnail_url=self.thumbnail_url.value if self.thumbnail_url.value else None,
            footer=self.footer.value if self.footer.value else None,
            author_name=self.author_name.value if self.author_name.value else None
        )
        
        await interaction.response.send_message(msg, ephemeral=True)


class AddFieldModal(discord.ui.Modal, title="➕ ДОБАВИТЬ ПОЛЕ"):
    
    field_name = discord.ui.TextInput(
        label="Название поля",
        placeholder="Введите название",
        max_length=256,
        required=True
    )
    
    field_value = discord.ui.TextInput(
        label="Значение поля",
        placeholder="Введите текст поля",
        style=discord.TextStyle.paragraph,
        max_length=1024,
        required=True
    )
    
    inline = discord.ui.TextInput(
        label="В строку? (да/нет)",
        placeholder="да",
        max_length=3,
        required=False,
        default="нет"
    )
    
    def __init__(self, channel_id: int, fields_list: list):
        super().__init__()
        self.channel_id = channel_id
        self.fields_list = fields_list
    
    async def on_submit(self, interaction: discord.Interaction):
        inline_val = self.inline.value.lower() in ['да', 'yes', 'true', '1']
        
        self.fields_list.append({
            'name': self.field_name.value,
            'value': self.field_value.value,
            'inline': inline_val
        })
        
        await interaction.response.send_message(f"✅ Поле **{self.field_name.value}** добавлено! Всего полей: {len(self.fields_list)}", ephemeral=True)


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
        print(f"📦 [EMBED_BUILDER] SendFieldsEmbedModal создан, channel_id={channel_id}, полей={len(fields)}")
    
    async def on_submit(self, interaction: discord.Interaction):
        print(f"📦 [EMBED_BUILDER] SendFieldsEmbedModal.on_submit вызван")
        
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
        except Exception as e:
            print(f"❌ Ошибка преобразования цвета: {e}")
            color_val = 0x00ff00
        
        print(f"📦 [EMBED_BUILDER] Отправка embed с полями в канал {self.channel_id}")
        
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