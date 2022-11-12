import asyncio
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart

from garantexAPI.trades import close_trade
from keyboards.inline.mainMenu import kb_menu_main, kb_menu_job, kb_accept_order
from keyboards.inline.mainMenu import kb_menu_main, kb_menu_job
from loader import dp
import time
import json
from aiogram.utils.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime
import time
import random
from settings import URL_DJANGO, cheques_base
from states.activity.activity_state import Activity
from aiogram.dispatcher import FSMContext

import requests
from jose import jws
from jose.constants import ALGORITHMS
from loader import bot
from garantexAPI.auth import *
from garantexAPI.chat import *
from garantexAPI.trades import *
from skillpaybot import select_message_from_database, delete_from_database
trade_cb = CallbackData("trade", "type", "id", "action")


def create_accept_kb(trade_id, trade_type):
    kb_accept_payment = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='Оплатил',
                                     callback_data=trade_cb.new(id=trade_id, type=trade_type,
                                                                action='accept_payment'))
            ]
        ]
    )
    return kb_accept_payment


def create_accept_cancel_kb(trade_id, trade_type):
    kb_accept_payment = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='Отменить сделку',
                                     callback_data=trade_cb.new(id=trade_id, type=trade_type,
                                                                action='cancel_payment'))
            ],
        ]
    )
    return kb_accept_payment


def create_yes_no_kb(trade_id, trade_type):
    kb_yes_no = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='Другая причина',
                                     callback_data=trade_cb.new(id=trade_id, type=trade_type,
                                                                action='other_reason'))
            ],
            [
                InlineKeyboardButton(text='Вернуться к сделке',
                                     callback_data=trade_cb.new(id=trade_id, type=trade_type,
                                                                action='back_to_trade'))
            ],
            [
                InlineKeyboardButton(text='Не хватает баланса',
                                     callback_data=trade_cb.new(id=trade_id, type=trade_type,
                                                                action='no_balance'))
            ],
        ]
    )
    return kb_yes_no


async def confirm_payment(id, message, state):
    while 1:
        try:
            req = requests.get(URL_DJANGO + f'trade/detail/{id}')
            if req.status_code == 200:
                trade_info = req.json()
                if trade_info['trade']['status'] == 'confirm_payment':
                    body = {
                        'tg_id': message.from_user.id,
                        'options': {
                            'is_working_now': False,
                            'is_instead': True,
                        }
                    }

                    change_status_agent = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)

                    if change_status_agent.status_code == 200:
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
    r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)
    if r.status_code == 200:
        data = r.json()[0]
        if data['is_instead']:
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
    await call.message.edit_text('Выберите действие', reply_markup=kb_menu_job)


@dp.callback_query_handler(text='Уйти со смены')
async def start_job(call: types.CallbackQuery):
    body = {
        'tg_id': call.from_user.id
    }

    r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)

    data = json.loads(r.text)[0]

    messages = select_message_from_database(call.from_user.id)
    trade_mas = []
    for msg, trade_id_db, in messages:
        trade_mas.append(trade_id_db)
        try:
            await bot.delete_message(call.from_user.id, msg)
        except Exception as e:
            print(e)
        delete_from_database(call.from_user.id, msg, trade_id_db, 'kf')
    res_delete = {
                'id' : trade_mas,
                'tg_id' : call.from_user.id
            }
    try:
        req = requests.post(URL_DJANGO + 'delete/kf/recipient/', json=res_delete)
    except Exception as e:
        print(e)
    if r.status_code == 200:
        if data['is_instead']:
            body = {
                'tg_id': call.from_user.id,
                'options': {
                    'is_working_now': False,
                    'is_instead': False,
                }
            }

            r = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)

            await call.answer("Вы закончили смену! Заявки больше вам не приходят.", show_alert=True)

            await call.message.delete()
        else:
            await call.answer("Вы и так уже не на смене!", show_alert=True)
    else:
        await call.message.answer('Не удалось выполнить действие, свяжитесь с тех. поддержкой.')


@dp.callback_query_handler(text='Встать на смену')
async def start_job(call: types.CallbackQuery):
    body = {
        'tg_id': call.from_user.id
    }

    r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)

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

            r = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)

            if r.status_code == 200:
                await call.answer("Вы начали смену! Ожидайте заявки.", show_alert=True)
            else:
                await call.answer('Не удалось начать смену, свяжитесь с тех. поддержкой.', show_alert=True)
        else:
            await call.answer("Вы и так уже на смене!", show_alert=True)


@dp.callback_query_handler(trade_cb.filter(action=['accept_trade']))
async def accept_order(call: types.CallbackQuery, callback_data: dict, state=FSMContext):

    trade_id = callback_data['id']
    print(callback_data)
    data = {
        'id': str(trade_id),
        'agent': str(call.from_user.id)
    }
    kb_accept_cancel_payment = create_accept_cancel_kb(trade_id, callback_data['type'])
    print(kb_accept_cancel_payment)
    
    if callback_data['type'] == 'BZ':
        url_type = 'trade'
        trade_type = 'trade'
    
    elif callback_data['type'] == 'googleSheets':
        url_type = 'pay'
        trade_type = 'pay'

    elif callback_data['type'] == 'kf':
        url_type = 'kf'
        trade_type = 'kftrade'
        
    # _______________GAANTEX__________________________GATANTEX________________________GATANTEX________________________
    elif callback_data['type'] == 'garantex':
        url_type = 'gar'
        trade_type = 'gar_trade'


    if (url_type in ['gar', 'pay', 'kf']):
        
        get_pay_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')

        if (not get_pay_info.json()[trade_type]['agent'] or str(get_pay_info.json()[trade_type]['agent']) == str(
                call.from_user.id)) and \
                get_pay_info.json()[trade_type]['status'] != 'closed':

            set_agent_trade = requests.post(URL_DJANGO + f'update/{url_type}/trade/', json=data)

            get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')

            if str(get_current_info.json()[trade_type]['agent']) == str(call.from_user.id):
                try:
                    messages = select_message_from_database(call.from_user.id)
                    trade_mas = []
                    for msg, trade_id_db,   in messages:
                        if (msg != call.message.message_id):
                            trade_mas.append(trade_id_db)
                            try:
                                await bot.delete_message(call.from_user.id, msg)
                            except Exception as e:
                                print(e)
                            delete_from_database(call.from_user.id, msg, trade_id_db, url_type)
                    res_delete = {
                                'id' : trade_mas,
                                'tg_id' : call.from_user.id
                            }
                    try:
                        req = requests.post(URL_DJANGO + f'delete/{url_type}/recipient/', json=res_delete)
                    except Exception as e:
                        print(e)
                    await call.answer('Вы успешно взяли заявку в работу!', show_alert=True)
                    print(1111111111)
                    # await call.message.edit_text('1111')
                    print(get_current_info.json()[trade_type])
                    await call.message.edit_text(f'''

Заявка: {url_type.upper()} — {trade_id}
Инструмент: {get_current_info.json()['paymethod_description']}
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
Адресат: `{get_current_info.json()[trade_type]['card_number']}`

Статус: *Ожидаем оплату и предоставление чека.*

    ''', reply_markup=kb_accept_cancel_payment, parse_mode='Markdown')
                    if (url_type == 'kf'):
                        type = 'kf'
                    elif (url_type == 'gar'):
                        type = 'garantex'
                    elif (url_type == 'pay'):
                        type = 'googleSheets'
                    await state.update_data(id=callback_data['id'], type=type, message_id=msg.message_id)
                    await Activity.acceptPayment.set()
                except Exception as e:
                    await call.answer('Произошла ошибка, нажмите кнопку заново.')

            else:
                await call.answer("Заявка уже в работе", show_alert=True)
                await call.message.delete()
        else:
            await call.answer('Заявка уже в работе.', show_alert=True)
            await call.message.delete()
    
    else:
        get_trade_info = requests.get(URL_DJANGO + f'trade/detail/{trade_id}/')
        if not get_trade_info.json()['trade']['agent'] or str(get_trade_info.json()['trade']['agent']) == str(
                call.from_user.id):

            set_agent_trade = requests.post(URL_DJANGO + f'update/trade/', json=data)

            get_current_info = requests.get(URL_DJANGO + f'trade/detail/{trade_id}/')
            if get_current_info.json()['trade']['agent'] == str(call.from_user.id):
                headers = authorization(
                    get_current_info.json()['user']['key'],
                    get_current_info.json()['user']['email']
                )

                proxy = get_current_info.json()['user']['proxy']

                data = {
                    'type': 'confirm-trade'
                }

                url = f'https://bitzlato.com/api/p2p/trade/{trade_id}/'
                try:
                    req_change_type = requests.post(url, headers=headers, proxies=proxy, json=data)

                    if req_change_type.status_code == 200:
                        await call.answer('Вы успешно взяли заявку в работу!', show_alert=True)
                        await call.message.edit_text(f'''
Переведите {get_current_info.json()['trade']['currency_amount']} {get_current_info.json()['trade']['currency']}
Комментарий: {get_current_info.json()['trade']['details']}
Реквизиты: {get_current_info.json()['trade']['counterDetails']} {get_current_info.json()['paymethod_description']}
                                                        ''', reply_markup=kb_accept_cancel_payment)
                        await Activity.acceptPayment.set()
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


@dp.callback_query_handler(trade_cb.filter(action=['back_to_trade']))
async def accept_order(call: types.CallbackQuery, callback_data: dict, state=FSMContext):
    print(callback_data)
    trade_id = callback_data['id']
    kb_accept_cancel_payment = create_accept_cancel_kb(trade_id, callback_data['type'])
    print(kb_accept_cancel_payment)
    if callback_data['type'] == 'BZ':
        url_type = 'trade'
        trade_type = 'trade'
    
    elif callback_data['type'] == 'googleSheets':
        url_type = 'pay'
        trade_type = 'pay'

    elif callback_data['type'] == 'kf':
        url_type = 'kf'
        trade_type = 'kftrade'


    # _______________GAANTEX__________________________GATANTEX________________________GATANTEX________________________
    elif callback_data['type'] == 'garantex':
        url_type = 'gar'
        trade_type = 'gar_trade'

    if (url_type in ['gar', 'pay', 'kf']):
        print(1111)
        get_pay_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')

        if (not get_pay_info.json()[trade_type]['agent'] or str(get_pay_info.json()[trade_type]['agent']) == str(
                call.from_user.id)) and \
                get_pay_info.json()[trade_type]['status'] != 'closed':

            get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')

            if str(get_current_info.json()[trade_type]['agent']) == str(call.from_user.id):
                try:
                    messages = select_message_from_database(call.from_user.id)
                    trade_mas = []
                    for msg, trade_id_db,   in messages:
                        if (msg != call.message.message_id):
                            trade_mas.append(trade_id_db)
                            try:
                                await bot.delete_message(call.from_user.id, msg)
                            except Exception as e:
                                print(e)
                            delete_from_database(call.from_user.id, msg, trade_id_db, url_type)
                    res_delete = {
                                'id' : trade_mas,
                                'tg_id' : call.from_user.id
                            }
                    try:
                        req = requests.post(URL_DJANGO + f'delete/{url_type}/recipient/', json=res_delete)
                    except Exception as e:
                        print(e)
                    msg = await call.message.edit_text(f'''

Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {get_current_info.json()['paymethod_description']}
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
Адресат: `{get_current_info.json()[trade_type]['card_number']}`

Статус: *Ожидаем оплату и предоставление чека.*

    ''', reply_markup=kb_accept_cancel_payment, parse_mode='Markdown')
                    if (url_type == 'kf'):
                        type = 'kf'
                    elif (url_type == 'gar'):
                        type = 'garantex'
                    elif (url_type == 'pay'):
                        type = 'googleSheets'
                    await state.update_data(id=callback_data['id'], type=type, message_id=msg.message_id)

                    await Activity.acceptPayment.set()
                except Exception as e:
                    print(e)
                    await call.answer('Произошла ошибка, нажмите кнопку заново.')

            else:
                await call.answer("Заявка уже в работе", show_alert=True)
                await call.message.delete()
        else:
            await call.answer('Заявка уже в работе.', show_alert=True)
            await call.message.delete()
    
    else:
        get_trade_info = requests.get(URL_DJANGO + f'trade/detail/{trade_id}/')
        if not get_trade_info.json()['trade']['agent'] or str(get_trade_info.json()['trade']['agent']) == str(
                call.from_user.id):

            set_agent_trade = requests.post(URL_DJANGO + f'update/trade/', json=data)

            get_current_info = requests.get(URL_DJANGO + f'trade/detail/{trade_id}/')
            if get_current_info.json()['trade']['agent'] == str(call.from_user.id):
                headers = authorization(
                    get_current_info.json()['user']['key'],
                    get_current_info.json()['user']['email']
                )

                proxy = get_current_info.json()['user']['proxy']

                data = {
                    'type': 'confirm-trade'
                }

                url = f'https://bitzlato.com/api/p2p/trade/{trade_id}/'
                try:
                    req_change_type = requests.post(url, headers=headers, proxies=proxy, json=data)

                    if req_change_type.status_code == 200:
                        await call.answer('Вы успешно взяли заявку в работу!', show_alert=True)
                        await call.message.edit_text(f'''
Переведите {get_current_info.json()['trade']['currency_amount']} {get_current_info.json()['trade']['currency']}
Комментарий: {get_current_info.json()['trade']['details']}
Реквизиты: {get_current_info.json()['trade']['counterDetails']} {get_current_info.json()['paymethod_description']}
                                                        ''', reply_markup=kb_accept_cancel_payment)
                        await Activity.acceptPayment.set()
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



@dp.callback_query_handler(trade_cb.filter(action=['cancel_payment']))
async def accept_cancel(call: types.CallbackQuery, callback_data=dict, state=FSMContext):
    print(1111, callback_data)
    await call.message.edit_text(f'''Вы уверены что хотите отменить сделку?''',
                                 reply_markup=create_yes_no_kb(callback_data['id'], callback_data['type']),
                                 parse_mode='Markdown')


@dp.callback_query_handler(trade_cb.filter(action=['other_reason']))
async def other_case_cancel(call: types.CallbackQuery, callback_data=dict, state=FSMContext):
    await call.message.edit_text(f'''Укажите причину отмены сделки''', parse_mode='Markdown')
    await state.update_data(id=callback_data['id'], type=callback_data['type'])
    await Activity.add_reason_cancel.set()


@dp.callback_query_handler(trade_cb.filter(action=['no_balance']))
async def no_balance_cancel(call: types.CallbackQuery, callback_data=dict, state=FSMContext):
    id = callback_data['id']
    body = {
        'tg_id': call.from_user.id,
        'options': {
            'is_working_now': False,
            'is_instead': False,
        }
    }
    change_status_agent = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)
    data = {
        'id': str(id),
        'status': 'again_pending' if callback_data['type'] == 'garantex' else 'trade_created',
        'agent': None,
    }
    if callback_data['type'] == 'garantex':
        update_status = requests.post(URL_DJANGO + 'update/garantex/trade/', json=data)
        await call.answer("Сделка отменена. Вы сняты со смены, ждите пополнения баланса.", show_alert=True)
        await call.message.delete()
    if callback_data['type'] == 'kf':

        update_status = requests.post(URL_DJANGO + 'update/kf/trade/', json=data)
        get_current_info = requests.get(URL_DJANGO + f'kf/trade/detail/{id}/')
        
        await call.answer("Сделка отменена. Вы сняты со смены, ждите пополнения баланса.", show_alert=True)
        await call.message.edit_text(f'''
Заявка: KF — {id}
Инструмент: {get_current_info.json()['kftrade']['type']}
Сумма: `{get_current_info.json()['kftrade']['amount']}` 
Адресат: `{get_current_info.json()['kftrade']['card_number']}`

Статус: *Отменена.*
Причина: *Не хватает баланса.*
                ''', parse_mode='Markdown')
    
    await state.finish()


@dp.message_handler(state=Activity.add_reason_cancel)
async def other_case_cancel(message: types.Message, state=FSMContext):
    state_data = await state.get_data()
    id = state_data['id']
    reason = message.text
    body = {
        'tg_id': message.from_user.id,
        'options': {
            'is_working_now': False,
            'is_instead': True,
        }
    }
    change_status_agent = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)
    state_data = await state.get_data()
    if state_data['type'] == 'garantex':
        gar_trade_info = requests.get(URL_DJANGO + f'gar/trade/detail/{str(id)}/').json()
        JWT = get_jwt(gar_trade_info['auth']['private_key'], gar_trade_info['auth']['uid'])
        header = {
            'Authorization': f'Bearer {JWT}'
        }
        data_garantex = {'deal_id': str(id), 'message': reason}

        message_request = requests.post(f'https://garantex.io/api/v2/otc/chats/message',
                                        headers=header, data=data_garantex)
        cancel_trade(JWT, id)
        data = {
            'id': str(id),
            'status': 'canceled',
        }

        update_status = requests.post(URL_DJANGO + 'update/garantex/trade/', json=data)
        await message.reply('Заявка отменена.')
    if (state_data['type'] == 'kf'):
        data = {
            'id': str(id),
            'status': 'cancel_by_operator',
            'comment' : message.text
        }

        get_current_info = requests.get(URL_DJANGO + f'kf/trade/detail/{id}/')

        update_status = requests.post(URL_DJANGO + 'update/kf/trade/', json=data)

        await message.reply(f'''
Заявка: KF — {id}
Инструмент: {get_current_info.json()['kftrade']['type']}
Сумма: `{get_current_info.json()['kftrade']['amount']}` 
Адресат: `{get_current_info.json()['kftrade']['card_number']}`

Статус: *Отменена.*
Причина: *{message.text}*

            ''', parse_mode='Markdown')
    await state.finish()



@dp.message_handler(content_types=['photo', 'document'], state=Activity.acceptPayment)
async def get_photo(message: types.Message, state=FSMContext):
    data = await state.get_data()

    id = data['id']
    msg_id = data['message_id']
    body = {
        'tg_id': message.from_user.id,
        'options': {
            'is_working_now': False,
            'is_instead': True,
        }
    }
    if data['type'] == 'BZ':
        id = data['id']

        get_trade_detail = requests.get(URL_DJANGO + f'trade/detail/{id}/')
        key = get_trade_detail.json()['user']['key']
        proxy = get_trade_detail.json()['user']['proxy']
        email = get_trade_detail.json()['user']['email']

        file_name = f'/root/prod/SkillPay-Django/tgchecks/{id}_{message.from_user.id}.png'
        await message.photo[-1].download(file_name)
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
        files = {'file': open(file_name, 'rb')}

        headers = authorization(key, email)

        r = requests.post(url, headers=headers, proxies=proxy, files=files)

        asyncio.create_task(confirm_payment(id=id, message=message, state=state))
    elif data['type'] == 'googleSheets':
        file_name = cheques_base + f'pay{id}_{message.from_user.id}.png'
        await message.photo[-1].download(file_name)
        data = {
            'id': id,
            'cheque': f'tgchecks/pay{id}_{message.from_user.id}.png'
        }
        upload = requests.post(URL_DJANGO + 'update/pay/', json=data)
        if upload.status_code == 200:
            data = {
                'id': id,
                'status': 'confirm_payment'
            }
            update_pay = requests.post(URL_DJANGO + 'update/pay/', json=data)

            change_status_agent = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)

            if change_status_agent.status_code == 200 and update_pay.status_code == 200:
                await message.reply('Чек принят! Сделка завершена, ожидайте следующую.')
            else:
                await message.answer('Произошла ошибка, свяжитесь с админом.')

            await state.finish()
        else:
            await message.answer('Произошла ошибка при скачивании фото. Свяжитесь с админом.')
            await state.finish()
    elif data['type'] == 'kf':
        get_current_info = requests.get(URL_DJANGO + f'kf/trade/detail/{id}/')
        file_name = cheques_base + f'kf{id}_{message.from_user.id}.pdf'
        if message.content_type == 'document' and message.document.file_name[-3:] == 'pdf':
            await message.document.download(destination_file=file_name)
            data = {
                'id': id,
                'cheque': f'kf_checks/kf{id}_{message.from_user.id}.pdf'
            }
            upload = requests.post(URL_DJANGO + 'update/kf/trade/', json=data)

            if upload.status_code == 200:
                await bot.delete_message(chat_id=message.from_user.id, message_id=msg_id)
                msg = await message.reply(text=f'''
Заявка: {get_current_info.json()['kftrade']['platform_id']}
Инструмент: {get_current_info.json()['kftrade']['type']}
Сумма: `{get_current_info.json()['kftrade']['amount']}` 
Адресат: `{get_current_info.json()['kftrade']['card_number']}`

Статус: *Производится проверка чека!*



''', parse_mode='Markdown')
                while 1:
                    req_django = requests.get(URL_DJANGO + f'kf/trade/detail/{id}/')
                    if (req_django.status_code == 200):
                        if (req_django.json()['kftrade']['status'] == 'confirm_payment'):
                            change_status_agent = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)
                            if change_status_agent.status_code == 200:
                                # await bot.delete_message(chat_id=message.from_user.id, message_id=msg.message_id)
                                await bot.edit_message_text(chat_id=message.from_user.id, message_id=msg.message_id,
                                                            text=f'''
Заявка: KF — {id}
Инструмент: {get_current_info.json()['kftrade']['type']}
Сумма: `{get_current_info.json()['kftrade']['amount']}` 
Адресат: `{get_current_info.json()['kftrade']['card_number']}`

Статус: *Заявка успешно выполнена!*

''', parse_mode='Markdown')
                            else:
                                await message.answer('Произошла ошибка, свяжитесь с админом.')
                            break
                    await asyncio.sleep(0)

                await state.finish()
            else:
                await message.answer('Произошла ошибка при скачивании документа. Свяжитесь с админом.')
                await state.finish()
        else:
            await message.reply(text='Вы отправили чек не в том формате, пришлите заново в формате pdf')
    # _______________GATANTEX__________________________GATANTEX________________________GATANTEX__________________
    elif data['type'] == 'garantex':
        id = data['id']

        get_trade_detail = requests.get(URL_DJANGO + f'gar/trade/detail/{id}/')
        trade_detail = get_trade_detail.json()
        jwt = get_jwt(uid=trade_detail['auth']['uid'], private_key=trade_detail['auth']['private_key'])

        file_name = f'/root/dev/SkillPay-Django/gar_checks/gar{id}_{message.from_user.id}.pdf'
        if message.content_type == 'document' and message.document.file_name[-3:] == 'pdf':
            await message.document.download(destination_file=file_name)
            data = {
                'id': id,
                'cheque': f'gar_checks/gar{id}_{message.from_user.id}.pdf'
            }
            upload = requests.post(URL_DJANGO + 'update/garantex/trade/', json=data)
            if upload.status_code == 200:
                jwt = get_jwt(uid=trade_detail['auth']['uid'], private_key=trade_detail['auth']['private_key'])
                header = {
                    'Authorization': f'Bearer {jwt}'
                }
                data_garantex = {'deal_id': id, 'message': 'Чек'}
                files = {'file': open(file_name, 'rb')}

                message_request = requests.post(f'https://garantex.io/api/v2/otc/chats/message',
                                                headers=header, data=data_garantex, files=files)
                if message_request.status_code == 201:
                    await bot.delete_message(chat_id=message.from_user.id, message_id=msg_id)
                    msg = await message.reply(text=f'''
Заявка: GAR — {id}
Инструмент: {trade_detail['gar_trade']['paymethod']}
Сумма: `{trade_detail['gar_trade']['currency_amount']}` 
Адресат: `{trade_detail['gar_trade']['details']}`

Статус: *Производится проверка чека!*

                    ''', parse_mode='Markdown')

                    while 1:
                        req_django = requests.get(URL_DJANGO + f'gar/trade/detail/{id}/')
                        if req_django.status_code == 200:
                            if req_django.json()['gar_trade']['status'] == 'completed':
                                change_status_agent = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)
                                if change_status_agent.status_code == 200:
                                    await bot.edit_message_text(chat_id=message.from_user.id, message_id=msg.message_id,
                                                                text=f'''
Заявка: GAR — {id}
Инструмент: {trade_detail['gar_trade']['paymethod']}
Сумма: `{trade_detail['gar_trade']['currency_amount']}` 
Адресат: `{trade_detail['gar_trade']['details']}`

Статус: *Заявка успешно выполнена!*

                    ''', parse_mode='Markdown')
                                else:
                                    await message.answer('Произошла ошибка, свяжитесь с админом.')
                                break
                        await asyncio.sleep(0)

                    await state.finish()
                else:
                    await message.answer('Произошла ошибка при скачивании документа. Свяжитесь с админом.')
                    await state.finish()
            else:
                await message.reply(text='Вы отправили чек не в том формате, пришлите заново в формате pdf')


@dp.callback_query_handler(text='Назад')
async def back(call: types.CallbackQuery):
    await call.message.edit_text('Меню', reply_markup=kb_menu_main)
