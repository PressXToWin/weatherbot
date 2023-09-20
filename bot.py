import math

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from api_requests import request
from database import orm
from settings import settings

bot = Bot(token=settings.bot_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

PAGE_SIZE = 4


class ChoiceCityWeather(StatesGroup):
    waiting_city = State()


class SetUserCity(StatesGroup):
    waiting_city = State()


@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    orm.add_user(message.from_user.id)
    markup = await main_menu()
    text = (f'Привет, {message.from_user.first_name}, '
            'я бот, который расскажет тебе о погоде на сегодня.')
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
    text = (f'Погода в {city}\n'
            f'Температура: {data["temp"]} С\n'
            f'Ощущается как: {data["feels_like"]} C\n'
            f'Скорость ветра: {data["wind_speed"]} м/с\n'
            f'Давление: {data["pressure_mm"]} мм')
    await message.answer(text, reply_markup=markup)


@dp.message_handler(regexp='Меню')
async def start_message(message: types.Message):
    markup = await main_menu()
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
    markup = await main_menu()
    city = await state.get_data()
    data = request.get_weather(city.get('waiting_city'))
    orm.create_report(message.from_user.id, data["temp"], data["feels_like"], data["wind_speed"], data["pressure_mm"],
                      city.get("waiting_city"))
    text = (f'Погода в {city.get("waiting_city")}\n'
            f'Температура: {data["temp"]} С\n'
            f'Ощущается как: {data["feels_like"]} C\n'
            f'Скорость ветра: {data["wind_speed"]} м/с\n'
            f'Давление: {data["pressure_mm"]} мм')
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
    markup = await main_menu()
    text = f'Ваш город {user_data.get("waiting_city")}.'
    await message.answer(text, reply_markup=markup)
    await state.finish()


@dp.message_handler(regexp='История')
async def get_reports(message: types.Message):
    current_page = 1
    reports = orm.get_reports(message.from_user.id)
    total_pages = math.ceil(len(reports) / PAGE_SIZE)
    text = 'История запросов:'
    inline_markup = types.InlineKeyboardMarkup()
    for report in reports[:current_page * PAGE_SIZE]:
        inline_markup.add(
            types.InlineKeyboardButton(
                text=f'{report.city} - {report.date}',
                callback_data=f'report_{report.id}'
            )
        )
    current_page += 1
    inline_markup.row(
        types.InlineKeyboardButton(text=f'{current_page - 1} / {total_pages}', callback_data='None'),
        types.InlineKeyboardButton(text='Вперёд', callback_data=f'next_{current_page}')
    )
    await message.answer(text, reply_markup=inline_markup)


@dp.callback_query_handler(lambda call: 'users' not in call.data)
async def callback_query(call, state: FSMContext):
    query_type = call.data.split('_')[0]
    if query_type == 'delete' and call.data.split('_')[1] == 'report':
        await delete_report(call)
        return
    async with state.proxy() as data:
        data['current_page'] = int(call.data.split('_')[1])
        await state.update_data(current_page=data['current_page'])
        if query_type == 'next':
            await callback_query_history_next(data, call)
        elif query_type == 'prev':
            await callback_query_history_prev(data, call)
        elif query_type == 'report':
            await callback_query_history_report(data, call)
        elif query_type == 'reports':
            await callback_query_history_reports_list(data, call)


async def main_menu():
    markup = types.reply_keyboard.ReplyKeyboardMarkup(
        row_width=2, resize_keyboard=True
    )
    btn1 = types.KeyboardButton('Погода в моём городе')
    btn2 = types.KeyboardButton('Погода в другом месте')
    btn3 = types.KeyboardButton('История')
    btn4 = types.KeyboardButton('Установить свой город')
    markup.add(btn1, btn2, btn3, btn4)
    return markup


@dp.message_handler(lambda message:
                    message.from_user.id in settings.tg_bot_admin
                    and message.text == 'Админ'
                    )
async def admin_panel(message: types.Message):
    markup = types.reply_keyboard.ReplyKeyboardMarkup(
        row_width=2, resize_keyboard=True
    )
    btn1 = types.KeyboardButton('Список пользователей')
    markup.add(btn1)
    text = 'Админ-панель'
    await message.answer(text, reply_markup=markup)


@dp.message_handler(lambda message:
                    message.from_user.id in settings.tg_bot_admin
                    and message.text == 'Список пользователей'
                    )
async def get_all_users(message: types.Message):
    current_page = 1
    users = orm.get_all_users()
    total_pages = math.ceil(len(users) / PAGE_SIZE)
    text = 'Пользователи бота'
    inline_markup = types.InlineKeyboardMarkup()
    for user in users[:current_page * PAGE_SIZE]:
        inline_markup.add(
            types.InlineKeyboardButton(
                text=f'id: {user.id}\n'
                     f'tg_id: {user.tg_id}\n'
                     f'Подключился: {user.connection_date}\n'
                     f'Отчётов: {len(user.reports)}',
                callback_data='None'
            )
        )
    current_page += 1
    inline_markup.row(
        types.InlineKeyboardButton(
            text=f'{current_page-1}/{total_pages}', callback_data='None'
        ),
        types.InlineKeyboardButton(
            text='Вперёд', callback_data=f'next_users_{current_page}'
        )
    )
    await message.answer(text, reply_markup=inline_markup)


@dp.callback_query_handler(lambda call: 'users' in call.data)
async def callback_query(call, state: FSMContext):
    query_type = call.data.split('_')[0]
    async with state.proxy() as data:
        data['current_page'] = int(call.data.split('_')[2])
        await state.update_data(current_page=data['current_page'])
        if query_type == 'next':
            await callback_query_admin_next(data, call)
        if query_type == 'prev':
            await callback_query_admin_prev(data, call)


async def callback_query_admin_next(data, call):
    users = orm.get_all_users()
    total_pages = math.ceil(len(users) / PAGE_SIZE)
    inline_markup = types.InlineKeyboardMarkup()
    if data['current_page'] * PAGE_SIZE >= len(users):
        for user in users[data['current_page'] * PAGE_SIZE - PAGE_SIZE:len(users) + 1]:
            inline_markup.add(
                types.InlineKeyboardButton(
                    text=f'id: {user.id}\n'
                         f'tg_id: {user.tg_id}\n'
                         f'Подключился: {user.connection_date}\n'
                         f'Отчётов: {len(user.reports)}',
                    callback_data='None'
                )
            )
        data['current_page'] -= 1
        inline_markup.row(
            types.InlineKeyboardButton(text='Назад', callback_data=f'prev_users_{data["current_page"]}'),
            types.InlineKeyboardButton(text=f'{data["current_page"] + 1}/{total_pages}', callback_data='None')
        )
        await call.message.edit_text(text='Все мои пользователи:', reply_markup=inline_markup)
        return
    for user in users[data['current_page'] * PAGE_SIZE - PAGE_SIZE:data['current_page'] * PAGE_SIZE]:
        inline_markup.add(
            types.InlineKeyboardButton(
                text=f'id: {user.id}\n'
                     f'tg_id: {user.tg_id}\n'
                     f'Подключился: {user.connection_date}\n'
                     f'Отчётов: {len(user.reports)}',
                callback_data='None'
            )
        )
    data['current_page'] += 1
    inline_markup.row(
        types.InlineKeyboardButton(text='Назад', callback_data=f'prev_users_{data["current_page"] - 2}'),
        types.InlineKeyboardButton(text=f'{data["current_page"] - 1}/{total_pages}', callback_data='None'),
        types.InlineKeyboardButton(text='Вперёд', callback_data=f'next_users_{data["current_page"]}')
    )
    await call.message.edit_text(text='Все мои пользователи:', reply_markup=inline_markup)


async def callback_query_admin_prev(data, call):
    users = orm.get_all_users()
    total_pages = math.ceil(len(users) / PAGE_SIZE)
    inline_markup = types.InlineKeyboardMarkup()
    if data['current_page'] == 1:
        for user in users[0:data['current_page'] * PAGE_SIZE]:
            inline_markup.add(
                types.InlineKeyboardButton(
                    text=f'id: {user.id}\n'
                         f'tg_id: {user.tg_id}\n'
                         f'Подключился: {user.connection_date}\n'
                         f'Отчётов: {len(user.reports)}',
                    callback_data='None'
                )
            )
        data['current_page'] += 1
        inline_markup.row(
            types.InlineKeyboardButton(text=f'{data["current_page"] - 1}/{total_pages}', callback_data='None'),
            types.InlineKeyboardButton(text='Вперёд', callback_data=f'next_users_{data["current_page"]}')
        )
        await call.message.edit_text(text='Все мои пользователи:', reply_markup=inline_markup)
        return
    for user in users[data['current_page'] * PAGE_SIZE - PAGE_SIZE:data['current_page'] * PAGE_SIZE]:
        inline_markup.add(
            types.InlineKeyboardButton(
                text=f'id: {user.id}\n'
                     f'tg_id: {user.tg_id}\n'
                     f'Подключился: {user.connection_date}\n'
                     f'Отчётов: {len(user.reports)}',
                callback_data='None'
            )
        )
    data['current_page'] -= 1
    inline_markup.row(
        types.InlineKeyboardButton(text='Назад', callback_data=f'prev_users_{data["current_page"]}'),
        types.InlineKeyboardButton(text=f'{data["current_page"] + 1}/{total_pages}', callback_data='None'),
        types.InlineKeyboardButton(text='Вперёд', callback_data=f'next_users_{data["current_page"]}'),
    )
    await call.message.edit_text(text='Все мои пользователи:', reply_markup=inline_markup)


async def delete_report(call):
    report_id = int(call.data.split('_')[2])
    current_page = 1
    orm.delete_user_report(report_id)
    reports = orm.get_reports(call.from_user.id)
    total_pages = math.ceil(len(reports) / PAGE_SIZE)
    inline_markup = types.InlineKeyboardMarkup()
    for report in reports[:current_page * PAGE_SIZE]:
        inline_markup.add(types.InlineKeyboardButton(
            text=f'{report.city} {report.date}',
            callback_data=f'report_{report.id}'
        ))
    current_page += 1
    inline_markup.row(
        types.InlineKeyboardButton(text=f'{current_page - 1}/{total_pages}', callback_data='None'),
        types.InlineKeyboardButton(text='Вперёд', callback_data=f'next_{current_page}')
    )
    await call.message.edit_text(text='История запросов:', reply_markup=inline_markup)
    return


async def callback_query_history_next(data, call):
    reports = orm.get_reports(call.from_user.id)
    total_pages = math.ceil(len(reports) / PAGE_SIZE)
    inline_markup = types.InlineKeyboardMarkup()
    if data['current_page'] * PAGE_SIZE >= len(reports):
        for report in reports[data['current_page'] * PAGE_SIZE - PAGE_SIZE:len(reports) + 1]:
            inline_markup.add(types.InlineKeyboardButton(
                text=f'{report.city} {report.date}',
                callback_data=f'report_{report.id}'
            ))
        data['current_page'] -= 1
        inline_markup.row(
            types.InlineKeyboardButton(text='Назад', callback_data=f'prev_{data["current_page"]}'),
            types.InlineKeyboardButton(text=f'{data["current_page"] + 1}/{total_pages}', callback_data='None')
        )
        await call.message.edit_text(text="История запросов:", reply_markup=inline_markup)
        return
    for report in reports[data['current_page'] * PAGE_SIZE - PAGE_SIZE:data['current_page'] * PAGE_SIZE]:
        inline_markup.add(types.InlineKeyboardButton(
            text=f'{report.city} {report.date}',
            callback_data=f'report_{report.id}'
        ))
    data['current_page'] += 1
    inline_markup.row(
        types.InlineKeyboardButton(text='Назад', callback_data=f'prev_{data["current_page"] - 2}'),
        types.InlineKeyboardButton(text=f'{data["current_page"] - 1}/{total_pages}', callback_data='None'),
        types.InlineKeyboardButton(text='Вперёд', callback_data=f'next_{data["current_page"]}')
    )
    await call.message.edit_text(text="История запросов:", reply_markup=inline_markup)


async def callback_query_history_prev(data, call):
    reports = orm.get_reports(call.from_user.id)
    total_pages = math.ceil(len(reports) / PAGE_SIZE)
    inline_markup = types.InlineKeyboardMarkup()
    if data['current_page'] == 1:
        for report in reports[0:data['current_page'] * PAGE_SIZE]:
            inline_markup.add(types.InlineKeyboardButton(
                text=f'{report.city} {report.date}',
                callback_data=f'report_{report.id}'
            ))
        data['current_page'] += 1
        inline_markup.row(
            types.InlineKeyboardButton(text=f'{data["current_page"] - 1}/{total_pages}', callback_data='None'),
            types.InlineKeyboardButton(text='Вперёд', callback_data=f'next_{data["current_page"]}')
        )
        await call.message.edit_text(text="История запросов:", reply_markup=inline_markup)
        return
    for report in reports[data['current_page'] * PAGE_SIZE - PAGE_SIZE:data['current_page'] * PAGE_SIZE]:
        inline_markup.add(types.InlineKeyboardButton(
            text=f'{report.city} {report.date}',
            callback_data=f'report_{report.id}'
        ))
    data['current_page'] -= 1
    inline_markup.row(
        types.InlineKeyboardButton(text='Назад', callback_data=f'prev_{data["current_page"]}'),
        types.InlineKeyboardButton(text=f'{data["current_page"] + 1}/{total_pages}', callback_data='None'),
        types.InlineKeyboardButton(text='Вперёд', callback_data=f'next_{data["current_page"]}'),
    )
    await call.message.edit_text(text="История запросов:", reply_markup=inline_markup)


async def callback_query_history_report(data, call):
    reports = orm.get_reports(call.from_user.id)
    report_id = call.data.split('_')[1]
    inline_markup = types.InlineKeyboardMarkup()
    for report in reports:
        if report.id == int(report_id):
            inline_markup.add(
                types.InlineKeyboardButton(text='Назад', callback_data=f'reports_{data["current_page"]}'),
                types.InlineKeyboardButton(text='Удалить зарос', callback_data=f'delete_report_{report_id}')
            )
            await call.message.edit_text(
                text=f'Данные по запросу\n'
                     f'Город:{report.city}\n'
                     f'Температура:{report.temp}\n'
                     f'Ощущается как:{report.feels_like}\n'
                     f'Скорость ветра:{report.wind_speed}\n'
                     f'Давление:{report.pressure_mm}',
                reply_markup=inline_markup
            )
            break


async def callback_query_history_reports_list(data, call):
    reports = orm.get_reports(call.from_user.id)
    total_pages = math.ceil(len(reports) / PAGE_SIZE)
    inline_markup = types.InlineKeyboardMarkup()
    data['current_page'] = 1
    for report in reports[:data['current_page'] * PAGE_SIZE]:
        inline_markup.add(types.InlineKeyboardButton(
            text=f'{report.city} {report.date}',
            callback_data=f'report_{report.id}'
        ))
    data['current_page'] += 1
    inline_markup.row(
        types.InlineKeyboardButton(text=f'{data["current_page"] - 1}/{total_pages}', callback_data='None'),
        types.InlineKeyboardButton(text='Вперёд', callback_data=f'next_{data["current_page"]}')
    )
    await call.message.edit_text(text='История запросов:', reply_markup=inline_markup)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
