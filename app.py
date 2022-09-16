import asyncio
from aiogram import executor
import requests
from requests import ConnectTimeout

from loader import dp, bot
import middlewares, filters, handlers
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData

URL_DJANGO = 'http://194.58.92.160:8001/'
URL_BZ = 'https://bitzlato.com/'

async def check_trades(dp):
    
    while 1:
        #
        # Запрос к БД на получение всех кайфаларов
        #
        try:
            req_django = requests.get(URL_DJANGO + 'api/trades/active/')
            print(req_django.json(), req_django.status_code)
            if req_django.status_code == 200:
                trades = req_django.json()
                if len(trades) > 0:
                    for trade in trades:
                        trade_cb = CallbackData("trade", "id", "action")
                        kb_accept_order = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(text='Принять заявку', callback_data=trade_cb.new(id=trade, action='accept_trade'))
                                ]
                            ]
                        )
                        get_active_agent = requests.get(URL_DJANGO + 'api/get/active/agents')
                        req_trade_info = requests.get(URL_DJANGO + f'api/trade/detail/{trade}')
                        print(req_trade_info.status_code, req_trade_info.text)
                        trade_info = req_trade_info.json()

                        for i in get_active_agent.json():
                            try:
                                await bot.send_message(int(i), f'''
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
            await asyncio.sleep(1)
        except Exception as e:
            print(type(e), ' ', e)
            continue

async def on_startup(dispatcher):
    # Устанавливаем дефолтные команды
    await set_default_commands(dispatcher)
    asyncio.create_task(check_trades(dp=dp))

    # Уведомляет про запуск
    await on_startup_notify(dispatcher)


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)