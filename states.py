from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_phone = State()

class MenuStates(StatesGroup):
    main          = State()   # Asosiy menyu
    subject       = State()   # Fan tanlash (Ona tili / Adabiyot)

# ── Ona tili oqimi ──────────────────────────────────
class OnatiliStates(StatesGroup):
    category    = State()   # Mavzulashtirilgan / Aralash / Atestatsiya
    topic       = State()   # Mavzu tanlash (Fonetika, Leksika...)
    difficulty  = State()   # Qiyinlik tanlash

# ── Adabiyot oqimi ──────────────────────────────────
class AdabiyotStates(StatesGroup):
    category    = State()   # Sinflar / Aralash / G'azallar / Atestatsiya
    grade       = State()   # Sinf tanlash (5-11)
    difficulty  = State()   # Qiyinlik tanlash

# ── Atestatsiya ─────────────────────────────────────
class AttestationStates(StatesGroup):
    choose_format = State()   # miniapp yoki pdf

# ── To'lov ──────────────────────────────────────────
class PaymentStates(StatesGroup):
    waiting_for_check = State()
    # FSM data da saqlanadi:
    # product_type: 'retry' | 'attestation_onatili' | 'attestation_adabiyot'
    # retry_key:    access_key string
    # amount:       narx

# ── Admin ────────────────────────────────────────────
class AdminStates(StatesGroup):
    # Savol qo'shish
    add_subject       = State()
    add_category      = State()
    add_subcategory   = State()
    add_difficulty    = State()
    add_is_attest     = State()
    add_order_num     = State()
    add_image         = State()
    add_text          = State()
    add_a             = State()
    add_b             = State()
    add_c             = State()
    add_d             = State()
    add_correct       = State()
    # Broadcast
    broadcast_message = State()

class EditQuestionStates(StatesGroup):
    browsing      = State()
    searching     = State()
    viewing       = State()
    edit_field    = State()
    edit_value    = State()
    confirm_delete = State()