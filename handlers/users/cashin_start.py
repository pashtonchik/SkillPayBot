import requests
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
from loader import dp
from settings import URL_DJANGO
from keyboards.inline.ikb import courier_kb, dispatcher_kb
from keyboards.inline.mainMenu import kb_menu_main
from random import randint

from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton



# @dp.message_handler(commands=['cashin'])
# async def send_cashin_menu(message: types.Message):
#     req = requests.get(url=URL_DJANGO + f'user/{message.chat.id}/')
#     if req.status_code == 200:
#         data = req.json()
#         if data['type'] == 'courier':
#             await message.answer(
#                 f"CASHIN\nРоль: курьер\nБаланс: {data['account_balance']}",
#                 reply_markup=courier_kb,
#                 )
#         elif data['type'] == 'dispatcher':
#             await message.answer(
#                 f"CASHIN\nРоль: диспетчер",
#                 reply_markup=dispatcher_kb,
#             )
#     else:
#         await message.reply(f'Вы не зарегистрированы!')


@dp.message_handler(CommandStart())
async def send_cashin_menu(message: types.Message):

    button_hi = KeyboardButton(text='Ваш баланс: 2000')

    greet_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    greet_kb.add(button_hi)
    await message.reply("1", reply_markup=greet_kb)
#     body = {
#         'tg_id': message.chat.id
#     }
#     r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)
#     if r.status_code == 200:
#         data = r.json()[0]
#         if data['role'] == 'operator':
#             if data['is_instead']:
#                 status = 'На смене'
#             else:
#                 status = 'Не на смене'
#             await message.answer(f"""
# Привет, {message.from_user.first_name}! 
# Статус: {status} """, reply_markup=kb_menu_main)
#         elif data['role'] == 'dispatcher':
#              await message.answer(
#                 f"CASHIN\nРоль: диспетчер",
#                 reply_markup=dispatcher_kb,
#             )
#         elif data['role'] == 'courier':
#             await message.answer(
#                 f"CASHIN\nРоль: курьер\nБаланс: {data['balance_courier']}",
#                 reply_markup=courier_kb,
#                 )
#         else:
#             await message.reply(f'Вы не зарегистрированы!')
#     else:
#         await message.answer(f"""
# У вас нет доступа к боту, обратитесь к администратору.    
# """)
