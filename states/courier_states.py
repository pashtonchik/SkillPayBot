from aiogram.dispatcher.filters.state import StatesGroup, State 


class CourierCashin(StatesGroup):
    input_amount = State()
    choose_operator = State()
    choose_card = State()
    confirm = State()
    confirm_task = State()
    edit_amount = State()


class CourierCashOut(StatesGroup):
    input_amount = State()
    confirm = State()
    confirm_task = State()
    edit_amount = State()


class Withdraw(StatesGroup):
    close_withdraw = State()

