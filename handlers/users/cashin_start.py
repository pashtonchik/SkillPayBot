

import requests
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
from loader import dp
from settings import URL_DJANGO
from keyboards.inline.ikb import courier_kb, dispatcher_kb, cancel_cb
from keyboards.inline.mainMenu import kb_menu_main
from random import randint
from loader import bot
from states.operator_states import OperatorCheckBalance
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.storage import FSMContext
from aiogram.utils.exceptions import MessageToDeleteNotFound

def update_keyboard(balance, smena):
    button_balance = KeyboardButton(text=f'Ваш баланс: {balance}')
    button_smena = KeyboardButton(text=smena)
    button_settings = KeyboardButton(text='Настройки')
    balance_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    balance_kb.add(button_balance)
    return balance_kb


@dp.callback_query_handler(text='ccancel', state='*')
async def ccansel(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text('Операция отменена')
    if await state.get_state()!= 'OperatorCheckBalance:input_balance': 
        await send_cashin_menu(callback_query.message, state)
    await state.finish()


@dp.message_handler(CommandStart())
async def send_cashin_menu(message: types.Message, state: FSMContext):

    body = {
        'tg_id': message.chat.id
    }
    r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)
    if r.status_code == 200:
        data = r.json()[0]
        if data['role'] == 'operator':
            if data['is_instead']:
                status = 'Закончить смену'
            else:
                status = 'Начать смену'

            await message.answer(f"""
Привет, {message.from_user.first_name}! 
""", reply_markup=update_keyboard(data['income_operator'], status))
                # msg = await message.answer(
                #     f'Привет, {message.from_user.first_name}!\nПожалуйста введите баланс по текущей карте, для выхода на смену',
                #     reply_markup=cancel_cb)
                # await state.set_data({'msg': msg.message_id})
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
