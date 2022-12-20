import asyncio
from aiogram import executor, types
import requests
from aiogram.utils.exceptions import MessageToDeleteNotFound

import middlewares, filters, handlers
from data.config import CHANNEL_ID
from loader import dp, bot
from settings import URL_DJANGO
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.utils.callback_data import CallbackData
from datetime import datetime
import sqlite3

trade_cb = CallbackData("trade", "type", "id", "action")

paymethod = {
    443 : 'TINK',
    3547 : 'SBER'
}

def init_database():
    con = sqlite3.connect("message.db")
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS messages (u_id INT, msg_id INT, trade_id CHAR, type CHAR)""")
    con.commit()
    con.close()


def add_to_database(u_id, msg_id, trade_id, type):
    con = sqlite3.connect("message.db")
    cur = con.cursor()
    cur.execute(f"""INSERT INTO messages (u_id, msg_id, trade_id, type) 
    values ({u_id}, {msg_id}, '{trade_id}', '{type}')""")
    con.commit()
    con.close()


def delete_from_database(u_id, msg_id, trade_id, type):
    con = sqlite3.connect("message.db")
    cur = con.cursor()
    cur.execute(f"""DELETE FROM messages WHERE u_id={u_id} and msg_id={msg_id} 
    and trade_id='{trade_id}' and type='{type}'""")
    con.commit()
    con.close()


def select_data_from_database(trade_id, type):
    con = sqlite3.connect("message.db")
    cur = con.cursor()
    cur.execute(f"""SELECT u_id, msg_id FROM messages WHERE trade_id='{trade_id}' and type='{type}'""")
    data = cur.fetchall()
    con.close()
    return data


def select_message_from_database(u_id):
    con = sqlite3.connect("message.db")
    cur = con.cursor()
    cur.execute(f"""SELECT msg_id, trade_id FROM messages WHERE u_id={u_id}""")
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
    if trade_type == 'bz':
        trade_type = 'bz'
    elif trade_type == 'pay':
        trade_type = 'googleSheets'
    elif trade_type == 'gar_trade':
        trade_type = 'garantex'

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
    messageText = f'''
Заявка: {trade['data']['platform_id']}
Инструмент: {paymethod[trade['data']['paymethod']]}
–––
Сумма: `{trade['data']['amount']}` 
–––
Статус: *свободная*

'''
    return messageText


def edited_message_text(trade):
    messageText = f'''
Заявка: {trade['platform_id']}
Инструмент: {paymethod[trade['paymethod']]}
–––
Сумма: `{trade['amount']}` 
–––
Статус: *свободная*

'''
    return messageText


async def check_trades(dp):
    while 1:
        try:
            req_django = requests.get(URL_DJANGO + 'trades/active/')
            if req_django.status_code == 200:
                trades = req_django.json()
                print(trades)

                for trade in trades:
                    print(trade)
                    if not trade['data']['channel_message_id']:
                        t = trade['data']
                        msg = await bot.send_message(chat_id=CHANNEL_ID, text=f'🆕 {t["platform_id"]} : {paymethod[t["paymethod"]]} : {t["amount"]}')
                        data_add_message = {
                            'type': trade['type'],
                            'channel_message_id': msg.message_id,
                        }
                        req_add_message = requests.post(URL_DJANGO + f'add/channel/message/id/{trade["data"]["id"]}/', json=data_add_message)
                    operators = trade['recipients']
                    kb_accept_order = create_button_accept(trade_id=trade['data']['id'],
                                                        trade_type=trade['type'])
                    for operator in operators:

                        message = await bot.send_message(int(operator), create_message_text(trade), \
                                                        reply_markup=kb_accept_order, parse_mode='Markdown')
                        add_to_database(message.chat.id, message.message_id, trade['data']['id'], trade['type'])
            trades = select_trades_from_database('kf')
            for trade in trades:
                trade = trade[0]
                tradeDetail = requests.get(URL_DJANGO + f'kf/trade/detail/{trade}/')
                if tradeDetail.status_code == 200:
                    tradeDetail = tradeDetail.json()
                    data = select_data_from_database(trade_id=trade, type='kf')
                    text = edited_message_text(tradeDetail['kftrade'])
                    if tradeDetail['kftrade']['status'] == 'closed' or tradeDetail['kftrade']['status'] == 'time_cancel':
                        for userId, msgId in data:
                            try:
                                if str(tradeDetail['kftrade']['agent']) != str(userId):
                                    await bot.delete_message(chat_id=userId, message_id=msgId)
                            except Exception as e:
                                print(e)
                                continue
                            # finally:
                            #     delete_from_database(userId, msgId, trade, 'kf')

            trades = select_trades_from_database('bz')
            for trade in trades:



                trade = trade[0]
                tradeDetail = requests.get(URL_DJANGO + f'bz/trade/detail/{trade}/')

                if tradeDetail.status_code == 200:
                    tradeDetail = tradeDetail.json()
                    data = select_data_from_database(trade_id=trade, type='bz')
                    text = edited_message_text(tradeDetail['bz'])
                    if tradeDetail['bz']['agent'] or tradeDetail['bz']['status'] == 'closed' or \
                        tradeDetail['bz']['status'] == 'time_cancel' or tradeDetail['bz']['status'] == 'cancel':
                        for userId, msgId in data:
                            try:
                                if str(tradeDetail['bz']['agent']) != str(userId):
                                    await bot.delete_message(chat_id=userId, message_id=msgId)
                            except Exception as e:
                                print(e)
                                continue
                            finally:
                                delete_from_database(userId, msgId, trade, 'bz')

            req_kftrades = requests.get(URL_DJANGO + 'get/free/kftrades/')
            kf_trades = req_kftrades.json()

            for trade in kf_trades:
                time_add_kf = datetime.strptime(trade['date_create'].split('.')[0], "%Y-%m-%dT%H:%M:%S").timestamp()
                time_now = datetime.now().timestamp()
                if time_now - time_add_kf > int(trade['time_close']) * 60:
                    data = {
                        'id': trade['id'],
                        'status': 'time_cancel',
                    }

                    update_status = requests.post(URL_DJANGO + 'update/kf/trade/', json=data)

            gar_trades_db = select_trades_from_database('gar_trade')
            if gar_trades_db:
                gar_trades = [i[0] for i in gar_trades_db]
                gar_trades = list(set(gar_trades))
            else:
                gar_trades = None
            req = {
                'gar_trade': gar_trades
            }
            if gar_trades:
                gar_trades_data = requests.post(URL_DJANGO + 'get/active/trades/for/delete/', json=req)
                status_code = gar_trades_data.status_code
            else:
                status_code = 0
            if status_code == 200:
                gar_trades_data = gar_trades_data.json()['gar_trade']
                for trade in gar_trades_data:
                    msgs = select_data_from_database(trade['id'], 'gar_trade')
                    if trade['status'] in ['canceled', 'completed'] or trade['agent']:
                        for userId, msgId in msgs:
                            try:
                                if str(userId) != str(trade['agent']):
                                    await bot.delete_message(userId, msgId)
                            except MessageToDeleteNotFound:
                                pass
                            finally:
                                delete_from_database(
                                        u_id=userId, msg_id=msgId,
                                        trade_id=trade['id'], type='gar_trade')
        except Exception as e:
            print(e)
            continue
        finally:
            await asyncio.sleep(1)

async def set_default_commands(dp):
    await dp.bot.set_my_commands([
        types.BotCommand("start", "Меню SkillPay"),
        types.BotCommand("help", "Помощь"),
        # types.BotCommand("cashin", "Для диспетчеров и курьеров"),
    ])

async def on_startup(dispatcher):
    await set_default_commands(dispatcher)
    asyncio.create_task(check_trades(dp=dp))
    await on_startup_notify(dispatcher)


if __name__ == '__main__':
    init_database()
    executor.start_polling(dp, on_startup=on_startup)
