import asyncio
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
from PyPDF2 import PdfFileReader

from pdf2image import convert_from_path

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
from settings import URL_DJANGO, cheques_kf, cheques_bz, cheques_gar, cheques_pay
from states.activity.activity_state import Activity
from aiogram.dispatcher import FSMContext

import requests
from jose import jws
from jose.constants import ALGORITHMS
from loader import bot
from garantexAPI.auth import *
from garantexAPI.chat import *
from garantexAPI.trades import *
from skillpaybot import select_message_from_database, delete_from_database, paymethod

trade_cb = CallbackData("trade", "type", "id", "action")


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
                InlineKeyboardButton(text='Не хватает баланса',
                                     callback_data=trade_cb.new(id=trade_id, type=trade_type,
                                                                action='no_balance')),

                InlineKeyboardButton(text='Другая причина',
                                     callback_data=trade_cb.new(id=trade_id, type=trade_type,
                                                                action='other_reason'))
            ],
            [
                InlineKeyboardButton(text='Вернуться к сделке',
                                     callback_data=trade_cb.new(id=trade_id, type=trade_type,
                                                                action='back_to_trade'))
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
        'id': trade_mas,
        'tg_id': call.from_user.id
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
    data = await state.get_data()
    print('[DATA]', data)
    trade_id = callback_data['id']
    body = {
        'tg_id': call.from_user.id
    }

    r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)
    if r.status_code == 200:
        if r.json()[0]['is_working_now'] == False:

            print(callback_data)
            data = {
                'id': str(trade_id),
                'agent': str(call.from_user.id)
            }
            kb_accept_cancel_payment = create_accept_cancel_kb(trade_id, callback_data['type'])
            print(kb_accept_cancel_payment)

            if callback_data['type'] == 'bz':
                url_type = 'bz'
                trade_type = 'bz'

            elif callback_data['type'] == 'googleSheets':
                url_type = 'pay'
                trade_type = 'pay'

            elif callback_data['type'] == 'kf':
                url_type = 'kf'
                trade_type = 'kftrade'

            elif callback_data['type'] == 'garantex':
                url_type = 'gar'
                trade_type = 'gar_trade'

            if url_type in ['gar', 'pay', 'kf', 'bz']:
                print(trade_id)    
                get_pay_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')
                print(get_pay_info)
                if (not get_pay_info.json()[trade_type]['agent'] or str(
                        get_pay_info.json()[trade_type]['agent']) == str(
                    call.from_user.id)) and \
                        get_pay_info.json()[trade_type]['status'] != 'closed' and get_pay_info.json()[trade_type][
                    'status'] != 'time_cancel':

                    set_agent_trade = requests.post(URL_DJANGO + f'update/{url_type}/trade/', json=data)

                    print(set_agent_trade.status_code)

                    get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')

                    if str(get_current_info.json()[trade_type]['agent']) == str(call.from_user.id):
                        try:
                            messages = select_message_from_database(call.from_user.id)
                            trade_mas = []
                            for msg, trade_id_db, in messages:
                                if msg != call.message.message_id:
                                    trade_mas.append(trade_id_db)
                                    try:
                                        await bot.delete_message(call.from_user.id, msg)
                                    except Exception as e:
                                        print(e)
                                    delete_from_database(call.from_user.id, msg, trade_id_db, url_type)
                            res_delete = {
                                'id': trade_mas,
                                'tg_id': call.from_user.id
                            }
                            try:
                                req = requests.post(URL_DJANGO + f'delete/{url_type}/recipient/', json=res_delete)
                            except Exception as e:
                                print(e)
                            await call.answer('Вы успешно взяли заявку в работу!', show_alert=True)
                            msg = await call.message.edit_text(f'''

Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *заявка за вами, оплачиваем и присылаем чек*

            ''', reply_markup=kb_accept_cancel_payment, parse_mode='Markdown')
                            if url_type == 'kf':
                                type = 'kf'
                            elif url_type == 'gar':
                                type = 'garantex'
                            elif url_type == 'pay':
                                type = 'googleSheets'
                            elif url_type == 'bz':
                                type = 'bz'
                            print(trade_id, type)
                            await state.update_data(id=trade_id, type=type, message_id=msg.message_id,
                                                    url_type=url_type, trade_type=trade_type)
                            print('[DATA]', await state.get_data())
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

            

@dp.callback_query_handler(trade_cb.filter(action=['back_to_trade']), state=Activity.acceptPayment)
async def accept_order(call: types.CallbackQuery, callback_data: dict, state=FSMContext):
    data = await state.get_data()
    print('[DATA]', data)
    print(callback_data)
    trade_id = callback_data['id']
    kb_accept_cancel_payment = create_accept_cancel_kb(trade_id, callback_data['type'])
    print(kb_accept_cancel_payment)
    if callback_data['type'] == 'bz':
        url_type = 'bz'
        trade_type = 'bz'

    elif callback_data['type'] == 'googleSheets':
        url_type = 'pay'
        trade_type = 'pay'

    elif callback_data['type'] == 'kf':
        url_type = 'kf'
        trade_type = 'kftrade'

    elif callback_data['type'] == 'garantex':
        url_type = 'gar'
        trade_type = 'gar_trade'

    if url_type in ['gar', 'pay', 'kf', 'bz']:
        get_pay_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')

        if (not get_pay_info.json()[trade_type]['agent'] or str(get_pay_info.json()[trade_type]['agent']) == str(
                call.from_user.id)) and \
                get_pay_info.json()[trade_type]['status'] != 'closed':

            get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')

            if str(get_current_info.json()[trade_type]['agent']) == str(call.from_user.id):
                try:
                    messages = select_message_from_database(call.from_user.id)
                    trade_mas = []
                    for msg, trade_id_db, in messages:
                        if (msg != call.message.message_id):
                            trade_mas.append(trade_id_db)
                            try:
                                await bot.delete_message(call.from_user.id, msg)
                            except Exception as e:
                                print(e)
                            delete_from_database(call.from_user.id, msg, trade_id_db, url_type)
                    res_delete = {
                        'id': trade_mas,
                        'tg_id': call.from_user.id
                    }
                    try:
                        req = requests.post(URL_DJANGO + f'delete/{url_type}/recipient/', json=res_delete)
                    except Exception as e:
                        print(e)
                    print(get_current_info.json()[trade_type])
                    msg = await call.message.edit_text(f'''

Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *заявка за вами, оплачиваем и присылаем чек*

    ''', reply_markup=kb_accept_cancel_payment, parse_mode='Markdown')
                    if (url_type == 'kf'):
                        type = 'kf'
                    elif (url_type == 'gar'):
                        type = 'garantex'
                    elif (url_type == 'pay'):
                        type = 'googleSheets'
                    elif (url_type == 'bz'):
                        type = 'bz'
                    await state.update_data(id=trade_id, type=type, message_id=msg.message_id, url_type=url_type,
                                            trade_type=trade_type)
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


@dp.callback_query_handler(trade_cb.filter(action=['cancel_payment']), state=Activity.acceptPayment)
async def accept_cancel(call: types.CallbackQuery, callback_data=dict, state=FSMContext):
    data = await state.get_data()
    id = data['id']
    print(data)
    trade_type = data['trade_type']
    url_type = data['url_type']

    get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')

    msg = await call.message.edit_text(f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *режим отмены, выберите причину*
''',
                                 reply_markup=create_yes_no_kb(callback_data['id'], callback_data['type']),
                                 parse_mode='Markdown')

@dp.callback_query_handler(trade_cb.filter(action=['other_reason']), state=Activity.acceptPayment)
async def other_case_cancel(call: types.CallbackQuery, callback_data=dict, state=FSMContext):
    data = await state.get_data()

    trade_type = data['trade_type']
    url_type = data['url_type']

    get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{data["id"]}/')

    msg = await call.message.edit_text(f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *отправьте комментарий проблемы отправки*

''', parse_mode='Markdown')
    await state.update_data(id=callback_data['id'], type=callback_data['type'], msg_id=msg.message_id)
    await Activity.add_reason_cancel.set()


@dp.callback_query_handler(trade_cb.filter(action=['no_balance']), state=Activity.acceptPayment)
async def no_balance_cancel(call: types.CallbackQuery, callback_data=dict, state=FSMContext):
    id = callback_data['id']
    body = {
        'tg_id': call.from_user.id,
        'options': {
            'is_working_now': False,
            'is_instead': False,
        }
    }
    data = await state.get_data()

    trade_type = data['trade_type']
    url_type = data['url_type']

    change_status_agent = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)
    data = {
        'id': str(id),
        'status': 'again_pending' if callback_data['type'] == 'garantex' else 'again_trade_created',
        'agent': None,
    }
    
    update_status = requests.post(URL_DJANGO + f'update/{url_type}/trade/', json=data)
    get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')

    await call.answer("Сделка отменена. Вы сняты со смены, ждите пополнения баланса.", show_alert=True)
    await call.message.edit_text(f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *заявка отменена из-за нехватки баланса*
                ''', parse_mode='Markdown')

    await state.finish()


@dp.message_handler(state=Activity.add_reason_cancel)
async def other_case_cancel(message: types.Message, state=FSMContext):
    state_data = await state.get_data()
    await bot.delete_message(message.chat.id, state_data['msg_id'])
    id = state_data['id']
    reason = message.text
    body = {
        'tg_id': message.from_user.id,
        'options': {
            'is_working_now': False,
            'is_instead': True,
        }
    }
    trade_type = state_data['trade_type']
    url_type = state_data['url_type']
    change_status_agent = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)
    state_data = await state.get_data()

    if state_data['type'] == 'garantex':
        gar_trade_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{str(id)}/').json()
        JWT = get_jwt(gar_trade_info['auth']['private_key'], gar_trade_info['auth']['uid'])
        header = {
            'Authorization': f'Bearer {JWT}'
        }
        data_garantex = {'deal_id': str(id), 'message': reason}

        message_request = requests.post(f'https://garantex.io/api/v2/otc/chats/message',
                                        headers=header, data=data_garantex)
        cancel_trade(JWT, id)

    elif (state_data['type'] == 'bz'):
        get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')
        key = get_current_info.json()['user']['key']
        proxy = get_current_info.json()['user']['proxy']
        email = get_current_info.json()['user']['email']
        send_message = f'https://bitzlato.net/api/p2p/trade/{id}/chat/'
        headers = authorization(key, email)
        data_message = {
            'message': f'{message.text}.',
            'payload': {
                'message': 'string'
            }
        }
        send_message_req = requests.post(send_message, headers=headers, proxies=proxy, json=data_message)

        header = authorization(key=key, email_bz=email)
        data_cancel = {
            'type': "cancel"
        }
        adv_requests = requests.post(f'https://bitzlato.net/api/p2p/trade/{id}', headers=header,
                                 proxies=proxy, json=data_cancel)

    data = {
        'id': str(id),
        'status': 'cancel_by_operator',
        'comment' : message.text
    }

    update_status = requests.post(URL_DJANGO + f'update/{url_type}/trade/', json=data)
    
    get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')

    await message.reply(f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *заявка отменена из-за проблемы отправки*

        ''', parse_mode='Markdown')

    await state.finish()


@dp.message_handler(content_types=['photo', 'document'], state=Activity.acceptPayment)
async def get_photo(message: types.Message, state=FSMContext):
    data = await state.get_data()
    trade_type = data['trade_type']
    url_type = data['url_type']
    id = data['id']
    msg_id = data['message_id']
    file_name = f'/root/prod/SkillPay-Django/{url_type}/{id}_{message.from_user.id}.pdf'
    get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')

    body = {
        'tg_id': message.from_user.id,
        'options': {
            'is_working_now': False,
            'is_instead': True,
        }
    }


    if message.content_type == 'document' and message.document.file_name[-3:] == 'pdf':
        await message.document.download(destination_file=file_name)
        data = {
                'id': id,
                'cheque': f'{url_type}/{id}_{message.from_user.id}.pdf'
            }

        upload = requests.post(URL_DJANGO + f'update/{url_type}/trade/', json=data)

        await bot.delete_message(chat_id=message.from_user.id, message_id=msg_id)
        msg = await message.reply(text=f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *чек принят, производится проверка*

''', parse_mode='Markdown')

        pdf_document = file_name  
        with open(pdf_document, "rb") as filehandle:  
            pdf = PdfFileReader(filehandle)
            info = pdf.getDocumentInfo()
            pages = pdf.getNumPages()   
            page1 = pdf.getPage(0)
            text = page1.extractText()
            mas = text.replace('-', '').split()
            print(text)
            print(''.join(text.split()[2:4]), text.split()[10], text.split()[20][1:],  get_current_info.json()[trade_type]['card_number'][12:16])
        amount = ''
        status = ''
        card_number = ''
        if paymethod[get_current_info.json()[trade_type]['paymethod']] == 'TINK':
            if int(get_current_info.json()[trade_type]['amount']) < 1000:
                amount = ''.join(text.split()[2])
                status = text.split()[9]
                card_number = text.split()[19][1:]
            elif int(get_current_info.json()[trade_type]['amount']) >= 1000 and int(get_current_info.json()[trade_type]['amount']) < 1_000_000:
                amount = ''.join(text.split()[2:4])
                status = text.split()[10]
                card_number = text.split()[20][1:]
            elif int(get_current_info.json()[trade_type]['amount']) >= 1_000_000:
                amount = ''.join(text.split()[2:5])
                status = text.split()[11]
                card_number = text.split()[21][1:]
        elif paymethod[get_current_info.json()[trade_type]['paymethod']] == 'SBER':
            if int(get_current_info.json()[trade_type]['amount']) < 1000:
                amount = ''.join(mas[33])
                card_number = mas[29]
            elif int(get_current_info.json()[trade_type]['amount']) >= 1000 and int(get_current_info.json()[trade_type]['amount']) < 1_000_000:
                amount = ''.join(mas[33:35])
                card_number = mas[30]
            elif int(get_current_info.json()[trade_type]['amount']) >= 1_000_000:
                amount = ''.join(mas[33:36])
                card_number = mas[31]

        if ((paymethod[get_current_info.json()[trade_type]['paymethod']] == 'TINK' and 
            amount == get_current_info.json()[trade_type]['amount'] and 
            status == 'Успешно' and
            card_number == get_current_info.json()[trade_type]['card_number'][12:16])
            or 
            (paymethod[get_current_info.json()[trade_type]['paymethod']] == 'SBER' and 
            amount == get_current_info.json()[trade_type]['amount'] and 
            card_number == get_current_info.json()[trade_type]['card_number'][12:16])):

            if url_type == 'bz':
                get_trade_detail = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')
                key = get_trade_detail.json()['user']['key']
                proxy = get_trade_detail.json()['user']['proxy']
                email = get_trade_detail.json()['user']['email']
                print(file_name, file_name[0: len(file_name) - 4] +'.jpg')
                pages = convert_from_path(file_name)
                
                for i in range(len(pages)):

                    pages[i].save(file_name[0: len(file_name) - 4] +'.jpg', 'JPEG')
                file_name = file_name[0: len(file_name) - 4] +'.jpg'
                send_message = f'https://bitzlato.net/api/p2p/trade/{id}/chat/'
                headers = authorization(key, email)
                data_message = {
                    'message': 'Оплатил.',
                    'payload': {
                        'message': 'string'
                    }
                }
                send_message_req = requests.post(send_message, headers=headers, proxies=proxy, json=data_message)
                url = f'https://bitzlato.net/api/p2p/trade/{id}/chat/sendfile'

                data = {
                    'mime_type': 'image/png',
                    'name': 'Check.png'
                }
                files = {'file': open(file_name, 'rb')}

                headers = authorization(key, email)

                r = requests.post(url, headers=headers, proxies=proxy, files=files)

                headers = authorization(get_trade_detail.json()['user']['key'], get_trade_detail.json()['user']['email'])

                proxy = get_trade_detail.json()['user']['proxy']

                data = {
                    'type': 'payment'
                }

                url = f'https://bitzlato.net/api2/p2p/trade/{id}'

                req_change_type = requests.post(url, headers=headers, proxies=proxy, json=data)
            elif url_type == 'gar':
                get_trade_detail = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')
                trade_detail = get_trade_detail.json()
                jwt = get_jwt(uid=trade_detail['auth']['uid'], private_key=trade_detail['auth']['private_key'])
                header = {
                    'Authorization': f'Bearer {jwt}'
                }
                data_garantex = {'deal_id': id, 'message': 'Чек'}
                files = {'file': open(file_name, 'rb')}

                message_request = requests.post(f'https://garantex.io/api/v2/otc/chats/message',
                                            headers=header, data=data_garantex, files=files)
                print(message_request.status_code, message_request.text)
            while 1:
                try:
                    req = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')
                    if req.status_code == 200:
                        trade_info = req.json()
                        if trade_info[trade_type]['status'] == 'confirm_payment' or trade_info[trade_type]['status'] == 'completed':
                            body = {
                                'tg_id': message.from_user.id,
                                'options': {
                                    'is_working_now': False,
                                    'is_instead': True,
                                }
                            }

                            change_status_agent = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)

                            if change_status_agent.status_code == 200:
                                await bot.edit_message_text(chat_id=message.from_user.id, message_id=msg.message_id,
                                                                text=f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *успешно оплачена и закрыта*

                    ''', parse_mode='Markdown')
                            else:
                                await message.answer('Произошла ошибка, свяжитесь с админом.')

                            await state.finish()
                            break
                    await asyncio.sleep(1)

                except Exception as e:
                    print(e)
                    continue
        else:
            msg = await bot.edit_message_text(chat_id=message.from_user.id, message_id=msg.message_id,
                                                            text=f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *чек не принят, пришлите заново корректный*

''', parse_mode='Markdown')
            await state.update_data(msg_id=msg.message_id)

            await Activity.acceptPayment.set()
    else:
        await message.reply(text='Вы отправили чек не в том формате, пришлите заново в формате png')
        

@dp.callback_query_handler(text='Назад')
async def back(call: types.CallbackQuery):
    await call.message.edit_text('Меню', reply_markup=kb_menu_main)



@dp.message_handler(text='/reset', state='*')
async def reset(message: types.Message, state=FSMContext):
    await message.answer('Бот перезапущен, срочно обратитесь к диспетчеру, если была заявка в работе')
    await state.finish()

