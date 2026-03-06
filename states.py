from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_phone = State()

class PaymentStates(StatesGroup):
    waiting_for_check = State()

class TestStates(StatesGroup):
    choosing_difficulty = State()
    answering = State()

class AdminStates(StatesGroup):
    # Savol qo'shish
    add_q_difficulty = State()
    add_q_subject = State()
    add_q_image = State()
    add_q_text = State()
    add_q_a = State()
    add_q_b = State()
    add_q_c = State()
    add_q_d = State()
    add_q_correct = State()
    # Broadcast
    broadcast_text = State()

class EditQuestionStates(StatesGroup):
    browsing = State()        # Savollar ro'yxatini ko'rish
    searching = State()       # Qidirish
    viewing = State()         # Savol tafsilotlari
    edit_choose_field = State() # Qaysi maydonni tahrirlash
    edit_value = State()      # Yangi qiymat kiritish
    confirm_delete = State()  # O'chirishni tasdiqlash