"""
Integratsiya testlari — to'liq foydalanuvchi oqimlari.
"""
import pytest
from database.db import (
    create_user, get_access_status, mark_free_used,
    create_purchase, confirm_purchase, grant_subscription,
    get_active_subscription, grant_attestation, has_attestation,
    add_question, get_questions, count_questions,
    save_test_result, get_user_results, reset_all_subscriptions,
    ban_user, is_banned,
)

TID = 500001


@pytest.mark.asyncio
async def test_full_free_to_paid_flow():
    """
    To'liq oqim: ro'yxatdan o'tish → bepul test → to'lov → pullik test.
    """
    # 1. Foydalanuvchi yaratish
    await create_user(TID, "Integration User", "intuser")

    # 2. Birinchi urinish bepul
    key = "onatili:mavzu:leksikologiya"
    assert await get_access_status(TID, key) == 'free'
    await mark_free_used(TID, key)
    assert await get_access_status(TID, key) == 'buy'

    # 3. Kunlik obuna sotib olish
    pid = await create_purchase(TID, 'daily', 10_000, 'check_photo')
    await confirm_purchase(pid, 999)
    await grant_subscription(TID, 'daily', pid)

    # 4. Endi paid status
    assert await get_access_status(TID, key) == 'paid'

    # 5. Faol subscription bor
    sub = await get_active_subscription(TID)
    assert sub is not None
    assert sub.sub_type == 'daily'


@pytest.mark.asyncio
async def test_full_attestation_flow():
    """
    Attestatsiya oqimi: bo'lim tanlash → to'lov → huquq berish → test ishlash.
    """
    await create_user(TID, "Integration User")

    # 1. Bo'lim sotib olinmagan
    assert await has_attestation(TID, 'bolim_7') is False

    # 2. To'lov
    pid = await create_purchase(TID, 'attestation', 5_000, 'att_check', retry_key='bolim_7')
    await confirm_purchase(pid, 999)
    await grant_attestation(TID, 'bolim_7', 'miniapp')

    # 3. Huquq berildi
    assert await has_attestation(TID, 'bolim_7') is True

    # 4. Boshqa bo'limlar hali yo'q
    assert await has_attestation(TID, 'bolim_8') is False

    # 5. Savollar qo'shish va olish
    await add_question(
        subject='attestation', category='attestation', subcategory='bolim_7',
        question_text='7-bo\'lim integratsiya savoli',
        option_a='A', option_b='B', option_c='C', option_d='D',
        correct_answer='C', is_attestation=True, order_num=1
    )
    qs = await get_questions(
        'attestation', 'attestation',
        subcategory='bolim_7', is_attestation=True, count=35
    )
    assert len(qs) >= 1

    # 6. Natija saqlash
    score = await save_test_result(
        telegram_id=TID, subject='attestation', category='attestation',
        subcategory='bolim_7', difficulty=None,
        correct=25, wrong=8, skipped=2, is_attestation=True
    )
    assert score > 0


@pytest.mark.asyncio
async def test_reset_clears_everything():
    """
    Reset barcha huquqlarni tozalaydi.
    """
    await create_user(TID, "Reset User")
    pid = await create_purchase(TID, 'monthly', 100_000, 'monthly_check')
    await confirm_purchase(pid, 999)
    await grant_subscription(TID, 'monthly', pid)
    await grant_attestation(TID, 'bolim_9', 'miniapp')

    assert await get_active_subscription(TID) is not None
    assert await has_attestation(TID, 'bolim_9') is True

    await reset_all_subscriptions()

    assert await get_active_subscription(TID) is None
    assert await has_attestation(TID, 'bolim_9') is False


@pytest.mark.asyncio
async def test_ban_blocks_access():
    """
    Ban qilingan foydalanuvchi is_banned() True qaytaradi.
    """
    await create_user(TID, "Ban Test User")
    assert await is_banned(TID) is False
    await ban_user(TID)
    assert await is_banned(TID) is True
    # Unban
    from database.db import unban_user
    await unban_user(TID)
    assert await is_banned(TID) is False


@pytest.mark.asyncio
async def test_multiple_subjects_independent():
    """
    Har fan mustaqil — bir fanning kirish holati boshqasiga ta'sir qilmaydi.
    """
    await create_user(TID, "Multi User")
    key_onatili   = "onatili:aralash:None"
    key_adabiyot  = "adabiyot:aralash:None"

    # Ona tili bepul ishlatish
    await mark_free_used(TID, key_onatili)
    assert await get_access_status(TID, key_onatili)  == 'buy'
    assert await get_access_status(TID, key_adabiyot) == 'free'


@pytest.mark.asyncio
async def test_questions_count_accuracy():
    """
    count_questions va get_questions son mos kelishi kerak.
    """
    subject, category = 'onatili', 'mavzu'
    cnt = await count_questions(subject=subject, category=category)
    qs  = await get_questions(subject, category, count=1000)
    assert len(qs) <= cnt