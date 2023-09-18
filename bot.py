from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import math

from settings import bot_config
from api_requests import request
from database import orm

bot = Bot(token=bot_config.bot_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class ChoiceCityWeather(StatesGroup):
    waiting_city = State()


class SetUserCity(StatesGroup):
    waiting_city = State()


@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    orm.add_user(message.from_user.id)
    markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Погода в моём городе')
    btn2 = types.KeyboardButton('Погода в другом месте')
    btn3 = types.KeyboardButton('История')
    btn4 = types.KeyboardButton('Установить свой город')
    markup.add(btn1, btn2, btn3, btn4)
    text = f'Привет, {message.from_user.first_name}, я бот, который расскажет тебе о погоде на сегодня.'
    await message.answer(text, reply_markup=markup)


@dp.message_handler(regexp='Погода в моём городе')
async def start_message(message: types.Message):
    markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Меню')
    markup.add(btn1)
    city = orm.get_user_city(message.from_user.id)
    if city is None:
        text = 'Пожалуйста установите свой город'
        markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btn1 = types.KeyboardButton('Установить свой город')
        btn2 = types.KeyboardButton('Меню')
        markup.add(btn1, btn2)
        await message.answer(text, reply_markup=markup)
        return
    data = request.get_weather(city)
    orm.create_report(message.from_user.id, data["temp"], data["feels_like"], data["wind_speed"], data["pressure_mm"],
                      city)
    text = f'Погода в {city}\nТемпература: {data["temp"]} С\nОщущается как: {data["feels_like"]} C\nСкорость ветра: {data["wind_speed"]} м/с\nДавление: {data["pressure_mm"]} мм'
    await message.answer(text, reply_markup=markup)


@dp.message_handler(regexp='Меню')
async def start_message(message: types.Message):
    markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Погода в моём городе')
    btn2 = types.KeyboardButton('Погода в другом месте')
    btn3 = types.KeyboardButton('История')
    btn4 = types.KeyboardButton('Установить свой город')
    markup.add(btn1, btn2, btn3, btn4)
    text = f'Привет, {message.from_user.first_name}, я бот, который расскажет тебе о погоде на сегодня.'
    await message.answer(text, reply_markup=markup)


@dp.message_handler(regexp='Погода в другом месте')
async def city_start(message: types.Message):
    markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Меню')
    markup.add(btn1)
    text = 'Введите название города'
    await message.answer(text, reply_markup=markup)
    await ChoiceCityWeather.waiting_city.set()


@dp.message_handler(state=ChoiceCityWeather.waiting_city)
async def city_chosen(message: types.Message, state: FSMContext):
    if message.text == 'Меню':
        await start_message(message)
        await state.finish()
        return
    await state.update_data(waiting_city=message.text)
    markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Погода в моём городе')
    btn2 = types.KeyboardButton('Погода в другом месте')
    btn3 = types.KeyboardButton('История')
    btn4 = types.KeyboardButton('Установить свой город')
    markup.add(btn1, btn2, btn3, btn4)
    city = await state.get_data()
    data = request.get_weather(city.get('waiting_city'))
    orm.create_report(message.from_user.id, data["temp"], data["feels_like"], data["wind_speed"], data["pressure_mm"],
                      city.get("waiting_city"))
    text = f'Погода в {city.get("waiting_city")}\nТемпература: {data["temp"]} С\nОщущается как: {data["feels_like"]} C\nСкорость ветра: {data["wind_speed"]} м/с\nДавление: {data["pressure_mm"]} мм'
    await message.answer(text, reply_markup=markup)
    await state.finish()


@dp.message_handler(regexp='Установить свой город')
async def city_start(message: types.Message):
    markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Меню')
    markup.add(btn1)
    text = 'Из какого вы города?'
    await message.answer(text, reply_markup=markup)
    await SetUserCity.waiting_city.set()


@dp.message_handler(state=SetUserCity.waiting_city)
async def city_chosen(message: types.Message, state: FSMContext):
    if message.text == 'Меню':
        await start_message(message)
        await state.finish()
        return
    await state.update_data(waiting_city=message.text)
    user_data = await state.get_data()
    orm.set_user_city(message.from_user.id, user_data.get('waiting_city'))
    markup = types.reply_keyboard.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Погода в моём городе')
    btn2 = types.KeyboardButton('Погода в другом месте')
    btn3 = types.KeyboardButton('История')
    btn4 = types.KeyboardButton('Установить свой город')
    markup.add(btn1, btn2, btn3, btn4)
    text = f'Ваш город {user_data.get("waiting_city")}.'
    await message.answer(text, reply_markup=markup)
    await state.finish()


@dp.message_handler(regexp='История')
async def get_reports(message: types.Message):
    current_page = 1
    reports = orm.get_reports(message.from_user.id)
    total_pages = math.ceil(len(reports) / 4)
    text = 'История запросов:'
    inline_markup = types.InlineKeyboardMarkup()
    for report in reports[:current_page * 4]:
        inline_markup.add(
            types.InlineKeyboardButton(
                text=f'{report.city} - {report.date.day}.{report.date.month}.{report.date.year}',
                callback_data=f'report_{report.id}'
            )
        )
    current_page += 1
    inline_markup.row(
        types.InlineKeyboardButton(text=f'{current_page - 1} / {total_pages}', callback_data='None'),
        types.InlineKeyboardButton(text='Вперёд', callback_data=f'next_{current_page}')
    )
    await message.answer(text, reply_markup=inline_markup)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
