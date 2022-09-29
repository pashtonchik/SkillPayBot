import asyncio
from aiogram import executor
import requests
from loader import dp, bot
from settings import URL_DJANGO, URL_BZ
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData

trade_cb = CallbackData("trade", "type", "id", "action")


async def check_trades(dp):
    
    while 1:
        try:
            req_django = requests.get(URL_DJANGO + 'api/trades/active/')
            print(req_django.json(), req_django.status_code)
            if req_django.status_code == 200:
                trades = req_django.json().get('trades', [])
                pays = req_django.json().get('pays', [])

                for trade in trades:
                    kb_accept_order = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(text='Принять заявку',
                                                     callback_data=trade_cb.new(id=trade,
                                                                                type='BZ',
                                                                                action='accept_trade'
                                                                                )
                                                     )
                            ]
                        ]
                    )
                    get_active_agent = requests.get(URL_DJANGO + 'api/get/active/agents')
                    req_trade_info = requests.get(URL_DJANGO + f'api/trade/detail/{trade}')
                    print(req_trade_info.status_code, req_trade_info.text)
                    trade_info = req_trade_info.json()
                    
                    for i in get_active_agent.json():
                        if i['paymethod_description'] == trade_info['paymethod_description']:
                            try:
                                await bot.send_message(int(i['tg_id']), f'''
    Новая сделка! Покупка {trade_info['trade']['cryptocurrency']} за {trade_info['trade']['currency']}
    Сумма: {trade_info['trade']['currency_amount']} {trade_info['trade']['currency']}
    ''', reply_markup=kb_accept_order)
                            except Exception as e:
                                print(e)
                                continue
                    data = {
                                'id': trade,
                                'is_send': True
                            }
                    update_trade = requests.post(URL_DJANGO + 'api/update/trade/', json=data)
                    print(update_trade.status_code, update_trade.text)
                for pay in pays:
                    kb_accept_order = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(text='Принять заявку',
                                                     callback_data=trade_cb.new(id=pay,
                                                                                type='googleSheets',
                                                                                action='accept_trade'
                                                                                )
                                                     )
                            ]
                        ]
                    )
                    get_active_agent = requests.get(URL_DJANGO + 'api/get/active/agents/')
                    req_pay_info = requests.get(URL_DJANGO + f'api/pay/detail/{pay}/')
                    pay_info = req_pay_info.json()
                    for i in get_active_agent.json():
                        if i['paymethod_description'] == pay_info['paymethod_description']:
                            try:
                                await bot.send_message(int(i['tg_id']), f'''
    Новая сделка! Покупка 
    Сумма: {pay_info['pay']['amount']} RUB
    ''', reply_markup=kb_accept_order)
                            except Exception as e:
                                print(e)
                                continue
                    data = {
                        'id': pay,
                        'is_send': True
                    }
                    update_pay = requests.post(URL_DJANGO + 'api/update/pay/', json=data)
                    print('dasdasdasd' + str(update_pay.status_code))
                    
            await asyncio.sleep(1)
        except Exception as e:
            print(type(e), ' ', e)
            continue


async def on_startup(dispatcher):
    await set_default_commands(dispatcher)
    asyncio.create_task(check_trades(dp=dp))
    await on_startup_notify(dispatcher)


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
