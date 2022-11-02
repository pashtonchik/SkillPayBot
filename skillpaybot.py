import asyncio
from aiogram import executor, types
import requests
import middlewares, filters, handlers
from loader import dp, bot
from settings import URL_DJANGO
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.utils.callback_data import CallbackData
from datetime import datetime
import sqlite3

trade_cb = CallbackData("trade", "type", "id", "action")

def init_database():
    con = sqlite3.connect("message.db")
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS messages (u_id INT, msg_id INT, trade_id INT, type CHAR)""")
    con.commit()
    con.close()

def add_to_database(u_id, msg_id, trade_id, type):
    con = sqlite3.connect("message.db")
    cur = con.cursor()
    cur.execute(f"""INSERT INTO messages (u_id, msg_id, trade_id, type) 
    values ({u_id}, {msg_id}, {trade_id}), {type}""")
    con.commit()
    con.close()

def delete_from_database(trade_id, type):
    con = sqlite3.connect("message.db")
    cur = con.cursor()
    cur.execute(f"""DELETE FROM messages WHERE
    trade_id={trade_id} and type='{type}'""")
    con.commit()
    con.close()

def select_data_from_database(trade_id, type):
    con = sqlite3.connect("message.db")
    cur = con.cursor()
    cur.execute(f"""SELECT u_id, msg_id FROM messages WHERE trade_id={trade_id} and type='{type}'""")
    data = cur.fetchall()
    con.close()
    return data

def select_trades_from_database(type):
    con = sqlite3.connect("message.db")
    cur = con.cursor()
    cur.execute(f"""SELECT DISTINCT trade_id FROM messages WHERE type='{type}'""")
    data = cur.fetchall()
    con.close()
    return data


def create_button_accept(trade_id, trade_type):

    if trade_type == 'trade':
        trade_type = 'BZ'
    elif trade_type == 'pay':
        trade_type = 'googleSheets'

    kb_accept_order = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='Принять заявку',
                                     callback_data=trade_cb.new(id=trade_id,
                                                                type=trade_type,
                                                                action='accept_trade'
                                                                )
                                     )
            ]
        ]
    )
    return kb_accept_order

def create_message_text(trade):
    if trade['type'] == 'trade':
        messageText = f'''
Новая сделка! Покупка {trade['data']['cryptocurrency']} за {trade['data']['currency']}
Сумма: {trade['data']['currency_amount']} {trade['data']['currency']}
'''
    elif trade['type'] == 'pay':
        messageText = f'''
Новая сделка! Покупка 
Сумма: {trade['data']['amount']} RUB
'''
    else:   
        messageText = f'''
Заявка KF - {trade['data']['id']}                     
Инструмент: {trade['data']['type']}
Сумма: {trade['data']['amount']} RUB
                        '''
    return messageText

async def check_trades(dp):
    while 1:
        # try:
        req_django = requests.get(URL_DJANGO + 'trades/active/')
        print(req_django.status_code)
        if req_django.status_code == 200:
            trades = req_django.json()
            print(trades)

            for trade in trades:

                operators = trade['recipients']
                
                kb_accept_order = create_button_accept(trade_id=trade['data']['id'],
                                                                   trade_type=trade['type'])

                for operator in operators:
                    
                    try: 
                        message = await bot.send_message(int(operator), create_message_text(trade), reply_markup=kb_accept_order)
                        add_to_database(message.message_id, message.chat.id, trade['data']['id'], trade['type'])  
                    except Exception as e:
                        print(e)
                        continue
        trades = select_trades_from_database('kf')
        for trade, i in trades:
            tradeDetail = requests.get(URL_DJANGO + f'kf/trade/detail/{trade}/')
            if (tradeDetail.status_code == 200):
                tradeDetail = tradeDetail.json()
                data = select_data_from_database(trade_id=trade, type='kf')
                text = create_message_text(tradeDetail)
                if (tradeDetail['kftrade']['agent']):
                    text = text + \
"""

UPDATE:

Время сделки истекло!

"""
                elif (tradeDetail['kftrade']['status'] == 'closed'):
                    text = text + \
"""

UPDATE:

Время сделки истекло!

"""
                
                for userId, msgId in data:
                    try:
                        await bot.edit_message_text(chat_id=userId, message_id=msgId, text=text, reply_markup=ReplyKeyboardRemove())
                    except Exception as e:
                        print(e)
                        continue
            delete_from_database(trade, 'kf')
        req_kftrades = requests.get(URL_DJANGO + 'get/free/kftrades/')
        kf_trades = req_kftrades.json()

        for trade in kf_trades:
            time_add_kf = datetime.strptime(trade['date_create'].split('.')[0], "%Y-%m-%dT%H:%M:%S").timestamp()
            time_now = datetime.now().timestamp()
            if time_now - time_add_kf > 900:
                data = {
                    'id': trade['id'],
                    'status': 'time_cancel',
                }
                
                update_status = requests.post(URL_DJANGO + 'update/kf/trade/', json=data)

        await asyncio.sleep(1)
        
        # except Exception as e:
        #     print('3', type(e), ' ', e)
        #     continue


async def on_startup(dispatcher):
    await set_default_commands(dispatcher)
    asyncio.create_task(check_trades(dp=dp))
    await on_startup_notify(dispatcher)


if __name__ == '__main__':
    init_database()
    executor.start_polling(dp, on_startup=on_startup)
