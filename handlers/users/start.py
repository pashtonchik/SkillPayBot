import asyncio
from cgitb import text
from email import header
from wave import Wave_write
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
from keyboards.inline.mainMenu import kb_menu_main, kb_menu_job, kb_accept_order, kb_accept_payment
from loader import dp
import time
import requests
import json
from aiogram.utils.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime
import time
import random
from states.activity.activity_state import Activity
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import state

import requests
from jose import jws
from jose.constants import ALGORITHMS

from loader import bot

trade_cb = CallbackData("trade", "type", "id", "action")

URL = 'http://194.58.92.160:8000/api/'

async def confirm_payment(id, message, state):
    while 1:
        try:
            req = requests.get(URL + f'api/trade/detail/{id}')
            if (req.status_code == 200):
                trade_info = req.json()
                if (trade_info['trade']['status'] == 'confirm_payment'):
                    body = {
                        'tg_id': message.from_user.id,
                        'options': {
                            'is_working_now': False,
                            'is_instead': True,
                        }
                    }

                    change_status_agent = requests.post(URL + 'edit_agent_status/', json=body)

                    if (change_status_agent.status_code == 200):
                        await message.reply('Чек принят! Сделка завершена, ожидайте следующую.')
                    else:
                        await message.answer('Произошла ошибка, свяжитесь с админом.')

                    await state.finish()
                    break
            await asyncio.sleep(1)
            
        except Exception as e:
            print(e)
            continue
    
def authorization(key, email_bz):
    dt = datetime.datetime.now()
    ts = time.mktime(dt.timetuple())
    claims = {
        "email": email_bz,
        "aud": "usr",
        "iat": int(ts),
        "jti": hex(random.getrandbits(64))
    }
    token = jws.sign(claims, key, headers={"kid": "1"}, algorithm=ALGORITHMS.ES256)
    return {'Authorization': "Bearer " + token}


@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    body = {
        'tg_id': message.from_user.id
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
        'tg_id': call.from_user.id
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
    body = {
        'tg_id': call.from_user.id
    }

    r = requests.post(URL + 'get_agent_info/', json=body)

    data = json.loads(r.text)[0]

    if r.status_code == 200:
        if not data['is_instead']:
            body = {
                'tg_id': call.from_user.id,
                'options': {
                    'is_working_now': False,
                    'is_instead': True,
                }
            }

            r = requests.post(URL + 'edit_agent_status/', json=body)

            if r.status_code == 200:
                await call.answer("Вы начали смену! Ожидайте заявки.", show_alert=True)

#                 active_trades = requests.get(URL + 'trades/active/')
#                 if active_trades.status_code == 200:
#                     active_trades = active_trades.json()
#                     for trade in active_trades:
#                         req_trade_info = requests.get(URL + f'trade/detail/{trade}')
#                         trade_info = req_trade_info.json()
#                         await bot.send_message(453442665, f'''
# Новая сделка! Покупка {trade_info['cryptocurrency']} за {trade_info['trade']['currency']}
# Сумма: {trade_info['trade']['currency_amount']} {trade_info['trade']['currency']}
# ''', reply_markup=kb_accept_order)
            else:
                await call.answer('Не удалось начать смену, свяжитесь с тех. поддержкой.', show_alert=True)
        else:
            await call.answer("Вы и так уже на смене!", show_alert=True)


@dp.callback_query_handler(trade_cb.filter(action=['accept_trade']))
async def acceptOrder(call: types.CallbackQuery, callback_data: dict, state=FSMContext):
    URL_DJANGO = 'http://194.58.92.160:8000/'
    print('accept')
    print(callback_data)
    if (callback_data['type'] == 'BZ'):
        id = callback_data['id']
        get_trade_info = requests.get(URL_DJANGO + f'api/trade/detail/{id}')
        if (get_trade_info.json()['trade']['agent'] == None or str(get_trade_info.json()['trade']['agent']) == str(
                call.from_user.id)):
            data = {
                'id': str(id),
                'agent': str(call.from_user.id)
            }
            set_agent_trade = requests.post(URL_DJANGO + f'api/update/trade/', json=data)

            get_current_info = requests.get(URL_DJANGO + f'api/trade/detail/{id}')

            if (get_current_info.json()['trade']['agent'] == str(call.from_user.id)):
                kb_accept_payment = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(text='Оплатил', callback_data=trade_cb.new(id=id, type='BZ', action='accept_payment'))
                        ]
                    ]
                )

                headers = authorization(get_current_info.json()['user']['key'], get_current_info.json()['user']['email'])

                proxy = get_current_info.json()['user']['proxy']

                data = {
                    'type': 'confirm-trade'
                }

                url = f'https://bitzlato.com/api/p2p/trade/{id}'
                try:
                    req_change_type = requests.post(url, headers=headers, proxies=proxy, json=data)

                    if (req_change_type.status_code == 200):
                        await call.answer('Вы успешно взяли заявку в работу!', show_alert=True)
                        await call.message.edit_text(f'''
        Переведите {get_current_info.json()['trade']['currency_amount']} {get_current_info.json()['trade']['currency']}
        Комментарий: {get_current_info.json()['trade']['details']}
        Реквизиты: {get_current_info.json()['trade']['counterDetails']} {get_current_info.json()['paymethod_description']}

        После перевода нажмите кнопку "Оплатил"
        ''', reply_markup=kb_accept_payment)
                        await Activity.acceptOrder.set()
                    else:
                        await call.answer('Произошла ошибка, нажмите кнопку заново.')
                except Exception as e:
                    await call.answer('Произошла ошибка, нажмите кнопку заново.')

            else:
                await call.answer("Заявка уже в работе", show_alert=True)
                await call.message.delete()
        else:
            await call.answer("Заявка уже в работе", show_alert=True)
            await call.message.delete()
    elif callback_data['type'] == 'googleSheets':
        print(1)
        id = callback_data['id']
        get_pay_info = requests.get(URL_DJANGO + f'api/pay/detail/{id}/')
        print(get_pay_info.status_code)
        if (get_pay_info.json()['pay']['agent'] == None or str(get_pay_info.json()['pay']['agent']['tg_id']) == str(
                call.from_user.id)):
            data = {
                'id': str(id),
                'agent': str(call.from_user.id)
            }
            set_agent_trade = requests.post(URL_DJANGO + f'api/update/pay/', json=data)

            get_current_info = requests.get(URL_DJANGO + f'api/pay/detail/{id}/')

            print(get_current_info.json())
            print(call.from_user.id)
            if (str(get_current_info.json()['pay']['agent']['tg_id']) == str(call.from_user.id)):
                kb_accept_payment = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(text='Оплатил', callback_data=trade_cb.new(id=id, type='googleSheets' , action='accept_payment'))
                        ]
                    ]
                )
                try:
                    await call.answer('Вы успешно взяли заявку в работу!', show_alert=True)
                    await call.message.edit_text(f'''
            Переведите {get_current_info.json()['pay']['amount']} RUB
            Реквизиты: {get_current_info.json()['pay']['card_number']} {get_current_info.json()['paymethod_description']}

            После перевода нажмите кнопку "Оплатил"
            ''', reply_markup=kb_accept_payment)
                    await Activity.acceptOrder.set()
                except Exception as e:
                    await call.answer('Произошла ошибка, нажмите кнопку заново.')

            else:
                await call.answer("Заявка уже в работе", show_alert=True)
                await call.message.delete()

        else:
            await call.answer('Заявка уже в работе.', show_alert=True)
            await call.message.delete()

@dp.callback_query_handler(trade_cb.filter(action=['accept_payment']), state=Activity.acceptOrder)
async def acceptPayment(call: types.CallbackQuery, callback_data=dict, state=FSMContext):
    id = str(callback_data['id'])
    URL_DJANGO = 'http://194.58.92.160:8000/'

    if (callback_data['type'] == 'BZ'):

        get_current_info = requests.get(URL_DJANGO + f'api/trade/detail/{id}')

        headers = authorization(get_current_info.json()['user']['key'], get_current_info.json()['user']['email'])

        proxy = get_current_info.json()['user']['proxy']

        data = {
            'type': 'payment'
        }

        url = f'https://bitzlato.bz/api/p2p/trade/{id}'
        try:

            req_change_type = requests.post(url, headers=headers, proxies=proxy, json=data)

            if (req_change_type.status_code == 200):
                await call.message.answer('Пришлите чек о переводе в виде изображения.')
                await state.update_data(id=id, type='BZ')
                await Activity.acceptPayment.set()
            else:
                print(f'''ELSE:::   req_text: {req_change_type.text} {req_change_type.status_code}''')
                await call.message.answer('Произошла ошибка, нажмите кнопку заново.')
        except Exception as e:
            print(
                f'''EXCEPT:::  Klass: {type(e)}, text: {e}, req_text: {req_change_type.text} {req_change_type.status_code}''')
            await call.message.answer('Произошла ошибка, нажмите кнопку заново.')
    elif callback_data['type'] == 'googleSheets' :
        get_current_info = requests.get(URL_DJANGO + f'api/pay/detail/{id}/')
        await call.message.answer('Пришлите чек о переводе в виде изображения.')
        await state.update_data(id=id, type='googleSheets')
        await Activity.acceptPayment.set()


@dp.message_handler(content_types=['photo'], state=Activity.acceptPayment)
async def getPhoto(message: types.Message, state=FSMContext):
    URL_DJANGO = 'http://194.58.92.160:8000/'
    data = await state.get_data()
    id = data['id']
    if data['type'] == 'BZ' :
        id = data['id']

        get_trade_detail = requests.get(URL_DJANGO + f'api/trade/detail/{id}')
        key = get_trade_detail.json()['user']['key']
        proxy = get_trade_detail.json()['user']['proxy']
        email = get_trade_detail.json()['user']['email']

        fileName = f'/root/prod/SkillPay-Django/tgchecks/{id}_{message.from_user.id}.png'
        await message.photo[-1].download(fileName)
        send_message = f'https://bitzlato.bz/api/p2p/trade/{id}/chat/'
        headers = authorization(key, email)
        data_message = {
            'message': 'Оплатил.',
            'payload': {
                'message': 'string'
            }
        }
        send_message_req = requests.post(send_message, headers=headers, proxies=proxy, json=data_message)
        url = f'https://bitzlato.bz/api/p2p/trade/{id}/chat/sendfile'

        data = {
            'mime_type': 'image/png',
            'name': 'Check.png'
        }
        files = {'file': open(fileName, 'rb')}

        headers = authorization(key, email)

        r = requests.post(url, headers=headers, proxies=proxy, files=files)

        asyncio.create_task(confirm_payment(id=id, message=message, state=state))
    elif data['type'] == 'googleSheets':
        fileName = f'/root/prod/SkillPay-Django/tgchecks/{id}_{message.from_user.id}.png'
        await message.photo[-1].download(fileName)
        data = {
            'id' : id,
            'cheque' : f'tgchecks/{id}_{message.from_user.id}.png'
        }
        upload = requests.post(URL_DJANGO + 'api/update/pay/', json=data)
        if upload.status_code == 200:
            await message.answer('Чек принят! Сделка завершена.')
            await state.finish()
        else:
            await message.answer('Произошла ошибка при скачивании фото. Свяжитесь с админом.')
            await state.finish()


@dp.callback_query_handler(text='Назад')
async def back(call: types.CallbackQuery):
    await call.message.edit_text('Меню', reply_markup=kb_menu_main)
