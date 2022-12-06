import requests
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
from loader import dp
from settings import URL_DJANGO
from keyboards.inline.ikb import courier_kb, dispatcher_kb


@dp.message_handler(commands=['cashin'])
async def send_cashin_menu(message: types.Message):
    req = requests.get(url=URL_DJANGO + f'user/{message.chat.id}/')
    if req.status_code == 200:
        data = req.json()
        if data['type'] == 'courier':
            await message.answer(
                f"CASHIN\nРоль: курьер\nБаланс: {data['account_balance']}",
                reply_markup=courier_kb,
                )
        elif data['type'] == 'dispatcher':
            await message.answer(
                f"CASHIN\nРоль: диспетчер",
                reply_markup=dispatcher_kb,
            )
    else:
        await message.reply(f'Вы не зарегистрированы!')