from aiogram import types
from aiogram.dispatcher.storage import FSMContext
from keyboards.inline.ikb import confirm_kb, create_ikb, cancel_cb, accept_ikb
from loader import dp, bot
from settings import URL_DJANGO
from states.dispatcher_states import DispatcherCashin, DispatcherCashOut
from aiogram.utils.exceptions import ChatNotFound
import requests
from .courier import cancel_cb
from .cashin_start import send_cashin_menu
from aiogram.utils.exceptions import MessageToDeleteNotFound
from .cashin_start import ccansel


async def notifiy_couriers(text, amount, card_number=None, operator_name=None, ikb=None):
    r = requests.get(URL_DJANGO + 'courier/').json()
    text_message = f'{text}\nСумма:{amount}'
    if operator_name:
        text_message += f'\nОператор: {operator_name} \nКарта: {card_number}'
    if r:
        for courier in r:
            try:
                await bot.send_message(
                    chat_id=courier['tg_id'],
                    text=text_message,
                    reply_markup=ikb,
                )
            except ChatNotFound:
                pass


@dp.callback_query_handler(text='dis_operators')
async def print_operators(callback_query: types.CallbackQuery):
    req = requests.get(URL_DJANGO+'operators/')
    if req.status_code != 200:
        await callback_query.message.answer(f'Ошибка соединения с серверов\nкод ошибки: {req.status_code}')
    else:
        operators = req.json()
        if operators != []:
            answer_text = 'Cписок операторов:\n\n'
            for i in operators:
                answer_text += f'{i["user_name"]}\n'
        else:
            answer_text = 'В базе нет операторов'
        await callback_query.message.answer(answer_text)


@dp.callback_query_handler(text='dis_cashin', state=None)
async def use_cashin_button_dispatcher(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text('Введите колическов средств', reply_markup=cancel_cb)
    await DispatcherCashin.input_amount.set()
    await state.update_data({'msg':callback_query.message.message_id})


@dp.message_handler(state=DispatcherCashin.input_amount)
async def input_amount_dispatcher_cashout(message: types.Message, state: FSMContext):
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
            await send_cashin_menu(message, state)
        else:
            operators = requests.get(URL_DJANGO+'operators/').json()
            # print(operators)
            lables = [f"{i['user_name']} | {i['active_card']['card_number'][:4]}" for i in operators]
            callbacks = [i['tg_id'] for i in operators]
            ikb = create_ikb(lables, callbacks)
            msg = await message.answer(text='Выберите оператора', reply_markup=ikb)
            await state.update_data(msg=msg.message_id, id=msg.chat.id, amount=amount)
            await DispatcherCashin.choose_operator.set()

    except ValueError:
        await DispatcherCashin.input_amount.set()
        await message.answer('Значение указанно не верно.\nЕсли вы хотите отменить операцию введите 0')


@dp.callback_query_handler(state=DispatcherCashin.choose_operator)
async def input_amount_courier_cashin(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'ikb_cancel':
        await ccansel(call, state)
        return None
    state_data = await state.get_data()
    req = requests.get(url=URL_DJANGO + f'user/{call.from_user.id}/')
    if req.status_code == 200:
        operator = requests.get(
            URL_DJANGO + f'operators/{call.data[4:]}/').json()
        
        await state.update_data(
                                amount=state_data['amount'],
                                operator=call.data[4:],
                                )
        try:
            cur_card =operator['active_card']
            msg = await bot.edit_message_text(
                message_id=state_data['msg'],
                chat_id=state_data['id'],
                text=f'Операция: кэшин \nОператор: {operator["user_name"]}\nСумма: {state_data["amount"]} \
                    \nКарта: ************{cur_card["card_number"][-4:]}',
                reply_markup=confirm_kb,
            )
            await state.update_data(
                operator=operator['tg_id'],
                operator_name=operator["user_name"],
                card_id=cur_card['id'],
                card_number=cur_card["card_number"]
            )
            await DispatcherCashin.confirm.set()
        except Exception as e:
            await call.message.answer(
                text='Ошибка на стороне сервера.\n Операция была отменена'
            )
            await state.finish()
    else:
        await call.message.answer(f'Ошибка при отправке запроса на сервер\nкод ошибки: {req.status_code}')
        await state.finish()
    # state_data = await state.get_data()
    # req = requests.get(url=URL_DJANGO + f'user/{call.from_user.id}/')
    # if req.status_code == 200:
    #     cards = requests.get(URL_DJANGO + f'operator/{call.data[4:]}/cards/').json()
    #     lables = [i['card_number'] for i in cards]
    #     callbacks = [i['id'] for i in cards]
    #     print(f'kartbl: {callbacks}')
    #     ikb = create_ikb(lables, callbacks)
    #     msg = await call.message.edit_text(text='Выберите карту оператора', reply_markup=ikb)
    #     await state.update_data(msg=msg.message_id,
    #                             id=msg.chat.id,
    #                             amount=state_data['amount'],
    #                             operator=call.data[4:],
    #                             )
        # print(call.data)
    #     await DispatcherCashin.confirm.set()
    # else:
    #     await call.message.answer(f'Ошибка при отправке запроса на сервер\nкод ошибки: {req.status_code}')
    #     await state.finish()


# @dp.callback_query_handler(lambda c: c.data.startswith('ikb_'), state=DispatcherCashin.choose_card)
# async def select_operator_cashin_dispatcher(callback_query: types.CallbackQuery, state: FSMContext):
#     state_data = await state.get_data()
#     if callback_query.data == 'ikb_cancel':
#         await bot.edit_message_text(
#             message_id=state_data['msg'],
#             chat_id=state_data['id'],
#             text='Операция отменена'
#         )
#         await state.finish()
#     else:
#         operator_req = requests.get(URL_DJANGO + f'operators/{state_data["operator"]}/')
#         cards_operators_req = requests.get(URL_DJANGO + f'operator/{state_data["operator"]}/cards/')
#         card_req = requests.get(URL_DJANGO + f'get/card/{callback_query.data[4:]}/')
#         if operator_req.status_code != 200:
#             raise Exception(
#                 f'req status code: {operator_req.status_code }')
#         operator = operator_req.json()
#         card_number = card_req.json()['card_number']

#         msg = await bot.edit_message_text(
#             message_id=state_data['msg'],
#             chat_id=state_data['id'],
#             text=f'Операция: кэшин \nОператор: {operator["user_name"]} \nКарта: {card_number} \nСумма: {state_data["amount"]}',
#             reply_markup=confirm_kb,
#         )
#         await state.update_data(
#             operator=operator['tg_id'],
#             operator_name=operator["user_name"],
#             card_number=card_number,
#             card_id=callback_query.data[4:],
#         )
#         await DispatcherCashin.confirm.set()
        # except Exception as e:
        #     await callback_query.message.answer(
        #         text='Ошибка на стороне сервера.\n Операция была отменена'
        #     )


@dp.callback_query_handler(text='confirm', state=DispatcherCashin.confirm)
async def confirm_cashout_dispatcher(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await notifiy_couriers(
        amount=data['amount'],
        operator_name=data['operator_name'],
        card_number=data['card_number'],
        text='Заявка\nОперация: кэшин',
        ikb=accept_ikb(f"cashin_{data['amount']}_{data['operator_name']}_{data['operator']}_{data['card_number']}_{data['card_id']}")
    )
    print(f"cashin_{data['amount']}_{data['operator_name']}_{data['operator']}_{data['card_number']}_{data['card_id']}")
    await bot.edit_message_text(
        chat_id=data['id'],
        message_id=data['msg'],
        text=f'Операция: кэшин\nСумма: {data["amount"]}\nОператор: {data["operator_name"]}\n_________________________\nЗаявка отправлена курьерам.',
    )
    await send_cashin_menu(callback_query.message, state)
    await state.finish()


@dp.callback_query_handler(text='dis_cashout', state=None)
async def use_cashout_button_dispatcher(callback_query: types.CallbackQuery, state: FSMContext):
    await DispatcherCashOut.input_amount.set()
    await callback_query.message.edit_text(text='Введите количество средств, которое будет указано в заявке', reply_markup=cancel_cb)
    await state.update_data({'msg':callback_query.message.message_id})
    

@dp.message_handler(state=DispatcherCashOut.input_amount)
async def input_amount_courier_cashout(message: types.Message, state: FSMContext):
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
            await send_cashin_menu(message, state)
        else:
            msg = await message.answer(
                text=f'Подтверждение операции:\n\nЗабор наличных стредств из Garantex\n{amount}',
                reply_markup=confirm_kb
            )
            await state.update_data(amount=amount, msg=msg.message_id, id=msg.chat.id)
            await DispatcherCashOut.confirm.set()

    except ValueError:
        await DispatcherCashOut.input_amount.set()
        await message.answer('Значение указанно не верно.\nЕсли вы хотите отменить операцию введите 0')
        


@dp.callback_query_handler(text='confirm', state=DispatcherCashOut.confirm)
async def confirm_cashout(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await notifiy_couriers(
        amount=data['amount'],
        text='Заявка\nОперация: забор наличных средств с Garantex',
        ikb=accept_ikb(f'cashout_{data["amount"]}'),
        )
    await bot.edit_message_text(
        chat_id=data['id'],
        message_id=data['msg'],
        text=f'Заявка о заборе наличных средств из Gatantex\n{data["amount"]}\n_________________________\nЗаявка отправлена курьерам.',
    )
    await send_cashin_menu(callback_query.message, state)
    await state.finish()