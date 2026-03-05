from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_phone = State()

class PaymentStates(StatesGroup):
    waiting_for_check = State()

class TestStates(StatesGroup):
    answering = State()

class AdminStates(StatesGroup):
    waiting_action = State()