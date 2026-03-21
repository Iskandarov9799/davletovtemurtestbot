"""
Barcha database operatsiyalari — async SQLAlchemy orqali.
"""
from datetime import datetime
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from database.models import (
    User, Purchase, UserAccess, AttestationAccess,
    Question, TestResult, UserWrongQuestion
)
import database.connection as _conn

# ──────────────────────────────────────────────
# USERS
# ──────────────────────────────────────────────

async def get_user(telegram_id: int):
    async with _conn.AsyncSessionLocal() as s:
        r = await s.execute(select(User).where(User.telegram_id == telegram_id))
        return r.scalar_one_or_none()

async def create_user(telegram_id: int, full_name: str, username: str = None):
    async with _conn.AsyncSessionLocal() as s:
        existing = await s.execute(select(User).where(User.telegram_id == telegram_id))
        if existing.scalar_one_or_none():
            return
        s.add(User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            registered_at=datetime.utcnow()
        ))
        await s.commit()

async def update_user_phone(telegram_id: int, phone: str):
    async with _conn.AsyncSessionLocal() as s:
        await s.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(phone_number=phone, is_registered=True)
        )
        await s.commit()

async def is_registered(telegram_id: int) -> bool:
    user = await get_user(telegram_id)
    return bool(user and user.is_registered)

async def get_all_users():
    async with _conn.AsyncSessionLocal() as s:
        r = await s.execute(select(User).order_by(User.registered_at.desc()))
        return r.scalars().all()

async def get_user_tariff(telegram_id: int) -> dict:
    """Foydalanuvchi tarifini qaytaradi."""
    from database.models import Subscription
    now = datetime.utcnow()
    async with _conn.AsyncSessionLocal() as s:
        # Faol obuna
        sub = await s.execute(
            select(Subscription).where(
                Subscription.telegram_id == telegram_id,
                Subscription.expires_at > now
            ).join(Purchase, Subscription.purchase_id == Purchase.id)
             .where(Purchase.status == 'confirmed')
             .order_by(Subscription.expires_at.desc())
        )
        sub = sub.scalars().first()
        if sub:
            LABELS = {'daily': 'Kunlik', 'monthly': 'Oylik', 'yearly': 'Yillik'}
            return {
                'type': sub.sub_type,
                'label': LABELS.get(sub.sub_type, sub.sub_type),
                'expires': str(sub.expires_at)[:16]
            }
        # Attestatsiya
        att = await s.execute(
            select(AttestationAccess).where(
                AttestationAccess.telegram_id == telegram_id
            )
        )
        if att.scalars().first():
            return {'type': 'attestation', 'label': 'Attestatsiya', 'expires': None}
        return {'type': 'free', 'label': 'Bepul', 'expires': None}

async def admin_grant_subscription(telegram_id: int, sub_type: str) -> bool:
    """Admin tomonidan obuna berish (to'lovsiz)."""
    from datetime import timedelta
    from database.models import Subscription
    now = datetime.utcnow()
    if sub_type == 'daily':
        expires = now + timedelta(days=1)
    elif sub_type == 'monthly':
        expires = now + timedelta(days=30)
    elif sub_type == 'yearly':
        expires = now + timedelta(days=365)
    else:
        return False
    async with _conn.AsyncSessionLocal() as s:
        # Fake purchase yaratish
        p = Purchase(
            telegram_id=telegram_id,
            product_type=sub_type,
            amount=0,
            check_photo='admin_grant',
            status='confirmed',
            submitted_at=now,
            confirmed_at=now,
        )
        s.add(p)
        await s.flush()
        s.add(Subscription(
            telegram_id=telegram_id,
            sub_type=sub_type,
            started_at=now,
            expires_at=expires,
            purchase_id=p.id
        ))
        await s.commit()
    return True

async def admin_revoke_subscription(telegram_id: int) -> bool:
    """Admin tomonidan obunani bekor qilish."""
    from database.models import Subscription
    now = datetime.utcnow()
    async with _conn.AsyncSessionLocal() as s:
        await s.execute(
            update(Subscription)
            .where(
                Subscription.telegram_id == telegram_id,
                Subscription.expires_at > now
            )
            .values(expires_at=now)
        )
        await s.commit()
    return True

# ──────────────────────────────────────────────
# ACCESS — bepul / pullik
# ──────────────────────────────────────────────

async def get_access_status(telegram_id: int, access_key: str) -> str:
    """
    'free'  — birinchi marta, bepul
    'paid'  — to'lov tasdiqlangan (once/daily/monthly)
    'buy'   — to'lov kerak
    """
    async with _conn.AsyncSessionLocal() as s:
        # 1. Bepul urinish ishlatilganmi?
        ua = await s.execute(
            select(UserAccess).where(
                UserAccess.telegram_id == telegram_id,
                UserAccess.access_key == access_key
            )
        )
        ua = ua.scalar_one_or_none()
        if ua is None or not ua.free_used:
            return 'free'

        # 2. Faol obuna bormi? (daily / monthly)
        from database.models import Subscription
        now = datetime.utcnow()
        sub = await s.execute(
            select(Subscription).where(
                Subscription.telegram_id == telegram_id,
                Subscription.expires_at > now
            ).join(Purchase, Subscription.purchase_id == Purchase.id)
             .where(Purchase.status == 'confirmed')
        )
        if sub.scalars().first():
            return 'paid'

        # 3. Bir martalik to'lov (once) — ishlatilmagan bo'lishi kerak
        once = await s.execute(
            select(Purchase).where(
                Purchase.telegram_id == telegram_id,
                Purchase.product_type.in_(['once', 'retry']),
                Purchase.retry_key == access_key,
                Purchase.status == 'confirmed',
                Purchase.is_used == False
            )
        )
        if once.scalars().first():
            return 'paid'

        return 'buy'

async def mark_once_used(telegram_id: int, access_key: str):
    """Once to'lovni ishlatilgan deb belgilash"""
    async with _conn.AsyncSessionLocal() as s:
        await s.execute(
            update(Purchase)
            .where(
                Purchase.telegram_id == telegram_id,
                Purchase.product_type.in_(['once', 'retry']),
                Purchase.retry_key == access_key,
                Purchase.status == 'confirmed',
                Purchase.is_used == False
            )
            .values(is_used=True)
        )
        await s.commit()

async def mark_free_used(telegram_id: int, access_key: str):
    async with _conn.AsyncSessionLocal() as s:
        ua = await s.execute(
            select(UserAccess).where(
                UserAccess.telegram_id == telegram_id,
                UserAccess.access_key == access_key
            )
        )
        ua = ua.scalar_one_or_none()
        if ua:
            ua.free_used = True
        else:
            s.add(UserAccess(
                telegram_id=telegram_id,
                access_key=access_key,
                free_used=True
            ))
        await s.commit()

# ──────────────────────────────────────────────
# ATTESTATION
# ──────────────────────────────────────────────

async def has_attestation(telegram_id: int, subject: str) -> bool:
    async with _conn.AsyncSessionLocal() as s:
        r = await s.execute(
            select(AttestationAccess).where(
                AttestationAccess.telegram_id == telegram_id,
                AttestationAccess.subject == subject
            )
        )
        return r.scalar_one_or_none() is not None

async def get_attestation_format(telegram_id: int, subject: str):
    async with _conn.AsyncSessionLocal() as s:
        r = await s.execute(
            select(AttestationAccess).where(
                AttestationAccess.telegram_id == telegram_id,
                AttestationAccess.subject == subject
            )
        )
        row = r.scalar_one_or_none()
        return row.format if row else None

async def grant_attestation(telegram_id: int, subject: str, fmt: str):
    async with _conn.AsyncSessionLocal() as s:
        exists = await s.execute(
            select(AttestationAccess).where(
                AttestationAccess.telegram_id == telegram_id,
                AttestationAccess.subject == subject
            )
        )
        if not exists.scalar_one_or_none():
            s.add(AttestationAccess(
                telegram_id=telegram_id,
                subject=subject,
                format=fmt,
                purchased_at=datetime.utcnow()
            ))
            await s.commit()

# ──────────────────────────────────────────────
# PURCHASES
# ──────────────────────────────────────────────
# ── SUBSCRIPTION ──────────────────────────────────────

async def grant_subscription(telegram_id: int, sub_type: str, purchase_id: int):
    """Kunlik yoki oylik obuna berish"""
    from datetime import timedelta
    from database.models import Subscription
    now = datetime.utcnow()
    if sub_type == 'daily':
        expires = now + timedelta(days=1)
    elif sub_type == 'monthly':
        expires = now + timedelta(days=30)
    else:
        return
    async with _conn.AsyncSessionLocal() as s:
        s.add(Subscription(
            telegram_id=telegram_id,
            sub_type=sub_type,
            started_at=now,
            expires_at=expires,
            purchase_id=purchase_id
        ))
        await s.commit()


async def get_active_subscription(telegram_id: int):
    """Faol obunani qaytarish yoki None"""
    from database.models import Subscription
    now = datetime.utcnow()
    async with _conn.AsyncSessionLocal() as s:
        sub = await s.execute(
            select(Subscription).where(
                Subscription.telegram_id == telegram_id,
                Subscription.expires_at > now
            ).join(Purchase, Subscription.purchase_id == Purchase.id)
             .where(Purchase.status == 'confirmed')
             .order_by(Subscription.expires_at.desc())
        )
        return sub.scalars().first()



async def create_purchase(telegram_id: int, product_type: str, amount: int,
                           check_photo: str, retry_key: str = None) -> int:
    """
    product_type: 'retry' | 'attestation_onatili' | 'attestation_adabiyot'
    retry_key:    access_key (faqat retry uchun)
    """
    async with _conn.AsyncSessionLocal() as s:
        p = Purchase(
            telegram_id=telegram_id,
            product_type=product_type,  # ← har doim 'retry' yoki 'attestation_X'
            retry_key=retry_key,
            amount=amount,
            check_photo=check_photo,
            submitted_at=datetime.utcnow()
        )
        s.add(p)
        await s.commit()
        await s.refresh(p)
        return p.id

async def confirm_purchase(purchase_id: int, admin_id: int):
    async with _conn.AsyncSessionLocal() as s:
        await s.execute(
            update(Purchase)
            .where(Purchase.id == purchase_id)
            .values(status='confirmed',
                    confirmed_at=datetime.utcnow(),
                    confirmed_by=admin_id)
        )
        await s.commit()

async def reject_purchase(purchase_id: int, admin_id: int):
    async with _conn.AsyncSessionLocal() as s:
        await s.execute(
            update(Purchase)
            .where(Purchase.id == purchase_id)
            .values(status='rejected',
                    confirmed_at=datetime.utcnow(),
                    confirmed_by=admin_id)
        )
        await s.commit()

async def get_pending_purchases():
    async with _conn.AsyncSessionLocal() as s:
        r = await s.execute(
            select(Purchase, User)
            .join(User, Purchase.telegram_id == User.telegram_id)
            .where(Purchase.status == 'pending')
            .order_by(Purchase.submitted_at.asc())
        )
        return r.all()

async def get_purchase_by_id(purchase_id: int):
    async with _conn.AsyncSessionLocal() as s:
        r = await s.execute(select(Purchase).where(Purchase.id == purchase_id))
        return r.scalar_one_or_none()

# ──────────────────────────────────────────────
# QUESTIONS
# ──────────────────────────────────────────────

async def get_questions(subject: str, category: str,
                         subcategory: str = None, difficulty: str = None,
                         count: int = 35, is_attestation: bool = False,
                         telegram_id: int = None) -> list:
    """
    Savollarni qaytaradi:
    - Attestation: tartib bo'yicha (order_num)
    - Oddiy: avval foydalanuvchi xato qilgan savollar, keyin random yangilar
    """
    async with _conn.AsyncSessionLocal() as s:
        if is_attestation:
            q = select(Question).where(
                Question.subject == subject,
                Question.is_attestation == True
            ).order_by(Question.order_num)
            r = await s.execute(q)
            return r.scalars().all()

        filters = [
            Question.subject == subject,
            Question.category == category,
            Question.is_attestation == False,
        ]
        if subcategory:
            filters.append(Question.subcategory == subcategory)
        if difficulty:
            filters.append(Question.difficulty == difficulty)

        if not telegram_id:
            # Foydalanuvchi aniqlanmagan — oddiy random
            q = select(Question).where(*filters).order_by(func.random()).limit(count)
            r = await s.execute(q)
            return r.scalars().all()

        # 1. Xato qilingan savollar (wrong_count bo'yicha kamayish tartibida)
        wrong_q = (
            select(Question)
            .join(UserWrongQuestion, UserWrongQuestion.question_id == Question.id)
            .where(
                *filters,
                UserWrongQuestion.telegram_id == telegram_id
            )
            .order_by(UserWrongQuestion.wrong_count.desc())
            .limit(count)
        )
        wrong_r = await s.execute(wrong_q)
        wrong_questions = list(wrong_r.scalars().all())
        wrong_ids = [q.id for q in wrong_questions]

        remaining = count - len(wrong_questions)

        if remaining <= 0:
            return wrong_questions[:count]

        # 2. Yangi savollar (xato qilinmaganlar)
        new_filters = filters + [Question.id.notin_(wrong_ids)] if wrong_ids else filters
        new_q = select(Question).where(*new_filters).order_by(func.random()).limit(remaining)
        new_r = await s.execute(new_q)
        new_questions = list(new_r.scalars().all())

        # Xato savollar oldin, keyin yangilar
        import random
        random.shuffle(new_questions)
        return wrong_questions + new_questions

async def count_questions(subject: str = None, category: str = None,
                           subcategory: str = None, difficulty: str = None,
                           is_attestation: bool = False,
                           subcategory_prefix: str = None) -> int:
    """subcategory_prefix — LIKE filter, masalan '10_' barcha 10-sinf boblarini topadi."""
    async with _conn.AsyncSessionLocal() as s:
        filters = []
        if subject:        filters.append(Question.subject == subject)
        if is_attestation: filters.append(Question.is_attestation == True)
        else:
            if category:           filters.append(Question.category == category)
            if subcategory:        filters.append(Question.subcategory == subcategory)
            if subcategory_prefix: filters.append(Question.subcategory.like(f"{subcategory_prefix}%"))
            if difficulty:         filters.append(Question.difficulty == difficulty)

        q = select(func.count()).select_from(Question)
        if filters:
            q = q.where(*filters)
        r = await s.execute(q)
        return r.scalar() or 0

async def add_question(subject, category, question_text,
                        option_a, option_b, option_c, option_d,
                        correct_answer, subcategory=None,
                        difficulty=None, is_attestation=False,
                        order_num=None, image_file_id=None,
                        question_type='choice', written_parts=1,
                        keywords_1=None, keywords_2=None):
    async with _conn.AsyncSessionLocal() as s:
        s.add(Question(
            subject=subject, category=category, subcategory=subcategory,
            difficulty=difficulty, is_attestation=is_attestation,
            order_num=order_num, question_text=question_text,
            option_a=option_a, option_b=option_b,
            option_c=option_c, option_d=option_d,
            correct_answer=correct_answer, image_file_id=image_file_id,
            question_type=question_type, written_parts=written_parts,
            keywords_1=keywords_1, keywords_2=keywords_2,
        ))
        await s.commit()

async def mark_wrong_question(telegram_id: int, question_id: int):
    """Foydalanuvchi xato qilgan savolni qayd etish"""
    async with _conn.AsyncSessionLocal() as s:
        existing = await s.execute(
            select(UserWrongQuestion).where(
                UserWrongQuestion.telegram_id == telegram_id,
                UserWrongQuestion.question_id == question_id
            )
        )
        existing = existing.scalar_one_or_none()
        if existing:
            existing.wrong_count += 1
            existing.last_wrong = datetime.utcnow()
        else:
            s.add(UserWrongQuestion(
                telegram_id=telegram_id,
                question_id=question_id,
                wrong_count=1
            ))
        await s.commit()

async def mark_correct_question(telegram_id: int, question_id: int):
    """Foydalanuvchi to'g'ri javob bergan savolni xatolar ro'yxatidan olib tashlash"""
    async with _conn.AsyncSessionLocal() as s:
        await s.execute(
            delete(UserWrongQuestion).where(
                UserWrongQuestion.telegram_id == telegram_id,
                UserWrongQuestion.question_id == question_id
            )
        )
        await s.commit()

async def get_question_by_id(qid: int):
    async with _conn.AsyncSessionLocal() as s:
        r = await s.execute(select(Question).where(Question.id == qid))
        return r.scalar_one_or_none()

async def update_question(qid: int, **kwargs):
    allowed = ['subject','category','subcategory','difficulty','is_attestation',
               'order_num','question_text','option_a','option_b','option_c',
               'option_d','correct_answer','image_file_id']
    values = {k: v for k, v in kwargs.items() if k in allowed}
    if not values:
        return
    async with _conn.AsyncSessionLocal() as s:
        await s.execute(update(Question).where(Question.id == qid).values(**values))
        await s.commit()

async def delete_question(qid: int):
    async with _conn.AsyncSessionLocal() as s:
        await s.execute(delete(Question).where(Question.id == qid))
        await s.commit()

async def get_all_questions() -> list:
    """Bazadagi barcha savollarni qaytaradi."""
    async with _conn.AsyncSessionLocal() as s:
        r = await s.execute(
            select(Question).order_by(Question.subject, Question.category, Question.subcategory, Question.order_num, Question.id)
        )
        return r.scalars().all()

async def get_questions_page(subject=None, category=None, offset=0, limit=5):
    async with _conn.AsyncSessionLocal() as s:
        filters = []
        if subject:  filters.append(Question.subject == subject)
        if category: filters.append(Question.category == category)
        q = select(Question).order_by(Question.id.desc()).offset(offset).limit(limit)
        if filters:
            q = q.where(*filters)
        r = await s.execute(q)
        return r.scalars().all()

async def search_questions(keyword: str, subject: str = None):
    async with _conn.AsyncSessionLocal() as s:
        filters = [Question.question_text.ilike(f"%{keyword}%")]
        if subject:
            filters.append(Question.subject == subject)
        r = await s.execute(
            select(Question).where(*filters).order_by(Question.id.desc()).limit(30)
        )
        return r.scalars().all()

# ──────────────────────────────────────────────
# TEST RESULTS
# ──────────────────────────────────────────────

async def save_test_result(telegram_id, subject, category, subcategory,
                            difficulty, correct, wrong, skipped,
                            is_attestation=False) -> float:
    async with _conn.AsyncSessionLocal() as s:
        total = correct + wrong + skipped
        score = round((correct / total) * 100, 1) if total > 0 else 0.0

        # Attempt raqamini hisoblash
        r = await s.execute(
            select(func.count()).select_from(TestResult).where(
                TestResult.telegram_id == telegram_id,
                TestResult.subject == subject,
                TestResult.category == category,
                TestResult.subcategory == subcategory,
                TestResult.difficulty == difficulty,
            )
        )
        attempt = (r.scalar() or 0) + 1

        s.add(TestResult(
            telegram_id=telegram_id, subject=subject,
            category=category, subcategory=subcategory,
            difficulty=difficulty, is_attestation=is_attestation,
            total=total, correct=correct, wrong=wrong,
            skipped=skipped, score=score,
            attempt_number=attempt,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow()
        ))
        await s.commit()
        return score

async def get_user_results(telegram_id: int, limit: int = 10):
    async with _conn.AsyncSessionLocal() as s:
        r = await s.execute(
            select(TestResult)
            .where(TestResult.telegram_id == telegram_id)
            .order_by(TestResult.finished_at.desc())
            .limit(limit)
        )
        return r.scalars().all()

# ──────────────────────────────────────────────
# LEADERBOARD
# ──────────────────────────────────────────────

async def get_leaderboard(limit: int = 10):
    async with _conn.AsyncSessionLocal() as s:
        r = await s.execute(
            select(
                User.full_name,
                User.username,
                func.max(TestResult.score).label('best_score'),
                func.count(TestResult.id).label('attempts'),
            )
            .join(User, TestResult.telegram_id == User.telegram_id)
            .group_by(TestResult.telegram_id, User.full_name, User.username)
            .order_by(func.max(TestResult.score).desc())
            .limit(limit)
        )
        return r.all()

# ──────────────────────────────────────────────
# STATISTICS
# ──────────────────────────────────────────────

async def get_full_stats() -> dict:
    async with _conn.AsyncSessionLocal() as s:
        async def scalar(q):
            r = await s.execute(q)
            return r.scalar() or 0

        from database.models import Subscription
        now = datetime.utcnow()

        stats = {
            # Foydalanuvchilar
            'total_users':         await scalar(select(func.count()).select_from(User)),
            'registered':          await scalar(select(func.count()).select_from(User).where(User.is_registered == True)),
            # To'lovlar
            'pending':             await scalar(select(func.count()).select_from(Purchase).where(Purchase.status == 'pending')),
            'confirmed_purchases': await scalar(select(func.count()).select_from(Purchase).where(Purchase.status == 'confirmed')),
            # Faol obunalar
            'active_daily':        await scalar(
                select(func.count()).select_from(Subscription)
                .join(Purchase, Subscription.purchase_id == Purchase.id)
                .where(Subscription.expires_at > now, Subscription.sub_type == 'daily',
                       Purchase.status == 'confirmed')
            ),
            'active_monthly':      await scalar(
                select(func.count()).select_from(Subscription)
                .join(Purchase, Subscription.purchase_id == Purchase.id)
                .where(Subscription.expires_at > now, Subscription.sub_type == 'monthly',
                       Purchase.status == 'confirmed')
            ),
            # Testlar
            'total_tests':         await scalar(select(func.count()).select_from(TestResult)),
            'today_tests':         await scalar(
                select(func.count()).select_from(TestResult)
                .where(TestResult.finished_at >= datetime(now.year, now.month, now.day))
            ),
            # Savollar
            'total_questions':     await scalar(select(func.count()).select_from(Question)),
            'onatili_q':           await scalar(select(func.count()).select_from(Question).where(Question.subject == 'onatili')),
            'adabiyot_q':          await scalar(select(func.count()).select_from(Question).where(Question.subject == 'adabiyot')),
            'attestation_q':       await scalar(select(func.count()).select_from(Question).where(Question.subject == 'attestation')),
            'milliy_q':            await scalar(select(func.count()).select_from(Question).where(Question.subject == 'milliy')),
        }
        avg_r = await s.execute(select(func.avg(TestResult.score)))
        avg = avg_r.scalar()
        stats['avg_score'] = round(float(avg), 1) if avg else 0
        return stats

async def delete_questions_by_filter(subject: str = None, category: str = None,
                                       subcategory: str = None,
                                       subcategory_prefix: str = None) -> int:
    """Bo'lim bo'yicha savollarni o'chirish. subcategory_prefix — LIKE filter."""
    async with _conn.AsyncSessionLocal() as s:
        filters = []
        if subject:            filters.append(Question.subject == subject)
        if category:           filters.append(Question.category == category)
        if subcategory:        filters.append(Question.subcategory == subcategory)
        if subcategory_prefix: filters.append(Question.subcategory.like(f"{subcategory_prefix}%"))
        q = delete(Question)
        if filters:
            q = q.where(*filters)
        result = await s.execute(q)
        await s.commit()
        return result.rowcount

async def delete_all_questions() -> int:
    """Barcha savollarni o'chirish, o'chirilgan soni qaytaradi"""
    async with _conn.AsyncSessionLocal() as s:
        result = await s.execute(delete(Question))
        await s.commit()
        return result.rowcount