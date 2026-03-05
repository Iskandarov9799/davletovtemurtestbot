# 📚 Ona tili va Adabiyot Test Boti

Aiogram 3 asosida yaratilgan Telegram test boti.

## 📁 Loyiha tuzilishi

```
telegram_test_bot/
├── bot.py                    # Asosiy fayl
├── config.py                 # Konfiguratsiya
├── states.py                 # FSM holatlari
├── requirements.txt          # Kutubxonalar
├── .env.example              # .env namunasi
├── handlers/
│   ├── registration.py       # Ro'yxatdan o'tish
│   ├── payment.py            # To'lov va admin tasdiqlash
│   ├── test_handler.py       # Test mantiqsi
│   └── admin.py              # Admin panel
├── keyboards/
│   └── keyboards.py          # Barcha klaviaturalar
├── database/
│   ├── db.py                 # SQLite funksiyalari
│   └── questions_data.py     # Savollar bazasi
└── tests/
```

## ⚙️ O'rnatish

### 1. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 2. Bot tokenini sozlash
`config.py` faylida `BOT_TOKEN` ni o'zgartiring:
```python
BOT_TOKEN: str = "YOUR_BOT_TOKEN_HERE"
```

Yoki `.env` fayl yarating:
```
BOT_TOKEN=your_token_here
```

### 3. Admin ID ni sozlash
`config.py` faylida admin Telegram ID sini kiriting:
```python
ADMIN_IDS: list = [123456789]  # Sizning Telegram ID ingiz
```

### 4. Karta ma'lumotlarini sozlash
```python
PAYMENT_AMOUNT: int = 15000         # To'lov summasi (so'm)
PAYMENT_CARD_NUMBER: str = "8600..."  # Karta raqami
PAYMENT_CARD_OWNER: str = "Ism Familiya"
```

### 5. Botni ishga tushirish
```bash
python bot.py
```

---

## 🔄 Jarayon ketma-ketligi

```
Foydalanuvchi /start bosadi
        ↓
Telefon raqami ulashadi (contact)
        ↓
Ro'yxatdan o'tdi ✅
        ↓
To'lov ma'lumotlarini ko'radi
        ↓
Karta orqali to'lov qiladi
        ↓
Chek rasmini yuboradi 📸
        ↓
Admin chekni ko'radi va tasdiqlaydi ✅
        ↓
Foydalanuvchiga xabar keladi 🔔
        ↓
30 ta random savol ishlaydi 📝
        ↓
Natijani ko'radi 📊
```

---

## 👤 Admin buyruqlari

| Tugma | Funksiya |
|-------|----------|
| `/admin` | Admin panelni ochish |
| `💰 Kutayotgan to'lovlar` | Tasdiqlanmagan to'lovlar |
| `👥 Barcha foydalanuvchilar` | Foydalanuvchilar ro'yxati |
| `📊 Statistika` | Bot statistikasi |

---

## 📋 Texnik ma'lumotlar

- **Framework:** Aiogram 3.x
- **Database:** SQLite3
- **FSM Storage:** MemoryStorage (ishlab chiqish uchun)
- **Savollar:** 50+ Ona tili va Adabiyot savollari
- **Test:** Har safar 30 ta **random** savol