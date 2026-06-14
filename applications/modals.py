"""Модалки для системы заявок"""
import discord
import json
from datetime import datetime
from applications.manager import app_manager
from core.database import db


class ApplicationModal(discord.ui.Modal, title="📝 ЗАЯВКА В СЕМЬЮ"):
    """Динамическая модалка заявки"""
    
    def __init__(self):
        super().__init__()
        self.fields = []
        try:
            self._add_fields()
        except Exception as e:
            print(f"❌ [ЗАЯВКА] Ошибка в __init__: {e}")
            import traceback
            traceback.print_exc()
    
    def _add_fields(self):
        """Динамически добавляем поля из БД"""
        try:
            fields = db.get_application_fields()
            print(f"🔍 [ЗАЯВКА] Загружено полей: {len(fields)}")
            
            if not fields:
                print("❌ [ЗАЯВКА] Нет полей в БД!")
                text_input = discord.ui.TextInput(
                    label="Ошибка",
                    placeholder="Нет настроенных полей, обратитесь к администратору",
                    required=False
                )
                self.add_item(text_input)
                return
            
            for field in fields:
                print(f"🔍 [ЗАЯВКА] Добавляю поле: {field['name']} - {field['description']}")
                
                # Discord ограничения: label до 45 символов, placeholder до 100
                label = field['description'] or field['name']
                if len(label) > 45:
                    label = label[:42] + "..."
                
                placeholder = field['placeholder'] or "Введите информацию"
                if len(placeholder) > 100:
                    placeholder = placeholder[:97] + "..."
                
                text_input = discord.ui.TextInput(
                    label=label,
                    placeholder=placeholder,
                    max_length=500,
                    required=field['required'],
                    style=discord.TextStyle.paragraph
                )
                self.add_item(text_input)
                self.fields.append({'id': field['id'], 'name': field['name'], 'input': text_input})
                
        except Exception as e:
            print(f"❌ [ЗАЯВКА] КРИТИЧЕСКАЯ ОШИБКА В _add_fields: {e}")
            import traceback
            traceback.print_exc()
    
    async def on_submit(self, interaction: discord.Interaction):
        # Собираем ответы
        answers = {}
        for field in self.fields:
            answers[field['name']] = field['input'].value
        
        print(f"🔍 [ЗАЯВКА] Ответы: {answers}")
        
        # Сохраняем заявку
        try:
            app_id, error = app_manager.create_application_dynamic(
                user_id=str(interaction.user.id),
                user_name=interaction.user.display_name,
                answers=answers
            )
            print(f"🔍 [ЗАЯВКА] Результат: app_id={app_id}, error={error}")
        except Exception as e:
            print(f"❌ [ЗАЯВКА] Исключение: {e}")
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
            return
        
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="✅ ЗАЯВКА ОТПРАВЛЕНА",
            description="Ваша заявка принята и передана на рассмотрение. Ожидайте решения.",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Отправляем в канал модерации
        await self._send_to_moderation(interaction, app_id, answers)
    
    async def _send_to_moderation(self, interaction, app_id: int, answers: dict):
        settings = app_manager.get_settings()
        applications_channel_id = settings.get('applications_channel')
        
        if not applications_channel_id:
            print("❌ Канал для анкет не настроен")
            return
        
        applications_channel = interaction.client.get_channel(int(applications_channel_id))
        if not applications_channel:
            print(f"❌ Канал {applications_channel_id} не найден")
            return
        
        # Получаем описания полей из БД
        fields_info = {f['name']: f['description'] for f in db.get_application_fields()}
        
        embed = discord.Embed(
            title="📝 НОВАЯ ЗАЯВКА",
            color=0xffa500,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Отправитель", value=interaction.user.mention, inline=True)
        
        for key, value in answers.items():
            if value:
                display_name = fields_info.get(key, key)
                embed.add_field(name=display_name, value=value[:1024], inline=False)
        
        embed.set_footer(text=f"Заявка ID: {app_id}")
        
        recruit_role_id = settings.get('applications_recruit_role')
        content = f"<@&{recruit_role_id}>" if recruit_role_id else None
        
        from applications.views import ApplicationModerationView
        sent_message = await applications_channel.send(
            content=content,
            embed=embed,
            view=ApplicationModerationView(app_id, str(interaction.user.id))
        )
        
        app_manager.save_application_message(
            application_id=app_id,
            channel_id=str(applications_channel.id),
            message_id=str(sent_message.id),
            user_id=str(interaction.user.id)
        )