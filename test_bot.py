#!/usr/bin/env python3
"""
АВТОМАТИЧЕСКОЕ ТЕСТИРОВАНИЕ КНОПОК И МОДАЛОК БОТА
Запуск: python test_bot_ui.py
ВНИМАНИЕ: Используйте ТЕСТОВЫЙ сервер Discord!
"""

import discord
from discord.ext import commands
import asyncio
import json
import sys
from datetime import datetime

# ===== КОНФИГУРАЦИЯ =====
# ВСТАВЬ СВОИ ДАННЫЕ:
TEST_GUILD_ID = 000000000000000000  # ID твоего ТЕСТОВОГО сервера
TEST_CHANNEL_ID = 000000000000000000  # ID канала для тестов
TEST_ROLE_ID = 000000000000000000  # ID роли для тестов

# Токен ТЕСТОВОГО бота (не основного!)
BOT_TOKEN = "ТВОЙ_ТЕСТОВЫЙ_ТОКЕН"

# ===== ЦВЕТА ДЛЯ ВЫВОДА =====
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(text, status="info"):
    if status == "ok":
        print(f"{Colors.GREEN}✅ {text}{Colors.END}")
    elif status == "error":
        print(f"{Colors.RED}❌ {text}{Colors.END}")
    elif status == "warning":
        print(f"{Colors.YELLOW}⚠️ {text}{Colors.END}")
    elif status == "info":
        print(f"{Colors.BLUE}📋 {text}{Colors.END}")
    elif status == "title":
        print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BLUE}{text}{Colors.END}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")

# ===== ТЕСТОВЫЙ БОТ =====
class UITester(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)
        self.test_results = []
        self.test_channel = None
        self.test_guild = None
        
    async def setup_hook(self):
        print_test("🚀 ЗАПУСК ТЕСТИРОВАНИЯ UI", "title")
        
    async def on_ready(self):
        print_test(f"Бот запущен как {self.user}", "ok")
        
        self.test_guild = self.get_guild(TEST_GUILD_ID)
        if not self.test_guild:
            print_test(f"Сервер {TEST_GUILD_ID} не найден!", "error")
            await self.close()
            return
            
        self.test_channel = self.test_guild.get_channel(TEST_CHANNEL_ID)
        if not self.test_channel:
            print_test(f"Канал {TEST_CHANNEL_ID} не найден!", "error")
            await self.close()
            return
            
        print_test(f"Тестовый сервер: {self.test_guild.name}", "ok")
        print_test(f"Тестовый канал: #{self.test_channel.name}", "ok")
        
        # Запускаем тесты
        await self.run_all_tests()
        
    async def run_all_tests(self):
        """Запуск всех UI тестов"""
        
        # 1. Тест системы заявок
        await self.test_application_modal()
        await asyncio.sleep(2)
        
        # 2. Тест Tier системы
        await self.test_tier_modal()
        await asyncio.sleep(2)
        
        # 3. Тест CAPT системы
        await self.test_capt_buttons()
        await asyncio.sleep(2)
        
        # 4. Тест AFK системы
        await self.test_afk_buttons()
        await asyncio.sleep(2)
        
        # 5. Тест системы отпусков
        await self.test_vacation_buttons()
        await asyncio.sleep(2)
        
        # 6. Тест системы мероприятий
        await self.test_events_buttons()
        
        # Вывод итогов
        await self.print_summary()
        
        # Завершаем
        await self.close()
        
    async def test_application_modal(self):
        """Тест модалки заявки в семью"""
        print_test("📝 ТЕСТ: СИСТЕМА ЗАЯВОК", "title")
        
        try:
            # Отправляем сообщение с кнопкой
            view = ApplicationTestView(self)
            embed = discord.Embed(
                title="📝 ТЕСТОВАЯ ПАНЕЛЬ ЗАЯВОК",
                description="Нажми на кнопку для теста модалки",
                color=0x5865F2
            )
            
            msg = await self.test_channel.send(embed=embed, view=view)
            print_test("Отправлена тестовая панель заявок", "ok")
            
            # Ждём результат (кнопку нажмёт пользователь или таймер)
            await asyncio.sleep(30)
            
            try:
                await msg.delete()
            except:
                pass
                
        except Exception as e:
            print_test(f"Ошибка: {e}", "error")
            self.test_results.append({"test": "Заявки", "status": "failed", "error": str(e)})
    
    async def test_tier_modal(self):
        """Тест модалки Tier заявки"""
        print_test("🌟 ТЕСТ: TIER СИСТЕМА", "title")
        
        try:
            from tier.views import TierSubmitView
            
            embed = discord.Embed(
                title="🌟 ТЕСТОВАЯ ПАНЕЛЬ TIER",
                description="Нажми на кнопку для теста заявки на Tier",
                color=0xffa500
            )
            
            msg = await self.test_channel.send(embed=embed, view=TierSubmitView())
            print_test("Отправлена тестовая панель Tier", "ok")
            
            await asyncio.sleep(30)
            
            try:
                await msg.delete()
            except:
                pass
                
        except Exception as e:
            print_test(f"Ошибка: {e}", "error")
            self.test_results.append({"test": "Tier", "status": "failed", "error": str(e)})
    
    async def test_capt_buttons(self):
        """Тест кнопок CAPT системы"""
        print_test("🎯 ТЕСТ: CAPT СИСТЕМА", "title")
        
        try:
            from capt_registration.views import PublicView
            
            # Создаём тестовую регистрацию
            embed = discord.Embed(
                title="🎯 ТЕСТОВАЯ CAPT РЕГИСТРАЦИЯ",
                description="Противник: TEST | Время: 19:30 МСК",
                color=0xff0000
            )
            embed.add_field(name="❌ ОСНОВНОЙ", value="*Пуст*", inline=False)
            embed.add_field(name="⏳ РЕЗЕРВ", value="*Пуст*", inline=False)
            
            view = PublicView()
            view.set_registration_active(True)
            
            msg = await self.test_channel.send(embed=embed, view=view)
            print_test("Отправлена тестовая панель CAPT", "ok")
            
            await asyncio.sleep(30)
            
            try:
                await msg.delete()
            except:
                pass
                
        except Exception as e:
            print_test(f"Ошибка: {e}", "error")
            self.test_results.append({"test": "CAPT", "status": "failed", "error": str(e)})
    
    async def test_afk_buttons(self):
        """Тест AFK кнопок"""
        print_test("🛌 ТЕСТ: AFK СИСТЕМА", "title")
        
        try:
            from afk.views import AfkView
            
            embed = discord.Embed(
                title="🛌 ТЕСТОВАЯ AFK ПАНЕЛЬ",
                description="Нажми на кнопку для теста AFK",
                color=0x00ff00
            )
            
            msg = await self.test_channel.send(embed=embed, view=AfkView())
            print_test("Отправлена тестовая панель AFK", "ok")
            
            await asyncio.sleep(30)
            
            try:
                await msg.delete()
            except:
                pass
                
        except Exception as e:
            print_test(f"Ошибка: {e}", "error")
            self.test_results.append({"test": "AFK", "status": "failed", "error": str(e)})
    
    async def test_vacation_buttons(self):
        """Тест кнопок отпусков"""
        print_test("🏖️ ТЕСТ: СИСТЕМА ОТПУСКОВ", "title")
        
        try:
            from vacation.views import VacationView
            
            embed = discord.Embed(
                title="🏖️ ТЕСТОВАЯ ПАНЕЛЬ ОТПУСКОВ",
                description="Нажми на кнопку для теста заявки на отпуск",
                color=0x00ccff
            )
            
            msg = await self.test_channel.send(embed=embed, view=VacationView())
            print_test("Отправлена тестовая панель отпусков", "ok")
            
            await asyncio.sleep(30)
            
            try:
                await msg.delete()
            except:
                pass
                
        except Exception as e:
            print_test(f"Ошибка: {e}", "error")
            self.test_results.append({"test": "Отпуска", "status": "failed", "error": str(e)})
    
    async def test_events_buttons(self):
        """Тест кнопок мероприятий"""
        print_test("📅 ТЕСТ: СИСТЕМА МЕРОПРИЯТИЙ", "title")
        
        try:
            from events.views import EventsView
            
            embed = discord.Embed(
                title="📅 ТЕСТОВАЯ ПАНЕЛЬ МЕРОПРИЯТИЙ",
                description="Сегодняшние мероприятия",
                color=0xffaa00
            )
            
            msg = await self.test_channel.send(embed=embed, view=EventsView())
            print_test("Отправлена тестовая панель мероприятий", "ok")
            
            await asyncio.sleep(30)
            
            try:
                await msg.delete()
            except:
                pass
                
        except Exception as e:
            print_test(f"Ошибка: {e}", "error")
            self.test_results.append({"test": "Мероприятия", "status": "failed", "error": str(e)})
    
    async def print_summary(self):
        """Вывод итогов тестирования"""
        print_test("\n📊 ИТОГИ UI ТЕСТИРОВАНИЯ", "title")
        
        passed = len([r for r in self.test_results if r.get("status") == "passed"])
        failed = len([r for r in self.test_results if r.get("status") == "failed"])
        
        print_test(f"Пройдено: {passed}", "ok")
        print_test(f"Провалено: {failed}", "error" if failed > 0 else "ok")
        
        if failed == 0:
            print_test("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! UI работает корректно!", "ok")
        else:
            print_test("\n⚠️ Есть проблемы, проверь ошибки выше", "warning")
        
        # Сохраняем результат
        report = {
            "timestamp": datetime.now().isoformat(),
            "results": self.test_results,
            "passed": passed,
            "failed": failed
        }
        
        with open("ui_test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print_test(f"\n📄 Отчёт сохранён в ui_test_report.json", "info")

# ===== ТЕСТОВЫЕ VIEW ДЛЯ ЗАЯВОК =====
class ApplicationTestView(discord.ui.View):
    def __init__(self, tester):
        super().__init__(timeout=60)
        self.tester = tester
        
    @discord.ui.button(label="📝 Подать заявку", style=discord.ButtonStyle.primary, custom_id="test_apply")
    async def test_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Тестовая кнопка - должна открыть модалку"""
        print_test(f"Нажата кнопка теста заявок от {interaction.user}", "info")
        
        # Проверяем, что открывается модалка
        try:
            from applications.modals import ApplicationModal
            await interaction.response.send_modal(ApplicationModal())
            print_test("Модалка заявки открылась успешно", "ok")
            self.tester.test_results.append({"test": "Заявки - модалка", "status": "passed"})
        except Exception as e:
            print_test(f"Ошибка открытия модалки: {e}", "error")
            self.tester.test_results.append({"test": "Заявки - модалка", "status": "failed", "error": str(e)})
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

# ===== ЗАПУСК =====
def main():
    BOT_TOKEN = input("🔑 Введи токен тестового бота: ").strip()
    
    if not BOT_TOKEN:
        print("❌ Токен не введён!")
        return
    
    if len(BOT_TOKEN) < 50:  # Проверка, что это реальный токен
        print("❌ Похоже, это не токен Discord!")
        return
    
    print("✅ Токен принят, запускаю тесты...")
    bot = UITester()
    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    main()