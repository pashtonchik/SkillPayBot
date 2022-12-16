import asyncio

from aiogram import types
from aiogram.dispatcher.storage import FSMContext
from keyboards.inline.ikb import confirm_kb, create_ikb, cancel_cb
from keyboards.inline.mainMenu import kb_accept_cancel_withdraw
from loader import dp, bot
from settings import URL_DJANGO
from states.courier_states import CourierCashin, CourierCashOut, Withdraw
from aiogram.utils.exceptions import ChatNotFound
from .cashin_start import send_cashin_menu
import requests
from aiogram.utils.exceptions import MessageToDeleteNotFound


@dp.callback_query_handler(text='Вывод')
async def input_withdraw_amount(callback_query: types.CallbackQuery, state: FSMContext):
    body = {
        'tg_id': callback_query.from_user.id
    }
    r = requests.post(URL_DJANGO + 'get_agent_info/', json=body)
    print(r.status_code, r.json())
    if r.status_code == 200:
        operator_info = r.json()[0]
        if operator_info['is_working_now']:
            await callback_query.answer(text='Сначала завершите заявку!', show_alert=True)
            await state.finish()
            # удалить старое сообщение
        elif not operator_info['income_operator'] or float(operator_info['income_operator']) < 0 :
            await callback_query.answer(text='Вывод недоступен!', show_alert=True)
            # удалить старое сообщение
            await state.finish()
        else:
            await callback_query.message.edit_text(
                text=f'Сумма доступная к выводу: {operator_info["income_operator"]}RUB',
                reply_markup=kb_accept_cancel_withdraw)
            await state.update_data(balance_operator=operator_info['income_operator'])
            await Withdraw.close_withdraw.set()
    else:
        await callback_query.message.edit_text(text='Возникла ошибка на сервере, попробуйте позже',
                                               reply_markup=kb_accept_cancel_withdraw)


@dp.callback_query_handler(text='accept_withdraw', state=Withdraw.close_withdraw)
async def info_accept_withdraw(callback_query: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    req_accept_withdraw = requests.post(URL_DJANGO + f'create/withdraw/req/{callback_query.from_user.id}/')
    if req_accept_withdraw.status_code == 200:
        await callback_query.message.edit_text(
            text=f'Вывод средств: \n------------- \nСумма: {state_data["balance_operator"]}\n------------- \nЗаявка на рассмотрении у диспетчера, ожидайте выплаты')
        await state.finish()

    elif req_accept_withdraw.status_code == 207:
        await callback_query.message.edit_text(text='Вы уже запросили вывод, ожидайте проверки!')
        await state.finish()
    else:
        await callback_query.message.edit_text(text='Произошла ошибка на сервере, попробуйте позже')
        await state.finish()



@dp.callback_query_handler(text='cancel_withdraw', state=Withdraw.close_withdraw)
async def info_cancel_withdraw(callback_query: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    await callback_query.message.edit_text(
        text=f'Вывод средств: \n------------- \nСумма: {state_data["balance_operator"]}\n------------- \nЗаявка на вывод средств отменена')
    await state.finish()
