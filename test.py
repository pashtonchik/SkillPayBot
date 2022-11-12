@dp.callback_query_handler(trade_cb.filter(action=['accept_trade']))
async def accept_order(call: types.CallbackQuery, callback_data: dict, state=FSMContext):

    trade_id = callback_data['id']
    data = {
        'id': str(trade_id),
        'agent': str(call.from_user.id)
    }
    kb_accept_cancel_payment = create_accept_cancel_kb(trade_id, callback_data['type'])
    
    if callback_data['type'] == 'BZ':
        get_trade_info = requests.get(URL_DJANGO + f'trade/detail/{trade_id}/')
        if not get_trade_info.json()['trade']['agent'] or str(get_trade_info.json()['trade']['agent']) == str(
                call.from_user.id):

            set_agent_trade = requests.post(URL_DJANGO + f'update/trade/', json=data)

            get_current_info = requests.get(URL_DJANGO + f'trade/detail/{trade_id}/')
            if get_current_info.json()['trade']['agent'] == str(call.from_user.id):
                headers = authorization(
                    get_current_info.json()['user']['key'],
                    get_current_info.json()['user']['email']
                )

                proxy = get_current_info.json()['user']['proxy']

                data = {
                    'type': 'confirm-trade'
                }

                url = f'https://bitzlato.com/api/p2p/trade/{trade_id}/'
                try:
                    req_change_type = requests.post(url, headers=headers, proxies=proxy, json=data)

                    if req_change_type.status_code == 200:
                        await call.answer('Вы успешно взяли заявку в работу!', show_alert=True)
                        await call.message.edit_text(f'''
Переведите {get_current_info.json()['trade']['currency_amount']} {get_current_info.json()['trade']['currency']}
Комментарий: {get_current_info.json()['trade']['details']}
Реквизиты: {get_current_info.json()['trade']['counterDetails']} {get_current_info.json()['paymethod_description']}
                                                        ''', reply_markup=kb_accept_cancel_payment)
                        await Activity.acceptOrder.set()
                    else:
                        await call.answer('Произошла ошибка, нажмите кнопку заново.')
                except Exception as e:
                    await call.answer('Произошла ошибка, нажмите кнопку заново.')

            else:
                await call.answer("Заявка уже в работе", show_alert=True)
                await call.message.delete()
        else:
            await call.answer("Заявка уже в работе", show_alert=True)
            await call.message.delete()
    
    elif callback_data['type'] == 'googleSheets':
        url_type = 'pay'
        trade_type = 'pay'

    elif callback_data['type'] == 'kf':
        url_type = 'kf'
        trade_type = 'kftrade'
        
    # _______________GAANTEX__________________________GATANTEX________________________GATANTEX________________________
    elif callback_data['type'] == 'garantex':
        url_type = 'gar'
        trade_type = 'gar_trade'



    get_pay_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')

    if (not get_pay_info.json()[trade_type]['agent'] or str(get_pay_info.json()[trade_type]['agent']) == str(
            call.from_user.id)) and \
            get_pay_info.json()[trade_type]['status'] != 'closed':

        set_agent_trade = requests.post(URL_DJANGO + f'update/{url_type}/trade/', json=data)

        get_current_info = requests.get(URL_DJANGO + f'{url_type}/trade/detail/{trade_id}/')

        if str(get_current_info.json()[trade_type]['agent']) == str(call.from_user.id):
            try:
                messages = select_message_from_database(call.from_user.id)
                trade_mas = []
                for msg, trade_id_db,   in messages:
                    if (msg != call.message.message_id):
                        trade_mas.append(trade_id_db)
                        try:
                            await bot.delete_message(call.from_user.id, msg)
                        except Exception as e:
                            print(e)
                        delete_from_database(call.from_user.id, msg, trade_id_db, url_type)
                res_delete = {
                            'id' : trade_mas,
                            'tg_id' : call.from_user.id
                        }
                try:
                    req = requests.post(URL_DJANGO + f'delete/{url_type}/recipient/', json=res_delete)
                except Exception as e:
                    print(e)
                await call.answer('Вы успешно взяли заявку в работу!', show_alert=True)
                await call.message.edit_text(f'''
    Заявка: {url_type.upper()} — {trade_id}
    Инструмент: {get_current_info.json()[trade_type]['paymethod_description']}
    Сумма: `{get_current_info.json()[trade_type]['amount']}` 
    Адресат: `{get_current_info.json()[trade_type]['card_number']}`

    Статус: *Ожидаем оплату и предоставление чека.*

        ''', reply_markup=kb_accept_cancel_payment, parse_mode='Markdown')
                await Activity.acceptPayment.set()
            except Exception as e:
                await call.answer('Произошла ошибка, нажмите кнопку заново.')

        else:
            await call.answer("Заявка уже в работе", show_alert=True)
            await call.message.delete()
    else:
        await call.answer('Заявка уже в работе.', show_alert=True)
        await call.message.delete()