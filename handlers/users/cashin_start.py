import requests
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
from loader import dp
from settings import URL_DJANGO
from keyboards.inline.ikb import courier_kb, dispatcher_kb
from keyboards.inline.mainMenu import kb_menu_main
from random import randint
from loader import bot

from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton

def update_keyboard(balance, smena):
    button_balance = KeyboardButton(text=f'Ваш баланс: {balance}')
    button_smena = KeyboardButton(text=smena)
    button_settings = KeyboardButton(text='Настройки')
    balance_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    balance_kb.add(button_balance)
    return balance_kb


@dp.message_handler(CommandStart())
async def send_cashin_menu(message: types.Message):

    body = {
        'tg_id': message.chat.id
    }
    r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)
    if r.status_code == 200:
        data = r.json()[0]
        if data['role'] == 'operator':
            if data['is_instead']:
                status = 'На смене'
            else:
                status = 'Не на смене'
            await message.answer(f"""
Привет, {message.from_user.first_name}! 
Статус: {status} """, reply_markup=update_keyboard)
            # msg = await message.answer("Обновление баланса🆙", reply_markup=update_balance(data['income_operator']))
            # await bot.delete_message(message.chat.id, msg.message_id)
        elif data['role'] == 'dispatcher':
             await message.answer(
                f"CASHIN\nРоль: диспетчер",
                reply_markup=dispatcher_kb,
            )
        elif data['role'] == 'courier':
            await message.answer(
                f"CASHIN\nРоль: курьер\nБаланс: {data['balance_courier']}",
                reply_markup=courier_kb,
                )
        else:
            await message.reply(f'Вы не зарегистрированы!')
    else:
        await message.answer(f"""
У вас нет доступа к боту, обратитесь к администратору.    
""")
