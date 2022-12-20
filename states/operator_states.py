from aiogram.dispatcher.filters.state import StatesGroup, State 

class OperatorCheckBalance(StatesGroup):
    input_balance = State()