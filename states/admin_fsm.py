from aiogram.fsm.state import State, StatesGroup

class AdminFSM(StatesGroup):
    waiting_for_broadcast_msg = State()
    waiting_for_search_id = State()
    waiting_for_balance_val = State()
    
    # Редактирование направления
    editing_rate = State()
    editing_min = State()
    editing_max = State()
    editing_reqs = State()
    editing_margin = State()
    
    # Создание нового направления
    adding_dir_operation = State()
    adding_dir_crypto = State()
    adding_dir_bank = State()
    adding_dir_rate = State()
    adding_dir_min = State()
    adding_dir_max = State()
    adding_dir_reqs = State()