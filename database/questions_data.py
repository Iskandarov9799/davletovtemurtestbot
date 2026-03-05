from database.db import get_connection

ONA_TILI_QUESTIONS = [
    # === ONA TILI ===
    {
        "subject": "ona_tili",
        "question": "Qaysi so'z olmosh turkumiga kiradi?",
        "a": "kitob", "b": "men", "c": "yaxshi", "d": "yugurmoq",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Fe'lning necha zamonlari bor?",
        "a": "2 ta", "b": "3 ta", "c": "4 ta", "d": "5 ta",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "'Bog'lovchi' qaysi so'z turkumiga kiradi?",
        "a": "Ravish", "b": "Undov", "c": "Bog'lovchi", "d": "Ko'makchi",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Qaysi gapda ega bor?",
        "a": "Kecha yomg'ir yog'di.", "b": "Bor!", "c": "Chiqing!", "d": "Kel!",
        "correct": "A"
    },
    {
        "subject": "ona_tili",
        "question": "So'z qaysi bo'laklardan tashkil topadi?",
        "a": "Gap va jumladan", "b": "Morfema va fonemadan", "c": "Harf va raqamdan", "d": "Leksema va sintaksemadan",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Qaysi so'z sifat turkumiga kiradi?",
        "a": "tez", "b": "tezlik", "c": "tezlashmoq", "d": "tezda",
        "correct": "A"
    },
    {
        "subject": "ona_tili",
        "question": "O'zbek tilida unli tovushlar soni nechta?",
        "a": "5", "b": "6", "c": "7", "d": "8",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Qaysi so'zda imlo xatosi bor?",
        "a": "ko'cha", "b": "maktab", "c": "kitob", "d": "o'quvchi",
        "correct": "A"
    },
    {
        "subject": "ona_tili",
        "question": "'Bola o'qidi' gapida 'o'qidi' so'zi qanday bo'lak?",
        "a": "Ega", "b": "Kesim", "c": "To'ldiruvchi", "d": "Aniqlovchi",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Antonim nima?",
        "a": "Ma'nodosh so'zlar", "b": "Qarama-qarshi ma'noli so'zlar", "c": "Shakldosh so'zlar", "d": "Ko'p ma'noli so'zlar",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Quyidagilardan qaysi biri ot so'z turkumiga kiradi?",
        "a": "baland", "b": "tez", "c": "daftar", "d": "yugurmoq",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Sinonimlarga misol keltiring:",
        "a": "katta – kichik", "b": "yaxshi – yomon", "c": "baland – past", "d": "go'zal – chiroyli",
        "correct": "D"
    },
    {
        "subject": "ona_tili",
        "question": "Ko'plik qo'shimchasi qaysi?",
        "a": "-ning", "b": "-lar", "c": "-ga", "d": "-dan",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Qaysi gapda murojaat bor?",
        "a": "Men uyga bordim.", "b": "Akam keldi.", "c": "Bola, uyga bor!", "d": "Kitob stoldа.",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Frazeologizm nima?",
        "a": "Bir so'zdan iborat ibora", "b": "Ko'chma ma'nodagi barqaror so'z birikmasi", "c": "Matematika atamasi", "d": "Xorijiy so'z",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "'Qo'l bermoq' frazeologizmining ma'nosi:",
        "a": "Qo'l uzatmoq", "b": "Yordam bermoq", "c": "Salom bermoq", "d": "Qo'lni ko'tarmoq",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Ega qanday so'roqqa javob beradi?",
        "a": "Nima? Qaysi?", "b": "Kim? Nima?", "c": "Qachon? Qayerda?", "d": "Qanday? Qancha?",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "To'ldiruvchi qanday so'roqlarga javob beradi?",
        "a": "Kim? Nima?", "b": "Kimni? Nimani? Kimga? Nimaga?", "c": "Qanday? Qanaqa?", "d": "Qachon? Qayerda?",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Quyidagi gapda nechta so'z bor: 'Kecha men kitob o'qidim.'",
        "a": "3", "b": "4", "c": "5", "d": "6",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Leksikologiya neni o'rganadi?",
        "a": "Tovushlarni", "b": "So'z tarkibini", "c": "So'zlarning ma'nosini", "d": "Gapni",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Paronim nima?",
        "a": "Qarama-qarshi ma'noli so'zlar", "b": "Talaffuzi o'xshash, ma'nosi boshqa so'zlar", "c": "Ma'nodosh so'zlar", "d": "Ko'p ma'noli so'zlar",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Qaysi so'z fe'l turkumiga kiradi?",
        "a": "ish", "b": "ishchi", "c": "ishlash", "d": "ishlamoq",
        "correct": "D"
    },
    {
        "subject": "ona_tili",
        "question": "Hozirgi zamon fe'li qaysi?",
        "a": "yozdi", "b": "yozmoqchi", "c": "yozayapti", "d": "yozgan",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "O'tgan zamon fe'li qaysi?",
        "a": "boraman", "b": "boradi", "c": "bordi", "d": "bormoqchi",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Ravish qanday so'roqqa javob beradi?",
        "a": "Kim? Nima?", "b": "Qanday? Qancha? Qachon? Qayerda?", "c": "Kimning? Nimaning?", "d": "Qaysi? Qanday?",
        "correct": "B"
    },

    # === ADABIYOT ===
    {
        "subject": "ona_tili",
        "question": "Alisher Navoiy qaysi asarni yozgan?",
        "a": "Ona yurt", "b": "Xamsa", "c": "O'tkan kunlar", "d": "Kecha va kunduz",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "'O'tkan kunlar' romanini kim yozgan?",
        "a": "Hamza", "b": "Cho'lpon", "c": "Abdulla Qodiriy", "d": "G'afur G'ulom",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Lirik tur qaysi janrni o'z ichiga oladi?",
        "a": "Roman", "b": "Doston", "c": "She'r", "d": "Hikoya",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Epik tur qaysi janrni o'z ichiga oladi?",
        "a": "She'r", "b": "Lirik she'r", "c": "Roman, hikoya, doston", "d": "Qo'shiq",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "G'azalning o'ziga xos xususiyati nima?",
        "a": "Qofiyalanmaydi", "b": "Matla va maqta bo'ladi", "c": "Nasrda yoziladi", "d": "Sakkiz misradan iborat",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "'Kecha va kunduz' romanini kim yozgan?",
        "a": "Abdulla Qodiriy", "b": "Cho'lpon", "c": "Hamza", "d": "Oybek",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Navoiyning tug'ilgan yili:",
        "a": "1441", "b": "1444", "c": "1455", "d": "1460",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Ruboiy necha misradan iborat?",
        "a": "2", "b": "4", "c": "6", "d": "8",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Abdulla Oribek asari:",
        "a": "Semurg'", "b": "Xamsa", "c": "Navoiy", "d": "Qutlug' qon",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Tasviriy vosita – istiora nima?",
        "a": "O'xshatish", "b": "Ko'chim (metafora)", "c": "Mubolag'a", "d": "Takrorlash",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Qofiya nima?",
        "a": "She'r satrlari oxirida keluvchi ohangdosh so'zlar", "b": "She'r boshi", "c": "Misra o'rtasidagi pauza", "d": "She'r mavzusi",
        "correct": "A"
    },
    {
        "subject": "ona_tili",
        "question": "Hamza Hakimzodaning to'liq ismi:",
        "a": "Hamza Hakimzoda Niyoziy", "b": "Hamza Abdullayev", "c": "Hamza G'ulomov", "d": "Hamza Karimov",
        "correct": "A"
    },
    {
        "subject": "ona_tili",
        "question": "'Mehrobdan chayon' asarini kim yozgan?",
        "a": "Oybek", "b": "Cho'lpon", "c": "Abdulla Qodiriy", "d": "Hamid Olimjon",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Badiiy adabiyotning asosiy vazifasi nima?",
        "a": "Ma'lumot berish", "b": "Insonni tarbiyalash va estetik zavq berish", "c": "Faqat o'rgatish", "d": "Tariхni yozish",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Ertak qaysi turga kiradi?",
        "a": "Lirik", "b": "Dramatik", "c": "Epik", "d": "Lirik-epik",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Drama asarlarining asosiy elementi nima?",
        "a": "Tasvir", "b": "Dialog va monolog", "c": "Tasviriy vositalar", "d": "Qofiya",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "'Alpomish' dostoni qaysi xalq og'zaki ijodiga kiradi?",
        "a": "Qozoq", "b": "Tojik", "c": "O'zbek", "d": "Qirg'iz",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Mumtoz adabiyot deganda nima tushuniladi?",
        "a": "Zamonaviy adabiyot", "b": "Qadimgi va o'rta asrlar klassik adabiyoti", "c": "Bolalar adabiyoti", "d": "Tarjima adabiyot",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Navoiyning 'Xamsa'si nechta dostondan iborat?",
        "a": "3", "b": "4", "c": "5", "d": "6",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "Badiiy vosita – mubolag'a nima?",
        "a": "Narsani kichraytirish", "b": "Narsani haddan tashqari oshirib ko'rsatish", "c": "Narsani solishtirish", "d": "Narsani yashirish",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "O'xshatish qaysi so'z bilan bog'lanadi?",
        "a": "lekin", "b": "chunki", "c": "go'yo, kabi, singari", "d": "balki",
        "correct": "C"
    },
    {
        "subject": "ona_tili",
        "question": "G'afur G'ulomning mashhur asari:",
        "a": "Shum bola", "b": "O'tkan kunlar", "c": "Xamsa", "d": "Alpomish",
        "correct": "A"
    },
    {
        "subject": "ona_tili",
        "question": "She'riyatda misra nima?",
        "a": "She'rning bir bandi", "b": "She'rning bir satri", "c": "She'rning boshi", "d": "She'rning qofiyasi",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Adabiy til va sheva o'rtasidagi farq nima?",
        "a": "Adabiy til yozma, sheva og'zaki", "b": "Adabiy til umumxalq uchun, sheva ma'lum hudud uchun", "c": "Ular bir xil", "d": "Sheva adabiy tildan to'g'ri",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Asarda bosh qahramon kim bo'lsa, u kim deyiladi?",
        "a": "Yordamchi qahramon", "b": "Bosh qahramon yoki protagonist", "c": "Antagonist", "d": "Epizodik qahramon",
        "correct": "B"
    },
    {
        "subject": "ona_tili",
        "question": "Qaysi asar Abdulla Qodiriy qalamiga mansub emas?",
        "a": "O'tkan kunlar", "b": "Mehrobdan chayon", "c": "Obid ketmon", "d": "Shum bola",
        "correct": "D"
    },
]

def seed_questions():
    conn = get_connection()
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) as cnt FROM questions")
    count = cursor.fetchone()['cnt']

    if count > 0:
        print(f"ℹ️  {count} ta savol allaqachon mavjud.")
        conn.close()
        return

    for q in ONA_TILI_QUESTIONS:
        cursor.execute("""
            INSERT INTO questions (subject, question_text, option_a, option_b, option_c, option_d, correct_answer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            q['subject'],
            q['question'],
            q['a'], q['b'], q['c'], q['d'],
            q['correct']
        ))

    conn.commit()
    conn.close()
    print(f"✅ {len(ONA_TILI_QUESTIONS)} ta savol muvaffaqiyatli qo'shildi!")