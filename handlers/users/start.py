import asyncio
import os

import environs
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
from PyPDF2 import PdfFileReader

from pdf2image import convert_from_path

from data.config import CHANNEL_ID
from states.operator_states import OperatorCheckBalance
from aiogram.utils.exceptions import MessageToDeleteNotFound
from keyboards.inline.ikb import cancel_cb

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
import re
import requests
from jose import jws
from jose.constants import ALGORITHMS
from loader import bot
from garantexAPI.auth import *
from garantexAPI.chat import *
from garantexAPI.trades import *
from skillpaybot import select_message_from_database, delete_from_database, paymethod, select_data_from_database, \
    add_to_database
from keyboards.inline.ikb import courier_kb, dispatcher_kb

from aiogram.types.reply_keyboard import KeyboardButton, ReplyKeyboardMarkup

trade_cb = CallbackData("trade", "type", "id", "action")

def update_keyboard(balance, smena):
    button_balance = KeyboardButton(text=f'Ваш баланс: {balance}')
    button_smena = KeyboardButton(text=smena)
    button_settings = KeyboardButton(text='Настройки')
    balance_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    balance_kb.add(button_balance)
    balance_kb.add(button_smena)
    balance_kb.add(button_settings)
    return balance_kb


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


@dp.message_handler(text='Начать смену', state='*')
async def join_to_job(message: types.Message, state=FSMContext):
    body = {
        'tg_id': message.chat.id
    }

    r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)

    data = json.loads(r.text)[0]

    # await bot.delete_message(call.from_user.id, msg.message_id)

    if r.status_code == 200:
        if data['active_card']:
            if not data['is_instead'] and data['is_staff']:

                # body = {
                #     'tg_id': message.chat.id,
                #     'options': {
                #         # 'is_working_now': False,
                #         'is_instead': True,
                #     }
                # }

                # r = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)
                msg = await message.answer(
                    f'Привет, {message.from_user.first_name}!\nПожалуйста введите баланс по текущей карте, для выхода на смену',
                    reply_markup=cancel_cb)
                await state.set_data({'msg': msg.message_id})
                await OperatorCheckBalance.input_balance.set()
            elif not data['is_instead']:
                body = {
                    'tg_id': message.chat.id,
                    'options': {
                        # 'is_working_now': False,
                        'is_instead': True,
                    }
                }

                r = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)
                if r.status_code == 200:
                    await message.answer("Вы начали смену! Ожидайте заявки.",
                                         reply_markup=update_keyboard(data['income_operator'], "Закончить смену"))
                else:
                    await message.answer('Не удалось начать смену, свяжитесь с тех. поддержкой.',
                                         reply_markup=update_keyboard(data['income_operator'], "Начать смену"))
            else:
                await message.answer("Вы и так уже на смене!",
                                     reply_markup=update_keyboard(data['income_operator'], "Закончить смену"))
        else:
            await message.answer("У вас нет активной карточки! Свяжитесь с диспетчером.",
                                 reply_markup=update_keyboard(data['income_operator'], "Начать смену"))


@dp.message_handler(state=OperatorCheckBalance.input_balance)
async def check_operator_balance(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    try:
        await bot.delete_message(message.chat.id, state_data['msg'])
    except MessageToDeleteNotFound:
        pass
    except KeyError:
        pass
    try:
        balance = float(message.text)
        if balance < 0:
            raise ValueError
        data = requests.get(URL_DJANGO + f'operators/{message.chat.id}/').json()
        if not data['active_card']:
            await message.answer('У вас нет активной карты.\nОбратитесь в службу поддержки!')
            await state.finish()
        elif balance == float(data['active_card']['card_balance']):
            body = {
                'tg_id': message.chat.id,
                'options': {
                    # 'is_working_now': False,
                    'is_instead': True,
                }
            }

            r = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)
            if r.status_code == 200:
                await message.answer(f"""
Привет, {message.from_user.first_name}! Ты успешно зашел на смену, ожидай заявки.""",
                                     reply_markup=update_keyboard(data['income_operator'], 'Закончить смену'))
            else:
                await message.answer("Не удалось начать смену, свяжитесь с тех. поддержкой")
            # msg = await message.answer("Обновление баланса🆙", reply_markup=update_balance(data['income_operator']))
        else:
            await message.answer(
                '⛔️ Найдены несоответствия в балансе! ⛔️\nВаш аккаунт будет временно заблокирован, пока вы не обратитесь в службу поддержки\n')
        await state.finish()
    except ValueError:
        await message.answer('Пожалуйста введите корректное значение баланса или отмените операцию',
                             reply_markup=cancel_cb)
    except Exception as e:
        print(e)
        await message.answer('Ошибка на стороне сервера')
        await state.finish()
        print(data)


@dp.message_handler(text='Закончить смену', state='*')
async def leave_from_job(message: types.Message, state=FSMContext):
    body = {
        'tg_id': message.chat.id
    }

    r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)

    data = json.loads(r.text)[0]

    messages = select_message_from_database(message.chat.id)
    trade_mas = []
    for msg, trade_id_db, in messages:
        trade_mas.append(trade_id_db)
        try:
            await bot.delete_message(message.chat.id, msg)
        except Exception as e:
            print(e)
        delete_from_database(message.chat.id, msg, trade_id_db, 'kf')
    res_delete = {
        'id': trade_mas,
        'tg_id': message.chat.id
    }
    try:
        req = requests.post(URL_DJANGO + 'delete/kf/recipient/', json=res_delete)
    except Exception as e:
        print(e)
    if r.status_code == 200:
        if data['is_instead']:
            body = {
                'tg_id': message.chat.id,
                'options': {
                    'is_working_now': False,
                    'is_instead': False,
                }
            }

            r = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)

            await message.answer("Вы закончили смену! Заявки больше вам не приходят.",
                                 reply_markup=update_keyboard(data['income_operator'], "Начать смену"))

        else:
            await message.answer("Вы и так уже не на смене!",
                                 reply_markup=update_keyboard(data['income_operator'], "Закончить смену"))
    else:
        await message.answer('Не удалось выполнить действие, свяжитесь с тех. поддержкой.',
                             reply_markup=update_keyboard(data['income_operator'], "Начать смену"))


@dp.message_handler(text='/reset', state='*')
async def reset(message: types.Message, state=FSMContext):
    get_dispatchers = requests.get(URL_DJANGO + 'get/dispatchers/')
    dispatcher_id = get_dispatchers.json()
    body = {
        'tg_id': message.from_user.id
    }
    r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)
    get_agent_name = r.json()[0]['user_name']
    for i in dispatcher_id:
        try:
            await bot.send_message(chat_id=i, text=f'''
Агент: {get_agent_name}
Использовал /reset.
                ''')
        except Exception as e:
            print(e)
    await message.answer('Бот перезапущен, срочно обратитесь к диспетчеру, если была заявка в работе')
    await state.finish()


@dp.message_handler(text='Настройки', state='*')
async def job(message: types.Message, state=FSMContext):
    await message.answer('Выберите действие', reply_markup=kb_menu_main)


# @dp.callback_query_handler(text='Уйти со смены')
# async def start_job(call: types.CallbackQuery):
#     body = {
#         'tg_id': call.from_user.id
#     }

#     r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)

#     data = json.loads(r.text)[0]


#     msg = await call.message.answer("Обновление баланса🆙", reply_markup=update_balance(data['income_operator']))
#     # await bot.delete_message(call.from_user.id, msg.message_id)

#     messages = select_message_from_database(call.from_user.id)
#     trade_mas = []
#     for msg, trade_id_db, in messages:
#         trade_mas.append(trade_id_db)
#         try:
#             await bot.delete_message(call.from_user.id, msg)
#         except Exception as e:
#             print(e)
#         delete_from_database(call.from_user.id, msg, trade_id_db, 'kf')
#     res_delete = {
#         'id': trade_mas,
#         'tg_id': call.from_user.id
#     }
#     try:
#         req = requests.post(URL_DJANGO + 'delete/kf/recipient/', json=res_delete)
#     except Exception as e:
#         print(e)
#     if r.status_code == 200:
#         if data['is_instead']:
#             body = {
#                 'tg_id': call.from_user.id,
#                 'options': {
#                     'is_working_now': False,
#                     'is_instead': False,
#                 }
#             }

#             r = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)

#             await call.answer("Вы закончили смену! Заявки больше вам не приходят.", show_alert=True)

#             await call.message.delete()
#         else:
#             await call.answer("Вы и так уже не на смене!", show_alert=True)
#     else:
#         await call.message.answer('Не удалось выполнить действие, свяжитесь с тех. поддержкой.')


# @dp.callback_query_handler(text='Встать на смену')
# async def start_job(call: types.CallbackQuery):
#     body = {
#         'tg_id': call.from_user.id
#     }

#     r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)

#     data = json.loads(r.text)[0]

#     msg = await call.message.answer("Обновление баланса🆙", reply_markup=update_balance(data['income_operator']))
#     # await bot.delete_message(call.from_user.id, msg.message_id)

#     if r.status_code == 200:
#         if data['active_card']:
#             if not data['is_instead']:
#                 body = {
#                     'tg_id': call.from_user.id,
#                     'options': {
#                         'is_working_now': False,
#                         'is_instead': True,
#                     }
#                 }

#                 r = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)

#                 if r.status_code == 200:
#                     await call.answer("Вы начали смену! Ожидайте заявки.", show_alert=True)
#                 else:
#                     await call.answer('Не удалось начать смену, свяжитесь с тех. поддержкой.', show_alert=True)
#             else:
#                 await call.answer("Вы и так уже на смене!", show_alert=True)
#         else:
#             await call.answer("У вас нет активной карточки! Свяжитесь с диспетчером.", show_alert=True)


async def waiting_close(trade_id, url_type, trade_type, chat_id, state):
    flags = {
        'main_sent': False,
        'sent_1': False,
        'sent_3': False,
        'sent_5': False,
        'sent_10': False,
    }
    while True:
        print('функция пошла')
        get_trade_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')
        print(get_trade_info.status_code)
        print(select_message_from_database(chat_id))
        if get_trade_info.status_code == 200:
            trade_info = get_trade_info.json()
            print(trade_info[trade_type]['status'])
            if trade_info[trade_type]['status'] == 'in_progress':
                print('asdasda')
                time_create_trade = datetime.datetime.strptime(trade_info[trade_type]['date_create'],
                                                               "%Y-%m-%dT%H:%M:%S.%f").timestamp()
                time_now = datetime.datetime.now().timestamp()
                time_close = float(trade_info[trade_type]['time_close']) * 60
                print(time_close - time_now + time_create_trade)

                if not flags['main_sent']:
                    if int((time_close - time_now + time_create_trade) / 60) >= 1:
                        await bot.send_message(chat_id,
                                               f'Осталось {int((time_close - time_now + time_create_trade) / 60)} минут(ы), чтобы закрыть заявку!')
                    else:
                        await bot.send_message(chat_id, '⚠️Осталось меньше одной минуты!⚠️')
                    flags['main_sent'] = True
                    if (time_close - time_now + time_create_trade) < 600:
                        flags['sent_10'] = True
                    if (time_close - time_now + time_create_trade) < 300:
                        flags['sent_5'] = True
                    if (time_close - time_now + time_create_trade) < 180:
                        flags['sent_3'] = True
                    if (time_close - time_now + time_create_trade) < 60:
                        flags['sent_1'] = True

                if time_close - time_now + time_create_trade <= 0:
                    data = {
                        'id': str(trade_id),
                        'status': 'delete_on_bot',
                    }
                    edit_operator = {
                        'tg_id': chat_id,
                        'options': {
                            'is_working_now': False,
                            'is_instead': False,
                        }
                    }
                    # for msg_id, u_id in select_message_from_database(chat_id):
                    #     await bot.delete_message(chat_id, msg_id)
                    #     delete_from_database(chat_id, msg_id, trade_id, trade_type)
                    edit_operator_options = requests.post(URL_DJANGO + 'edit_agent_status/', json=edit_operator)
                    delete_trade_on_bot = requests.post(URL_DJANGO + f'update/{url_type}/trade/', json=data)
                    await state.finish()
                    body = {
                        'tg_id': chat_id,
                    }
                    r = requests.get(URL_DJANGO + 'get_agent_info/', json=body)
                    if r.status_code == 200:
                        data = r.json()
                    await bot.send_message(chat_id,
                                           'Время на закрытие заявки истекло! \nОбратитесь в техподдержку, если вы отправили деньги на указанные реквизиты',
                                           reply_markup=update_keyboard(data['income_operator'], 'Закончить смену' if data['is_instead'] else 'Начать смену'))
                    t = trade_info[trade_type]
                    try:
                        await bot.edit_message_text(chat_id=CHANNEL_ID, message_id=t['channel_message_id'],
                                                text=f'🔴 {t["platform_id"]} : {paymethod[t["paymethod"]]} : {t["amount"]} : {data["user_name"]} : timeout')
                    except Exception as e:
                        print(e)
                elif time_close - time_now + time_create_trade <= 60 and not flags['sent_1'] and flags['main_sent']:
                    await bot.send_message(chat_id, '⚠️Заявка долго в работе, осталась 1 минута!⚠️')
                    flags['sent_1'] = True
                elif time_close - time_now + time_create_trade <= 180 and not flags['sent_3']:
                    await bot.send_message(chat_id, '⚠️Заявка долго в работе, осталось 3 минуты!⚠️')
                    flags['sent_3'] = True
                elif time_close - time_now + time_create_trade <= 300 and not flags['sent_5']:
                    await bot.send_message(chat_id, '⚠️Заявка долго в работе, осталось 5 минут!⚠️')
                    flags['sent_5'] = True
                elif time_close - time_now + time_create_trade <= 600 and not flags['sent_10']:
                    await bot.send_message(chat_id, '⚠️Заявка долго в работе, осталось 10 минут!⚠️')
                    flags['sent_10'] = True
            else:
                break
        await asyncio.sleep(5)

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
        if r.json()[0]['is_working_now'] == False and r.json()[0]['active_card']:

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
                get_pay_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')
                if (get_pay_info.status_code == 200):
                    if (not get_pay_info.json()[trade_type]['agent'] or str(
                            get_pay_info.json()[trade_type]['agent']) == str(
                        call.from_user.id)) and \
                            get_pay_info.json()[trade_type]['status'] != 'closed' and get_pay_info.json()[trade_type][
                        'status'] != 'time_cancel' and get_pay_info.json()[trade_type]['status'] != 'cancel' and \
                            get_pay_info.json()[trade_type]['status'] != 'canceled':

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
                                asyncio.create_task(
                                    waiting_close(trade_id, url_type, trade_type, call.from_user.id, state))
                                # await waiting_close(get_current_info.json()[trade_type]['platform_id'], url_type, call.from_user.id)
                                await call.answer('Вы успешно взяли заявку в работу!', show_alert=True)
                                msg = await call.message.edit_text(f'''

Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *заявка за вами, пришлите номер карточки в чат, чтобы продолжить.*

                ''', parse_mode='Markdown')
                                t = get_current_info.json()[trade_type]
                                print(t)
                                try:
                                    await bot.edit_message_text(chat_id=CHANNEL_ID, message_id=t['channel_message_id'],
                                                             text=f'🟡 {t["platform_id"]} : {paymethod[t["paymethod"]]} : {t["amount"]} : @{call.from_user.username}')
                                except Exception as e:
                                    print(e)
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
                                await Activity.check_card.set()

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
                    await call.answer('Произошла ошибка, вероятно заявки не существует.', show_alert=True)
                    await call.message.delete()
        else:
            if r.json()[0]['is_working_now'] == True:
                await call.answer('У вас уже есть активная сделка, выполните её.', show_alert=True)
            elif not r.json()[0]['active_card']:
                await call.answer('У вас нет активной карточки! Свяжитесь с диспетчером.', show_alert=True)
    else:
        await call.answer('Вы не зарегистрированы.', show_alert=True)
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
                            # delete_from_database(call.from_user.id, msg, trade_id_db, url_type)
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


@dp.message_handler(state=Activity.check_card)
async def check_card(message: types.Message, state=FSMContext):
    data = await state.get_data()
    id = data['id']
    msg_id = data['message_id']
    trade_type = data['trade_type']
    url_type = data['url_type']
    type = data['type']
    kb_accept_cancel_payment = create_accept_cancel_kb(id, type)

    get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')

    try:
        await bot.delete_message(message.chat.id, msg_id)
        print(msg_id)
    except Exception as e:
        print(e)
    delete_from_database(message.from_user.id, msg_id, id, url_type)
    print('udalili')

    if (get_current_info.json()[trade_type]['card_number'] == message.text):
        msg = await message.reply(f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *заявка за вами, оплачиваем и присылаем чек*

    ''', reply_markup=kb_accept_cancel_payment, parse_mode='Markdown')
        add_to_database(message.from_user.id, msg.message_id, id, trade_type)
        print('dobavili', msg.message_id)
        await state.update_data(id=id, type=type, message_id=msg.message_id, url_type=url_type,
                                trade_type=trade_type)
        await Activity.acceptPayment.set()
    else:
        msg = await message.reply(f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *некорректные реквизиты, введите снова*

    ''', parse_mode='Markdown')
        add_to_database(message.from_user.id, msg.message_id, id, trade_type)
    await state.update_data(id=id, type=type, message_id=msg.message_id, url_type=url_type,
                            trade_type=trade_type)


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
    await state.update_data(id=callback_data['id'], type=callback_data['type'], message_id=msg.message_id)
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
    msg = await call.message.edit_text(f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *заявка отменена из-за нехватки баланса*
                ''', parse_mode='Markdown')

    for msg_id, trade_id in select_message_from_database(call.from_user.id):
        if trade_id == id:
            delete_from_database(call.message.chat.id, msg_id, id, trade_type)
    t = get_current_info.json()[trade_type]
    try:
        await bot.edit_message_text(chat_id=CHANNEL_ID, message_id=t['channel_message_id'],
                               text=f'🔴 {t["platform_id"]} : {paymethod[t["paymethod"]]} : {t["amount"]} : @{call.from_user.username} : no balance')
    except Exception as e:
        print(e)
    await state.finish()


@dp.message_handler(state=Activity.add_reason_cancel)
async def other_case_cancel(message: types.Message, state=FSMContext):
    state_data = await state.get_data()
    try:
        await bot.delete_message(message.chat.id, state_data['message_id'])
    except Exception as e:
        print(e)
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
        'comment': message.text
    }

    update_status = requests.post(URL_DJANGO + f'update/{url_type}/trade/', json=data)

    get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')

    msg = await message.reply(f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *заявка отменена из-за проблемы отправки*

        ''', parse_mode='Markdown')
    for msg_id, trade_id in select_message_from_database(message.from_user.id):
        if trade_id == id:
            delete_from_database(message.from_user.id, msg_id, id, trade_type)
    print('udalili', msg.message_id)
    t = get_current_info.json()[trade_type]
    try:
        await bot.edit_message_text(chat_id=CHANNEL_ID, message_id=t['channel_message_id'],
                               text=f'🔴 {t["platform_id"]} : {paymethod[t["paymethod"]]} : {t["amount"]} : @{message.from_user.username} : reason')
    except Exception as e:
        print(e)
    await state.finish()


@dp.message_handler(content_types=['photo', 'document'], state=Activity.acceptPayment)
async def get_photo(message: types.Message, state=FSMContext):
    data = await state.get_data()
    trade_type = data['trade_type']
    url_type = data['url_type']
    id = data['id']
    msg_id = data['message_id']
    file_name = f'/root/dev/SkillPay-Django/{url_type}/{id}_{message.from_user.id}.pdf'
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
        try:
            await bot.delete_message(chat_id=message.from_user.id, message_id=msg_id)
        except Exception as e:
            print(e)

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
            # print(''.join(text.split()[2:4]), text.split()[10], text.split()[20][1:],  get_current_info.json()[trade_type]['card_number'][12:16])
        amount = ''
        status = ''
        card_number = ''
        text = text.split('\n')
        try:
            if get_current_info.json()['validate_check']:
                if paymethod[get_current_info.json()[trade_type]['paymethod']] == 'TINK':
                    amount = re.sub('[,]', '.', re.sub('[^0-9,]', '', text[1]))
                    status = text[4].split()[1]
                    card_number = re.sub('[^0-9]', '', text[7])
                elif paymethod[get_current_info.json()[trade_type]['paymethod']] == 'SBER':
                    amount = re.sub('[,]', '.', re.sub('[^0-9,]', '', text[14]))
                    card_number = re.sub('[^0-9]', '', text[8])
        except Exception as e:
            print('ERROR CHECK', e)
        print(amount, status, card_number, get_current_info.json()['validate_check'])

        if (
                (paymethod[get_current_info.json()[trade_type]['paymethod']] == 'TINK' and
                 amount in get_current_info.json()[trade_type]['amount'] and
                 'Успешно' in status and
                 card_number in get_current_info.json()[trade_type]['card_number'])
                or
                (paymethod[get_current_info.json()[trade_type]['paymethod']] == 'SBER' and
                 amount in get_current_info.json()[trade_type]['amount'] and
                 card_number in get_current_info.json()[trade_type]['card_number'])

                or not get_current_info.json()['validate_check']):
            data = {
                'id': id,
                'cheque': f'{url_type}/{id}_{message.from_user.id}.pdf'
            }

            upload = requests.post(URL_DJANGO + f'update/{url_type}/trade/', json=data)

            if url_type == 'bz':
                get_trade_detail = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')
                key = get_trade_detail.json()['user']['key']
                proxy = get_trade_detail.json()['user']['proxy']
                email = get_trade_detail.json()['user']['email']
                print(file_name, file_name[0: len(file_name) - 4] + '.jpg')
                pages = convert_from_path(file_name)

                for i in range(len(pages)):
                    pages[i].save(file_name[0: len(file_name) - 4] + '.jpg', 'JPEG')
                file_name = file_name[0: len(file_name) - 4] + '.jpg'
                send_message = f'https://bitzlato.net/api/p2p/trade/{id}/chat/'
                headers = authorization(key, email)
                data_message = {
                    'message': 'Оплатил.',
                    'payload': {
                        'message': 'string'
                    }
                }
                # send_message_req = requests.post(send_message, headers=headers, proxies=proxy, json=data_message)
                url = f'https://bitzlato.net/api/p2p/trade/{id}/chat/sendfile'

                data = {
                    'mime_type': 'image/png',
                    'name': 'Check.png'
                }
                files = {'file': open(file_name, 'rb')}

                headers = authorization(key, email)

                r = requests.post(url, headers=headers, proxies=proxy, files=files)

                headers = authorization(get_trade_detail.json()['user']['key'],
                                        get_trade_detail.json()['user']['email'])

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
                data_garantex = {'deal_id': id}
                files = {'file': open(file_name, 'rb')}

                message_request = requests.post(f'https://garantex.io/api/v2/otc/chats/message',
                                                headers=header, data=data_garantex, files=files)
                jwt = get_jwt(uid=trade_detail['auth']['uid'], private_key=trade_detail['auth']['private_key'])
                header = {
                    'Authorization': f'Bearer {jwt}'
                }
                req_accept_payment = requests.put(f'https://garantex.io/api/v2/otc/deals/{id}/set_paid', headers=header)
                print(message_request.status_code, message_request.text)
            while 1:
                try:
                    req = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{id}/')
                    if req.status_code == 200:
                        trade_info = req.json()
                        if trade_info[trade_type]['status'] == 'confirm_payment' or trade_info[trade_type][
                            'status'] == 'completed':
                            body = {
                                'tg_id': message.from_user.id,
                                'options': {
                                    'is_working_now': False,
                                }
                            }

                            change_status_agent = requests.post(URL_DJANGO + 'edit_agent_status/', json=body)

                            if change_status_agent.status_code == 200:
                                body = {
                                    'tg_id': message.from_user.id,
                                }
                                req_info_agent = requests.post(URL_DJANGO + 'get_agent_info/', json=body)
                                print(req_info_agent.json())
                                data = req_info_agent.json()[0]
                                if data['is_instead']:
                                    temp = "Закончить смену"
                                else:
                                    temp = "Начать смену"
                                reply_markup = update_keyboard(data['income_operator'], temp)
                                for msg_id, trade_id in select_message_from_database(message.from_user.id):
                                    if trade_id == id:
                                        delete_from_database(message.from_user.id, msg_id, id, trade_type)
                                #await bot.delete_message(chat_id=message.from_user.id, message_id=msg.message_id)
                                # delete_from_database(message.from_user.id, msg_id, id, trade_type)
                                await bot.send_message(chat_id=message.from_user.id,
                                                            text=f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Инструмент: {paymethod[get_current_info.json()[trade_type]['paymethod']]}
–––
Сумма: `{get_current_info.json()[trade_type]['amount']}` 
–––
Адресат: {get_current_info.json()[trade_type]['card_number']}
–––
Статус: *успешно оплачена и закрыта*

                    ''', reply_markup=reply_markup, parse_mode='Markdown')

                                print('aaaaaaaaaaaaaaaaaaaaaaaaaaa', message.from_user.id)
                                try:
                                    data = {
                                        "tg_id": message.from_user.id
                                    }
                                except Exception as e:
                                    print(e)

                                get_agent_info_req = requests.post(URL_DJANGO + 'get_agent_info/', json=data)
                                print("BEBRA", get_agent_info_req, get_agent_info_req.json(), message.from_user.id,
                                      "LEBRA")
                                agent = ''
                                if get_agent_info_req.status_code == 200:
                                    agent = get_agent_info_req.json()[0]['user_name']
                                print(get_current_info.json())
                                t = get_current_info.json()[trade_type]
                                await bot.edit_message_text(chat_id=CHANNEL_ID, message_id=t['channel_message_id'],
                                                            text=f'🟢 {t["platform_id"]} : {paymethod[t["paymethod"]]} : {t["amount"]} : {data["user_name"]}')

                                # msg = await message.answer("Обновление баланса🆙", reply_markup=reply_markup=update_keyboard(data['income_operator'], "Начать смену"))
                            else:
                                await message.answer('Произошла ошибка, свяжитесь с админом.')

                            await state.finish()
                            break
                    await asyncio.sleep(1)

                except Exception as e:
                    print(e)
                    await asyncio.sleep(10)
                    continue
        else:
            get_dispatchers = requests.get(URL_DJANGO + 'get/dispatchers/')
            dispatcher_id = get_dispatchers.json()
            body = {
                'tg_id': message.from_user.id
            }
            r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)
            get_agent_name = r.json()[0]['user_name']
            for i in dispatcher_id:
                try:
                    await bot.send_message(chat_id=i, text=f'''
Заявка: {get_current_info.json()[trade_type]['platform_id']}
Агент: {get_agent_name}
Ошибка чека.
                ''')
                except Exception as e:
                    print(e)
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
            await state.update_data(message_id=msg.message_id)

            await Activity.acceptPayment.set()
    else:
        await message.reply(text='Вы отправили чек не в том формате, пришлите заново в формате png')


@dp.callback_query_handler(text='Назад')
async def back(call: types.CallbackQuery):
    await call.message.edit_text('Меню', reply_markup=kb_menu_main)
