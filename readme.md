# 📚 Ona tili va Adabiyot Test Boti

Telegram Mini App asosida ishlaydigan **Ona tili va Adabiyot** test boti. Foydalanuvchilar bot orqali savollarni ko'rib, Mini App ichida testni topshiradilar — natija avtomatik botga va guruhga yuboriladi.

---

## 🏗️ Arxitektura

```
Foydalanuvchi
    ↓
Telegram Bot (Aiogram 3)
    ↓
Mini App (GitHub Pages: index.html + main.js + style.css)
    ↓  tg.sendData()
Bot handler (web_app_data) → PostgreSQL DB
    ↓
Natija foydalanuvchiga + guruhga
```

**Mini App → Bot aloqasi:** `tg.sendData()` — Telegram o'z kanali orqali, HTTP/HTTPS shart emas. VPS da Nginx kerak emas.

---

## 📁 Loyiha tuzilishi

```
davletovtemurtestbot/
│
├── bot.py                      # Asosiy ishga tushirish fayli
├── config.py                   # Barcha sozlamalar (.env dan)
├── states.py                   # FSM holatlari
├── requirements.txt
│
├── handlers/
│   ├── registration.py         # /start, ro'yxatdan o'tish, menyu
│   ├── payment.py              # To'lov tizimi (once/daily/monthly)
│   ├── test_handler.py         # Test yuborish, Mini App URL yaratish
│   ├── miniapp_handler.py      # web_app_data qabul qilish → DB saqlash
│   ├── admin.py                # Admin panel, Excel import/eksport
│   └── question_editor.py      # Savol qo'shish/tahrirlash
│
├── keyboards/
│   └── keyboards.py            # Barcha klaviaturalar
│
├── database/
│   ├── connection.py           # SQLAlchemy engine, session
│   ├── models.py               # Jadval modellari
│   ├── db.py                   # Barcha async DB funksiyalari
│   └── questions_data.py       # Boshlang'ich savollar (agar kerak)
│
├── migrations/                 # Alembic migratsiyalari
│
├── index.html                  # Mini App UI (GitHub Pages)
├── main.js                     # Mini App logikasi
├── style.css                   # Mini App dizayni
│
└── tests/                      # Pytest testlar
```

---

## ⚙️ O'rnatish

### 1. Repozitoriyani clone qilish

```bash
git clone https://github.com/Iskandarov9799/davletovtemurtestbot.git
cd davletovtemurtestbot
```

### 2. Virtual muhit va kutubxonalar

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. `.env` fayl yaratish

```bash
cp .env.example .env
nano .env
```

`.env` tarkibi:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789, 987654321
PAYMENT_CARD=8600 0000 0000 0000
PAYMENT_OWNER=Ism Familiya
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
MINI_APP_URL=https://yourusername.github.io/your-repo/
SOLUTION_URL=https://t.me/your_channel
RESULT_GROUP_ID=-1001234567890
```

### 4. PostgreSQL ma'lumotlar bazasini yaratish

```bash
sudo -u postgres psql
CREATE USER botuser WITH PASSWORD 'yourpassword';
CREATE DATABASE onatili_bot OWNER botuser;
GRANT ALL PRIVILEGES ON DATABASE onatili_bot TO botuser;
\q
```

### 5. Migratsiyalarni ishlatish

```bash
alembic upgrade head
```

### 6. Botni ishga tushirish

```bash
python bot.py
```

---

## 🚀 VPS da deploy (systemd)

`/etc/systemd/system/bot.service` fayli:

```ini
[Unit]
Description=Ona tili Test Bot
After=network.target postgresql.service

[Service]
Type=simple
User=bot
WorkingDirectory=/home/bot
ExecStart=/home/bot/venv/bin/python bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable bot
systemctl start bot
systemctl status bot
```

Loglarni ko'rish:
```bash
journalctl -u bot -f
```

---

## 🌐 Mini App (GitHub Pages)

Mini App uchta fayldan iborat: `index.html`, `main.js`, `style.css`. Ular GitHub Pages orqali xizmat qiladi.

**GitHub Pages sozlash:**
1. Repository → Settings → Pages
2. Source: `Deploy from a branch` → `master` → `/ (root)`
3. URL: `https://yourusername.github.io/your-repo/`

Bu URL ni `.env` da `MINI_APP_URL` ga yozing.

**Yangilash:**
```bash
# Fayllarni o'zgartirgandan keyin
git add index.html main.js style.css
git commit -m "update miniapp"
git push
# VPS da bot qayta yuklanmaydi — GitHub Pages avtomatik yangilanadi
```

---

## 💳 To'lov tizimi

| Tarif | Narx | Davomiyligi |
|---|---|---|
| Bir martalik | 3,500 so'm | 1 ta test |
| Kunlik | 35,000 so'm | 24 soat |
| Oylik | 100,000 so'm | 30 kun |
| Attestatsiya | 10,000 so'm | Bir martalik |

**Jarayon:**
1. Foydalanuvchi karta raqamiga pul o'tkazadi
2. Chek rasmini botga yuboradi
3. Admin tasdiqlaydi → foydalanuvchiga test linki yuboriladi

---

## 🔄 Bot ishlash oqimi

```
/start
  ↓ Telefon raqam (contact)
  ↓ Ro'yxatdan o'tdi ✅
  ↓
Fan tanlash (Ona tili / Adabiyot / Attestatsiya / Milliy)
  ↓
Bo'lim / qiyinlik tanlash
  ↓ Bepul (birinchi marta) yoki to'lov
  ↓
Mini App URL → "Testni boshlash" tugmasi
  ↓
Mini App (GitHub Pages) ochiladi
  ↓ Savollar URL hash dan decode qilinadi (zlib + base64)
  ↓ Foydalanuvchi testni topshiradi
  ↓ tg.sendData(natija JSON)
  ↓
Bot web_app_data qabul qiladi
  ↓ DB ga saqlaydi (TestResult, UserWrongQuestion)
  ↓ Foydalanuvchiga natija xabari
  ↓ Guruhga natija yuboriladi
```

---

## 👤 Admin buyruqlari

| Buyruq / Tugma | Vazifasi |
|---|---|
| `/admin` | Admin panelni ochish |
| `💰 Kutayotgan to'lovlar` | Tasdiqlanmagan to'lovlar |
| `👥 Foydalanuvchilar` | Ro'yxat (20 ta) |
| `📊 Statistika` | To'liq statistika |
| `📥 Excel eksport` | Foydalanuvchilar + savollar Excel |
| `📤 Excel import` | Savollarni Excel dan yuklash |
| `➕ Savol qo'shish` | Yangi savol qo'shish (FSM) |
| `📋 Savollar` | Savollarni ko'rish / tahrirlash |
| `🗑 Savollarni o'chirish` | Bo'lim bo'yicha tozalash |
| `📢 Broadcast` | Barcha foydalanuvchilarga xabar |

---

## 🗃️ Ma'lumotlar bazasi

| Jadval | Vazifasi |
|---|---|
| `users` | Foydalanuvchilar (telegram_id, telefon, ism) |
| `purchases` | To'lovlar (pending/confirmed/rejected) |
| `subscriptions` | Kunlik/oylik obunalar |
| `user_access` | Bepul urinish holati |
| `attestation_access` | Attestatsiya ruxsati |
| `questions` | Savollar (choice + written) |
| `test_results` | Test natijalari |
| `user_wrong_questions` | Foydalanuvchi xato qilgan savollar |

---

## 🛠️ Texnik stack

| Komponent | Texnologiya |
|---|---|
| Bot framework | Aiogram 3.13 |
| Database | PostgreSQL + SQLAlchemy 2.0 (async) |
| Migratsiyalar | Alembic |
| Mini App | Vanilla JS + CSS (GitHub Pages) |
| Rasm saqlash | Telegram file_id / Cloudinary |
| Deploy | VPS + systemd |
| Testlar | Pytest + pytest-asyncio |

---

## 🔧 Muhim texnik jihatlar

**Savollarni Mini Appga yuborish:**
Savollar JSON → zlib compress → base64 → URL hash sifatida yuboriladi. Mini App JavaScript `DecompressionStream` yordamida ochadi.

**`tg.sendData()` vs `fetch()`:**
Mini App natijalarni `tg.sendData()` orqali yuboradi — bu Telegram'ning o'z kanali, HTTP/HTTPS yoki CORS kerak emas. VPS da Nginx o'rnatish shart emas.

**Duplicate handler muammosi:**
`F.web_app_data` handleri faqat `miniapp_handler.py` da bo'lishi kerak. `test_handler.py` da bu handler bo'lmasligi shart.

**`allowed_updates`:**
`bot.py` da `allowed_updates` ga `"web_app_data"` qo'shish shart — aks holda bot bu update turini qabul qilmaydi.

---

## 📝 Savollar formati (Excel import)

| Ustun | Ma'no |
|---|---|
| subject | `onatili` / `adabiyot` / `attestation` / `milliy` |
| category | `aralash` / `mavzu` / `sinf` va h.k. |
| subcategory | Bo'lim nomi (ixtiyoriy) |
| difficulty | `easy` / `medium` / `hard` |
| question_text | Savol matni |
| option_a/b/c/d | Javob variantlari |
| correct_answer | `A` / `B` / `C` / `D` |
| question_type | `choice` / `written` |
| keywords_1 | Yozma javob uchun kalit so'zlar |
| image_file_id | Telegram file_id (ixtiyoriy) |

---

## 🐛 Tez-tez uchraydigan muammolar

**Bot `web_app_data` ni qabul qilmayapti:**
```python
# bot.py da allowed_updates tekshiring:
allowed_updates=["message", "callback_query", "web_app_data", ...]
```

**Mini App ochilmayapti:**
- `MINI_APP_URL` `.env` da to'g'ri yozilganligini tekshiring
- GitHub Pages faol ekanligini tekshiring (repo Settings → Pages)

**DB ga saqlanmayapti:**
- `journalctl -u bot -f` — logda `web_app_data keldi` va `DB ga saqlandi` ko'rinishi kerak
- `test_handler.py` da duplicate `F.web_app_data` handler yo'qligini tekshiring

**Guruhga yuborilmayapti:**
- `RESULT_GROUP_ID` minus bilan: `-1001234567890`
- Bot guruhga qo'shilgan va admin ekanligini tekshiring

---

## 📄 Litsenziya

MIT License — erkin foydalanish mumkin.