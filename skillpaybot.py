import asyncio
from aiogram import executor, types
import requests
import middlewares, filters, handlers
from loader import dp, bot
from settings import URL_DJANGO
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData

trade_cb = CallbackData("trade", "type", "id", "action")


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

                for operator in operators:
                    if trade['type'] == 'trade':
                        try:
                            kb_accept_order = create_button_accept(trade_id=trade['data']['id'], trade_type=trade['type'])
                            await bot.send_message(int(operator), f'''
Новая сделка! Покупка {trade['data']['cryptocurrency']} за {trade['data']['currency']}
Сумма: {trade['data']['currency_amount']} {trade['data']['currency']}
''', reply_markup=kb_accept_order)
                        except Exception as e:
                            print('2', e)
                            continue
                    elif trade['type'] == 'pay':
                        try:
                            kb_accept_order = create_button_accept(trade_id=trade['data']['id'], trade_type=trade['type'])
                            await bot.send_message(int(operator), f'''
Новая сделка! Покупка 
Сумма: {trade['data']['amount']} RUB
''', reply_markup=kb_accept_order)
                        except Exception as e:
                            print('1', e)
                            continue
                    else:
                        try:
                            kb_accept_order = create_button_accept(trade_id=trade['data']['id'],
                                                                   trade_type=trade['type'])
                            await bot.send_message(int(operator), f'''
Заявка KF - {trade['data']['id']}                     
Инструмент: {trade['data']['type']}
Сумма: {trade['data']['amount']} RUB
                        ''', reply_markup=kb_accept_order)
                        except Exception as e:
                            print('1', e)
                            continue
        await asyncio.sleep(1)
        # except Exception as e:
        #     print('3', type(e), ' ', e)
        #     continue


async def on_startup(dispatcher):
    await set_default_commands(dispatcher)
    asyncio.create_task(check_trades(dp=dp))
    await on_startup_notify(dispatcher)


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
