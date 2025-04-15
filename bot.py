import os
import logging
from datetime import date
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from save_into_google_sheet import insert_info_into_sheet, account_map

# Получаем токен бота из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Определяем состояния формы для адреса


class AddressForm(StatesGroup):
    street = State()
    house = State()
    apartment = State()
    cold_water = State()
    electr = State()

# Определяем состояния формы для лицевого счёта


class AccountForm(StatesGroup):
    account = State()
    address = State()
    apartment = State()
    cold_water = State()
    electr = State()


# Создаём инлайн-клавиатуру для выбора улицы
street_keyboard = InlineKeyboardMarkup(row_width=1)
streets = [
    "ул. Рыленкова",
    "ул. Генерала Коновницына",
    "ул. Генерала Паскевича",
    "пр-д Соловьиная роща",
    "ул. Брылевка"
]

for street in streets:
    # Используем префикс для callback_data
    street_keyboard.add(InlineKeyboardButton(
        text=street, callback_data=f"street_{street}"))
street_keyboard.add(InlineKeyboardButton(
    text="Назад", callback_data="meter_readings"))

# Обработчик команд /start и /menu


@dp.message_handler(commands=['start', 'menu'], state="*")
async def send_welcome(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="Передать показания",
                             callback_data="meter_readings"),
        InlineKeyboardButton(text="Официальный сайт",
                             url="https://komfort67.com/index.php")
    )
    message_text = """
👋 Добро пожаловать!  
Выберите нужный раздел для удобного управления услугами:  
• Передать показания счётчиков 📊❄️⚡
• Оф. сайт Управляющей компании ООО Комфорт-сервис ✅
    """
    await message.answer(message_text, reply_markup=keyboard, parse_mode="markdown")
    await state.finish()  # Завершаем работу FSM

# Обработчик кнопки "Передать показания счётчиков"


@dp.callback_query_handler(lambda c: c.data == 'meter_readings', state="*")
async def process_meter_readings(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("По адресу", callback_data="by_address"),
        InlineKeyboardButton("По № лицевого счета", callback_data="by_account")
    )
    await bot.send_message(
        callback_query.from_user.id,
        "Выберите способ передачи показаний:\n(Для выхода в меню воспользуйтесь командой /menu)",
        reply_markup=keyboard
    )
    await bot.answer_callback_query(callback_query.id)
    await state.finish()

# Обработчик кнопки "По адресу"


@dp.callback_query_handler(lambda c: c.data == 'by_address', state="*")
async def process_by_address(callback_query: types.CallbackQuery):
    message_text = "Вы выбрали передачу показаний по адресу.\nВыберите улицу:"
    await bot.send_message(
        callback_query.from_user.id,
        message_text,
        reply_markup=street_keyboard,
        parse_mode="markdown"
    )
    await bot.answer_callback_query(callback_query.id)


@dp.callback_query_handler(lambda c: c.data.startswith("street_"), state="*")
async def process_street(callback_query: types.CallbackQuery, state: FSMContext):
    street = callback_query.data.replace("street_", "")
    await state.update_data(street=street)
    await bot.send_message(callback_query.from_user.id, "Введите номер дома:")
    await AddressForm.house.set()
    await bot.answer_callback_query(callback_query.id)


@dp.message_handler(state=AddressForm.house)
async def process_house(message: types.Message, state: FSMContext):
    await state.update_data(house=message.text)
    await message.answer("Введите номер квартиры:")
    await AddressForm.apartment.set()


@dp.message_handler(state=AddressForm.apartment)
async def process_apartment(message: types.Message, state: FSMContext):
    await state.update_data(apartment=message.text)
    await message.answer("Введите показания счётчика холодной воды:")
    await AddressForm.cold_water.set()

# Обработчик ввода показаний холодной воды (адрес)


@dp.message_handler(state=AddressForm.cold_water)
async def process_cold_water(message: types.Message, state: FSMContext):
    await state.update_data(cold_water=message.text)
    await message.answer("Введите показания счётчика электроэнергии:")
    await AddressForm.electr.set()

# Обработчик ввода показаний электроэнергии (адрес)


@dp.message_handler(state=AddressForm.electr)
async def process_electr(message: types.Message, state: FSMContext):
    await state.update_data(electr=message.text)
    data = await state.get_data()
    street = data.get('street', '').strip()
    house = data.get('house', '').strip()
    apartment = data.get('apartment', '').strip()
    cold_water = data.get('cold_water', '').strip()
    electr = data.get('electr', '').strip()
    result_message = (
        f"Адрес: {street}, дом № {house}\n"
        f"Квартира: Кв. {apartment}\n"
        f"Показания счётчика холодной воды: {cold_water}\n"
        f"Показания счётчика электроэнергии: {electr}\n\n"
        "Проверьте введённые данные. Если всё верно — нажмите «Отправить данные», "
        "иначе — выберите «Заполнить заново»."
    )
    final_keyboard = InlineKeyboardMarkup(row_width=2)
    final_keyboard.add(
        InlineKeyboardButton(text="Отправить данные",
                             callback_data="submit_data"),
        InlineKeyboardButton(text="Заполнить заново",
                             callback_data="meter_readings")
    )
    await message.answer(result_message, reply_markup=final_keyboard)

# Обработчик нажатия кнопки "Отправить данные" (адрес)


@dp.callback_query_handler(lambda c: c.data == 'submit_data', state="*")
async def process_submit(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    today = date.today().strftime("%d.%m.%Y")
    street = data.get('street', '').strip()
    house = data.get('house', '').strip()
    apartment = data.get('apartment', '').strip()
    cold_water = data.get('cold_water', '').strip()
    electr = data.get('electr', '').strip()
    if '.' in cold_water:
        cold_water = cold_water.replace('.', ',')
    answer = [today, None, f"{street}, дом № {house}",
              f"Кв. {apartment}", cold_water, electr]
    result = await insert_info_into_sheet(answer)
    if result:
        await bot.send_message(callback_query.from_user.id, "Ваши данные успешно отправлены!")
    else:
        await bot.send_message(callback_query.from_user.id, "Данные не сохранились! Повторите попытку (/menu)!")
    await state.finish()
    await bot.answer_callback_query(callback_query.id)

# Обработчик кнопки "По № лицевого счёта"


@dp.callback_query_handler(lambda c: c.data == 'by_account', state="*")
async def process_by_account(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.send_message(
        callback_query.from_user.id,
        "Вы выбрали передачу показаний по лицевому счёту.\nПожалуйста, введите номер вашего лицевого счёта:",
        parse_mode="markdown"
    )
    await AccountForm.account.set()
    await bot.answer_callback_query(callback_query.id)

# Обработчик ввода номера лицевого счёта


@dp.message_handler(state=AccountForm.account)
async def process_account(message: types.Message, state: FSMContext):
    account_text = message.text.strip()
    if not account_text.isdigit():
        await message.answer("Введён некорректный номер лицевого счёта.\nПожалуйста, попробуйте снова:")
        return
    account = int(account_text)
    account_status = await account_map(account)
    if isinstance(account_status, bool):
        await message.answer("Введён некорректный номер лицевого счёта.\nПожалуйста, попробуйте снова:")
        return
    # Сохраняем адрес и квартиру из account_status
    await state.update_data(account=account, apartment=account_status[1], address=account_status[2])
    await message.answer(
        f"Лицевой счёт успешно подтверждён!\n"
        f"Адрес: {account_status[2]}\n"
        f"Квартира: {account_status[1]}\n\n"
        "Введите, пожалуйста, показания счётчика холодной воды:"
    )
    await AccountForm.cold_water.set()

# Обработчик ввода показаний холодной воды (лицевой счёт)


@dp.message_handler(state=AccountForm.cold_water)
async def process_account_cold_water(message: types.Message, state: FSMContext):
    await state.update_data(cold_water=message.text)
    await message.answer("Введите показания счётчика электроэнергии:")
    await AccountForm.electr.set()

# Обработчик ввода показаний электроэнергии (лицевой счёт)


@dp.message_handler(state=AccountForm.electr)
async def process_account_electr(message: types.Message, state: FSMContext):
    await state.update_data(electr=message.text.strip())
    data = await state.get_data()
    account = data.get('account')
    address = data.get('address')
    apartment = data.get('apartment')
    cold_water = data.get('cold_water')
    electr = data.get('electr')
    result_message = (
        f"Лицевой счёт: {account}\n"
        f"Адрес: {address}\n"
        f"Квартира: {apartment}\n"
        f"Показания счётчика холодной воды: {cold_water}\n"
        f"Показания счётчика электроэнергии: {electr}\n\n"
        "Проверьте введённые данные. Если всё верно — нажмите «Отправить данные», "
        "иначе — выберите «Заполнить заново»."
    )
    final_keyboard = InlineKeyboardMarkup(row_width=2)
    final_keyboard.add(
        InlineKeyboardButton(text="Отправить данные",
                             callback_data="submit_data_account"),
        InlineKeyboardButton(text="Заполнить заново",
                             callback_data="meter_readings")
    )
    await message.answer(result_message, reply_markup=final_keyboard)

# Обработчик нажатия кнопки "Отправить данные" (лицевой счёт)


@dp.callback_query_handler(lambda c: c.data == 'submit_data_account', state="*")
async def process_submit_account(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    today = date.today().strftime("%d.%m.%Y")
    account = data.get('account', '')
    address = data.get('address', '')
    apartment = data.get('apartment', '')
    cold_water = data.get('cold_water', '').strip()
    electr = data.get('electr')
    if '.' in cold_water:
        cold_water = cold_water.replace('.', ',')
    answer = [today, account, address, apartment, cold_water, electr]
    result = await insert_info_into_sheet(answer)
    if result:
        await bot.send_message(callback_query.from_user.id, "Ваши данные успешно отправлены!")
    else:
        await bot.send_message(callback_query.from_user.id, "Данные не сохранились! Повторите попытку (/menu)!")
    await state.finish()
    await bot.answer_callback_query(callback_query.id)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
