from aiogram import types
from aiogram.dispatcher.storage import FSMContext
from keyboards.inline.ikb import *
from loader import dp, bot
from settings import URL_DJANGO
from states.courier_states import CourierCashin, CourierCashOut
from aiogram.utils.exceptions import ChatNotFound
from .cashin_start import send_cashin_menu
import requests
from aiogram.utils.exceptions import MessageToDeleteNotFound


@dp.callback_query_handler(text='ccancel', state='*')
async def ccansel(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await callback_query.message.edit_text('Операция отменена')
    await send_cashin_menu(callback_query.message)


async def notify_dispatchers(text, amount, courier, card_number=None, operator_name=None):
    r = requests.get(URL_DJANGO + 'dispatcher/').json()
    text_message = f'{text}\nКурьер: {courier}\nСумма: {amount}'
    if operator_name:
        text_message += f'\nОператор: {operator_name}\nКарта: {card_number}'
    if r:
        for dispatcher in r:
            try:
                await bot.send_message(
                    chat_id=dispatcher['tg_id'],
                    text=text_message
                )
            except ChatNotFound:
                pass


@dp.callback_query_handler(text='cashin', state=None)
async def use_cashin_button_courier(callback_query: types.CallbackQuery, state: FSMContext):
    await CourierCashin.input_amount.set()
    await state.update_data({'msg': callback_query.message.message_id})
    await callback_query.message.edit_text(text='Введите колическов средств, которые вы хотите зафиксировать', reply_markup=cancel_cb)


@dp.message_handler(state=CourierCashin.input_amount)
async def input_amount_courier_cashin(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    try:
        await bot.delete_message(message.chat.id, state_data['msg'])
    except MessageToDeleteNotFound:
        pass
    try:
        amount = float(message.text)
        if amount < 0:
            raise ValueError
        elif amount == 0:
            await state.finish()
            await message.answer('Операция отменена')
        else:
            req = requests.get(
                url=URL_DJANGO + f'user/{message.from_user.id}/')
            if req.status_code == 200:
                account_balance = req.json()['balance_courier']
                if account_balance >= amount:
                    operators = requests.get(URL_DJANGO + 'operators/').json()
                    lables = [i['user_name'] for i in operators]
                    callbacks = [i['tg_id'] for i in operators]
                    ikb = create_ikb(lables, callbacks)
                    msg = await message.answer(text='Выберите оператора', reply_markup=ikb)
                    await state.update_data(msg=msg.message_id, id=msg.chat.id, amount=amount)
                    await CourierCashin.choose_operator.set()
                else:
                    await message.answer('Недостаточно средств на счету')
            else:
                await message.answer(f'Ошибка при отправке запроса на сервер\nкод ошибки: {req.status_code}')
                await state.finish()

    except ValueError:
        await CourierCashin.input_amount.set()
        await message.answer('Значение указанно не верно.\nЕсли вы хотите отменить кэшин введите 0')


@dp.callback_query_handler(lambda c: c.data.startswith('ikb_'), state=CourierCashin.choose_operator)
async def input_amount_courier_cashin(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'ikb_cancel':
        await ccansel(call, state)
        return None
    state_data = await state.get_data()
    req = requests.get(url=URL_DJANGO + f'user/{call.from_user.id}/')
    if req.status_code == 200:
        cards = requests.get(
            URL_DJANGO + f'operator/{call.data[4:]}/cards/').json()
        lables = [i['card_number'] for i in cards]
        callbacks = [i['id'] for i in cards]
        ikb = create_ikb(lables, callbacks)
        msg = await call.message.edit_text(text='Выберите карту оператора', reply_markup=ikb)
        await state.update_data(msg=msg.message_id,
                                id=msg.chat.id,
                                amount=state_data['amount'],
                                operator=call.data[4:],
                                )
        print(call.data)
        await CourierCashin.choose_card.set()
    else:
        await call.message.answer(f'Ошибка при отправке запроса на сервер\nкод ошибки: {req.status_code}')
        await state.finish()


@dp.callback_query_handler(lambda c: c.data.startswith('ikb_'), state=CourierCashin.choose_card)
async def select_operator_cashin(callback_query: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    print(state_data)
    if callback_query.data == 'ikb_cancel':
        await bot.edit_message_text(
            message_id=state_data['msg'],
            chat_id=state_data['id'],
            text='Операция отменена'
        )
        await state.finish()
    else:
        try:
            operator_req = requests.get(
                URL_DJANGO + f'operators/{state_data["operator"]}/')
            card_operators_req = requests.get(
                URL_DJANGO + f'get/card/{callback_query.data[4:]}/')
            if operator_req.status_code != 200 or card_operators_req.status_code != 200:
                raise Exception(
                    f'req status code: {operator_req.status_code}')
            operator = operator_req.json()
            card = card_operators_req.json()
            # card_number = card_number.json()['card_number']
            print(callback_query.data[4:])
            print(card)
            cur_card = card
            msg = await bot.edit_message_text(
                message_id=state_data['msg'],
                chat_id=state_data['id'],
                text=f'Операция: кэшин \nОператор: {operator["user_name"]} \nКарта: {cur_card["card_number"]} \nСумма: {state_data["amount"]} \nКарта: ************{cur_card["card_number"][-4:]}',
                reply_markup=confirm_kb,
            )
            await state.update_data(
                operator=operator['tg_id'],
                operator_name=operator["user_name"],
                card_id=callback_query.data[4:],
                card_number=cur_card["card_number"]
            )
            await CourierCashin.confirm.set()
        except Exception as e:
            await callback_query.message.answer(
                text='Ошибка на стороне сервера.\n Операция была отменена'
            )
            await state.finish()


@dp.callback_query_handler(text='confirm', state=CourierCashin.confirm)
async def confirm_cashin(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    req = requests.post(
        url=URL_DJANGO + 'courier/cashin/',
        json={
            'tg_id': str(data['id']),
            'amount': data['amount'],
            'operator_id': data['operator'],
            'card_id': data['card_id'],
        }

    )
    if req.status_code == 200:
        await notify_dispatchers(
            amount=data['amount'],
            courier=callback_query.from_user.full_name,
            operator_name=data['operator_name'],
            text=f'Уведомление\nПроизведена операция: кэшин',
            card_number=data['card_number']
        )

        await bot.edit_message_text(
            chat_id=data['id'],
            message_id=data['msg'],
            text=f'Операция: кэшин\nСумма: {data["amount"]}\nОператор: {data["operator_name"]}\n_________________________\nОперация завершена'
        )
        await send_cashin_menu(callback_query.message)
    else:
        await callback_query.message.answer(f'Ошибка при отправке запроса на сервер\nкод ошибки: {req.status_code}')
        print(req.text)
    await state.finish()


@dp.callback_query_handler(text='cashout', state=None)
async def use_cashout_button(callback_query: types.CallbackQuery, state: FSMContext):
    await CourierCashOut.input_amount.set()
    await callback_query.message.edit_text(text='Введите колическов средств, которые вы хотите зафиксировать', reply_markup=cancel_cb)
    await state.update_data({'msg': callback_query.message.message_id})
    print(callback_query.message.message_id)


@dp.message_handler(state=CourierCashOut.input_amount)
async def input_amount_courier_cashout(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    print('state_data  ', state_data)
    try:
        await bot.delete_message(message.chat.id, state_data['msg'])
    except MessageToDeleteNotFound:
        pass
    try:

        amount = float(message.text)
        if amount < 0:
            raise ValueError
        elif amount == 0:
            await state.finish()
            await message.answer('Операция отменена')
            # await send_cashin_menu(message)
        else:
            msg = await message.answer(
                text=f'Подтверждение операции:\n\nЗабор наличных стредств из Garantex\n{amount}',
                reply_markup=confirm_kb
            )
            await state.update_data(amount=amount, msg=msg.message_id, id=msg.chat.id)
            await CourierCashOut.confirm.set()

    except ValueError:
        await CourierCashOut.input_amount.set()
        await message.answer('Значение указанно не верно.\nЕсли вы хотите отменить операцию введите 0')


@dp.callback_query_handler(text='confirm', state=CourierCashOut.confirm)
async def confirm_cashout(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    req = requests.post(
        url=URL_DJANGO + 'courier/cashout/',
        json={
            'tg_id': str(data['id']),
            'amount': data['amount'],
        }
    )
    if req.status_code == 200:
        await notify_dispatchers(
            amount=data['amount'],
            courier=callback_query.from_user.full_name,
            text=f'Уведомление\nПроизведена операция: забор наличных средств с Garantex',
        )
        await bot.edit_message_text(
            chat_id=data['id'],
            message_id=data['msg'],
            text=f'Забор наличных средств из Gatantex\n{data["amount"]}\n_________________________\nОперация завершена',
        )
        await send_cashin_menu(callback_query.message)
    else:
        await callback_query.message.answer(f'Ошибка при отправке запроса на сервер\nкод ошибки: {req.status_code}')
    await state.finish()


@dp.callback_query_handler(lambda c: c.data.startswith('accept_cashout'), state=None)
async def accept_cashout_task(callback_query: types.CallbackQuery, state: FSMContext):
    amount = parce_accept_ikb(callback_query.data)[0]
    await CourierCashOut.confirm_task.set()
    await state.set_data({'amount': amount, 'id': callback_query.message.chat.id, 'msg': callback_query.message.message_id})
    await callback_query.message.edit_text(f'Забор наличных средств из Gatantex\n{amount}\n_________________________\nСумма введена правильно?',
                                           reply_markup=yes_no_kb)


@dp.callback_query_handler(text='yes', state=CourierCashOut.confirm_task)
async def confirm_cashout_task(callback_query: types.CallbackQuery, state: FSMContext):
    await confirm_cashout(callback_query, state)


@dp.callback_query_handler(text='no', state=CourierCashOut.confirm_task)
async def cancel_cashout_task(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback_query.message.edit_text(
        f"Забор наличных средств из Gatantex\n{data['amount']}",
        reply_markup=accept_ikb(f'cashout_{data["amount"]}')
    )
    await state.finish()


@dp.callback_query_handler(lambda c: c.data.startswith('accept_cashin'), state=None)
async def accept_cashin_task(callback_query: types.CallbackQuery, state: FSMContext):
    data = parce_accept_ikb(callback_query.data)
    amount, operator_name, operator_id, card_number, card_id = data
    req = requests.get(
                url=URL_DJANGO + f'user/{callback_query.message.chat.id}/')
    if req.status_code == 200:
        account_balance = req.json()['balance_courier']
        if account_balance >= float(amount):
            await CourierCashin.confirm_task.set()
            msg = await callback_query.message.edit_text(
                text=f'Операция: кэшин \nОператор: {operator_name} \nКарта: {card_number} \nСумма:{amount}\
                    \nКарта: ************{card_number[-4:]}\n_________________________\nПерепроверьте, верна ли заявка?',
                reply_markup=yes_no_kb,
            )
            await state.update_data({'amount': amount, 'operator_name': operator_name,
                                    'operator': operator_id, 'card_id': card_id, 'msg': callback_query.message.message_id,
                                    'id': callback_query.message.chat.id, 'card_number': card_number})
        else:
            await callback_query.answer('Средств на вашем балансе недостаточно!')
    else:
        await callback_query.message.answer(f'Ошибка при отправке запроса на сервер\nкод ошибки: {req.status_code}')
        await state.finish()


@dp.callback_query_handler(text='yes', state=CourierCashin.confirm_task)
async def confirm_cashin_task(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    req = requests.get(
                url=URL_DJANGO + f'user/{callback_query.message.chat.id}/')
    if req.status_code == 200:
        account_balance = req.json()['balance_courier']
        if account_balance >= float(data['amount']):
            await confirm_cashin(callback_query, state)
        else:
            await callback_query.answer('Средств на вашем балансе недостаточно!')
            await cancel_cashout_task(callback_query, state)
    else:
        await callback_query.message.answer(f'Ошибка при отправке запроса на сервер\nкод ошибки: {req.status_code}')
        await state.finish()


@dp.callback_query_handler(text='no', state=CourierCashin.confirm_task)
async def cancel_cashout_task(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback_query.message.edit_text(
        text=f'Операция: кэшин \nОператор: {data["operator_name"]} \nКарта: {data["card_number"]}\
             \nСумма: {data["amount"]} \nКарта: ************{data["card_number"][-4:]}',
        reply_markup=accept_ikb(
            f"cashin_{data['amount']}_{data['operator_name']}_{data['operator']}_{data['card_number']}_{data['card_id']}")
    )
    await state.finish()
