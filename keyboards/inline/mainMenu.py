from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

kb_menu_main = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardMarkup(text='Смена', callback_data='Смена')
        ]
    ],
    resize_keyboard=True
)

kb_menu_job = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardMarkup(text='Встать на смену', callback_data='Встать на смену')
        ],
        [
            InlineKeyboardMarkup(text='Уйти со смены', callback_data='Уйти со смены')
        ],
        [
            InlineKeyboardMarkup(text='Назад', callback_data='Назад')
        ]
    ],
    resize_keyboard=False
)

kb_accept_order = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text='Принять заявку', callback_data='Принять заявку')
        ]
    ]
)

kb_accept_payment = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text='Я оплатил', callback_data='Я оплатил')
        ]
    ]
)
