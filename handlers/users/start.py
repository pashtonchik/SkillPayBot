from cgitb import text
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
import data
from keyboards.inline.mainMenu import kb_menu_main, kb_menu_job, kb_accept_order, kb_accept_payment
from loader import dp
import time
import requests
import json
from aiogram.utils.callback_data import CallbackData


trade_cb = CallbackData("trade", "id", "action")

URL = 'http://194.58.92.160:8000/api/'

@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    body = {
        'tg_id' : message.from_user.id
    }

    r = requests.post(URL + 'get_agent_info/', json=body)

    if (r.status_code == 200):
        data = r.json()[0]
        print(data)
        if (data['is_instead'] == True):
            status = 'На смене'
        else:
            status = 'Не на смене'

        await message.answer(f"""
Привет, {message.from_user.first_name}! 
Статус: {status} """, reply_markup=kb_menu_main)
    else:
        await message.answer(f"""
У вас нет доступа к боту, обратитесь к администратору.    
""")

@dp.callback_query_handler(text='Смена')
async def job(call: types.CallbackQuery):
    print(call.from_user.id)
    await call.message.edit_text('Выберите действие', reply_markup=kb_menu_job)

@dp.callback_query_handler(text='Уйти со смены')
async def startJob(call: types.CallbackQuery):
    
    body = {
        'tg_id' : call.from_user.id
    }

    r = requests.post(URL + 'get_agent_info/', json=body)
    
    data = json.loads(r.text)[0]

    print(data)
    if (r.status_code == 200):
        if (data['is_instead'] == True):
            body = {
                'tg_id': call.from_user.id,
                'options': {
                    'is_working_now': False,
                    'is_instead': False,
                }
            }

            r = requests.post(URL + 'edit_agent_status/', json=body)

            await call.answer("Вы закончили смену! Заявки больше вам не приходят.", show_alert=True)
            
            await call.message.delete()
        else:
            await call.answer("Вы и так уже не на смене!", show_alert=True)
    else:
        await call.message.answer('Не удалось выполнить действие, свяжитесь с тех. поддержкой.')

@dp.callback_query_handler(text='Встать на смену')
async def startJob(call: types.CallbackQuery):
    print("124455")
    body = {
        'tg_id' : call.from_user.id
    }

    r = requests.post(URL + 'get_agent_info/', json=body)
    
    data = json.loads(r.text)[0]
    
    if (r.status_code == 200):
        if (data['is_instead'] == False):
            body = {
                'tg_id': call.from_user.id,
                'options': {
                    'is_working_now': False,
                    'is_instead': True,
                }
            }

            r = requests.post(URL + 'edit_agent_status/', json=body)
            
            if (r.status_code == 200):
                await call.answer("Вы начали смену! Ожидайте заявки.", show_alert=True)
            else:
                await call.answer('Не удалось начать смену, свяжитесь с тех. поддержкой.', show_alert=True)
        else:
            await call.answer("Вы и так уже не на смене!", show_alert=True)


@dp.callback_query_handler(trade_cb.filter(action=['accept_trade']))
async def acceptOrder(call: types.CallbackQuery, callback_data: dict):
    URL_DJANGO = 'http://194.58.92.160:8000/'
    id = callback_data['id']
    get_trade_info = requests.get(f'http://194.58.92.160:8000/api/trade/detail/{id}')
    
    if (get_trade_info.json()['trade']['agent'] == None):
        data = {
            'id' : str(id),
            'agent' : str(call.message.from_user.id)
        }
        set_agent_trade = requests.post(f'http://194.58.92.160:8000/api/update/trade/', json=data)

        get_current_info = requests.get(f'http://194.58.92.160:8000/api/trade/detail/{id}')
        print(set_agent_trade.status_code, set_agent_trade.text)
        if (get_current_info.json()['trade']['agent'] == call.message.from_user.id):
            await call.answer('Вы успешно взяли заявку в работу!')
            await call.message.edit_text(f'''
Переведите {get_current_info.json()['currency_amount']} {get_current_info.json()['currency']}
Комментарий: {get_current_info.json()['details']}
Реквизиты: {get_current_info.json()['counterDetails']}''')
        else:
            await call.answer("Заявка уже в работе", show_alert=True)
            await call.message.delete()
    else:
        await call.answer("Заявка уже в работе", show_alert=True)
        await call.message.delete()
    

@dp.callback_query_handler(text='Я оплатил')
async def isPayment(call: types.CallbackQuery):

    await call.message.answer('Отправьте в чат чек об оплате.')


@dp.message_handler(content_types=['photo'])
async def handle_photos(message: types.Message):
    await message.reply('Принято!')


@dp.callback_query_handler(text='Назад')
async def back(call: types.CallbackQuery):
    await call.message.edit_text('Меню', reply_markup=kb_menu_main)


