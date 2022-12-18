from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def create_ikb(names, callbacks):
    if len(names) != len(callbacks):
        raise ValueError('names len != callbacks len')
    ikb = InlineKeyboardMarkup()
    for i in range(len(names)):
        ikb.add(
            InlineKeyboardButton(
                text=names[i],
                callback_data=f'ikb_{callbacks[i]}',
            )
        )
    ikb.add(
        InlineKeyboardButton(
            text='отмена',
            callback_data='ccancel'
        )
    )
    return ikb


courier_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton('кэшин', callback_data='cashin'),
    InlineKeyboardButton('забор средств с Garantex', callback_data='cashout'),
)

dispatcher_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton('заявка на кэшин',
                         callback_data='dis_cashin'),
        InlineKeyboardButton('заявка на забор средств', callback_data='dis_cashout'),
    ],
    [
        InlineKeyboardButton('список операторов', callback_data='dis_operators')
        ],
    ])

confirm_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton('подтвердить', callback_data='confirm'),
    InlineKeyboardButton('отмена', callback_data='ccancel'),
)

yes_no_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton('да', callback_data='yes'),
    InlineKeyboardButton('нет', callback_data='no'),
    InlineKeyboardButton('отмена', callback_data='cancel_'),
)

cancel_cb = InlineKeyboardMarkup().add(
    InlineKeyboardButton('отмена', callback_data='ccancel'),
)

def accept_ikb(data):
    return  InlineKeyboardMarkup().add(
        InlineKeyboardButton('принять', callback_data=f'accept_{data}')
    )

def parce_accept_ikb(data):
    return data[7:].split('_')[1:]