from aiogram.dispatcher.filters.state import StatesGroup, State


class Activity(StatesGroup):
    acceptOrder = State()
    acceptPayment = State()
    getPhoto = State()