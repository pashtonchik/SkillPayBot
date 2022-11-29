from aiogram.dispatcher.filters.state import StatesGroup, State


class Activity(StatesGroup):
    acceptOrder = State()
    check_card = State()
    acceptPayment = State()
    getPhoto = State()
    add_reason_cancel = State()
