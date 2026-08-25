from aiogram.fsm.state import State, StatesGroup

class ExchangeFSM(StatesGroup):
    choosing_crypto = State()
    choosing_bank = State()
    entering_amount = State()
    entering_requisites = State()
    confirming_order = State()
    waiting_for_receipt = State()