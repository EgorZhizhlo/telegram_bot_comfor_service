import os
import logging
from datetime import date
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from save_into_google_sheet import insert_info_into_sheet


# Получаем токен бота из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# Определяем состояния формы адреса
class AddressForm(StatesGroup):
    street = State()
    house = State()
    apartment = State()
    reading = State()


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
    # Для callback_data используем префикс, чтобы потом легко отфильтровать выбранную улицу
    street_keyboard.add(InlineKeyboardButton(text=street, callback_data=f"street_{street}"))
street_keyboard.add(types.InlineKeyboardButton(
            text="Назад", callback_data="meter_readings"))

# Обработчик команд /start и /menu


@dp.message_handler(commands=['start', 'menu'], state="*")
async def send_welcome(message: types.Message, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(
            text="Передать показания", callback_data="meter_readings"),
        types.InlineKeyboardButton(text="Официальный сайт", url="https://komfort67.com/index.php")
    )
    message_text = """
    👋 Добро пожаловать!  
Выберите нужный раздел для удобного управления услугами:  
Передать показания счётчика холодной воды 📊❄️  
Официальный сайт Управляющей компании ООО Комфорт-сервис ✅  
    """
    await message.answer(message_text, reply_markup=keyboard, parse_mode="markdown")
    await state.finish()  # Завершаем работу FSM


# Обработчик кнопки "Передать показания счётчиков"


@dp.callback_query_handler(lambda c: c.data == 'meter_readings', state="*")
async def process_meter_readings(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("По адресу", callback_data="by_address"),
        types.InlineKeyboardButton(
            "По № лицевого счета", callback_data="by_account"),
    )
    await bot.send_message(callback_query.from_user.id, "Выберите способ передачи показаний:\n(Для выхода в меню воспользуйтесь командой /menu)", reply_markup=keyboard)
    await bot.answer_callback_query(callback_query.id)
    await state.finish()  # Завершаем работу FSM

# Обработчик кнопки "По адресу"


@dp.callback_query_handler(lambda c: c.data == 'by_address', state="*")
async def process_by_address(callback_query: types.CallbackQuery):

    message_text = """
Вы выбрали передать показания по адресу.
Выберите улицу:
    """

    await bot.send_message(
        callback_query.from_user.id,
        message_text,
        reply_markup=street_keyboard,
        parse_mode="markdown"
    )
    await bot.answer_callback_query(callback_query.id)


# Обработчик выбора улицы
@dp.callback_query_handler(lambda c: c.data.startswith("street_"), state="*")
async def process_street(callback_query: types.CallbackQuery, state: FSMContext):
    street = callback_query.data.replace("street_", "")
    # Сохраняем выбранную улицу
    await state.update_data(street=street)
    await bot.send_message(callback_query.from_user.id, "Введите № дома:")
    await AddressForm.house.set()
    await bot.answer_callback_query(callback_query.id)


# Обработчик ввода номера дома
@dp.message_handler(state=AddressForm.house)
async def process_house(message: types.Message, state: FSMContext):
    await state.update_data(house=message.text)
    await message.answer("Введите № квартиры:")
    await AddressForm.apartment.set()


# Обработчик ввода номера квартиры
@dp.message_handler(state=AddressForm.apartment)
async def process_apartment(message: types.Message, state: FSMContext):
    await state.update_data(apartment=message.text)
    await message.answer("Введите показания счётчика холодной воды:")
    await AddressForm.reading.set()


@dp.message_handler(state=AddressForm.reading)
async def process_reading(message: types.Message, state: FSMContext):
    await state.update_data(reading=message.text)
    # Получаем все данные, сохранённые в FSM
    data = await state.get_data()
    street = data.get('street', '').strip()
    house = data.get('house', '').strip()
    apartment = data.get('apartment', '').strip()
    reading = data.get('reading', '').strip()
    result_message = (
        f"Адрес: {street}\n"
        f"Дом: {house}\n"
        f"Квартира: Кв. {apartment}\n"
        f"Показания счётчика холодной воды: {reading}"
    )
    # Создаём клавиатуру с двумя кнопками:
    final_keyboard = InlineKeyboardMarkup(row_width=2)
    final_keyboard.add(
        InlineKeyboardButton(text="Отправить данные", callback_data="submit_data"),
        InlineKeyboardButton(text="Заполнить заново", callback_data="meter_readings")
    )
    await message.answer(result_message, reply_markup=final_keyboard)


# Обработчик нажатия кнопки "Отправить данные"
@dp.callback_query_handler(lambda c: c.data == 'submit_data', state="*")
async def process_submit(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    today = date.today().strftime("%d.%m.%Y")
    street = data.get('street', '').strip()
    house = data.get('house', '').strip()
    apartment = data.get('apartment', '').strip()
    reading = data.get('reading', '').strip()
    if reading.count('.') > 0:
        reading = reading.replace('.', ',')
    answer = [today, None, street + ", дом № " + house, "Кв. " + apartment, reading]
    result = await insert_info_into_sheet(answer)
    if result:
        await bot.send_message(callback_query.from_user.id, "Ваши данные успешно отправлены!")
        await state.finish()  # Завершаем работу FSM
        await bot.answer_callback_query(callback_query.id)
    else:
        await bot.send_message(callback_query.from_user.id, "Данные не сохранились! Повторите попытку(/menu)!")
        await state.finish()  # Завершаем работу FSM
        await bot.answer_callback_query(callback_query.id)


# Обработчик кнопки "По № лицевого счета"


@dp.callback_query_handler(lambda c: c.data == 'by_account')
async def process_by_account(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Вы выбрали передать показания по лицевому счету")
    await bot.answer_callback_query(callback_query.id)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
