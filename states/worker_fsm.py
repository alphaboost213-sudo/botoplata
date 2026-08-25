from aiogram.fsm.state import StatesGroup, State

class WorkerFSM(StatesGroup):
    waiting_amount = State()
