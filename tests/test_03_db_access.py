"""
DB — kirish huquqlari: bepul, to'lov, attestatsiya.
"""
import pytest
from database.db import (
    create_user, get_access_status, mark_free_used,
    has_attestation, grant_attestation,
    create_purchase, confirm_purchase, get_purchase_by_id,
    reject_purchase, get_pending_purchases,
    grant_subscription, get_active_subscription,
    reset_all_subscriptions,
)

TID = 300001
ACCESS_KEY = "onatili:mavzu:fonetika"


@pytest.mark.asyncio
async def test_access_free_first_time():
    await create_user(TID, "Access User")
    status = await get_access_status(TID, ACCESS_KEY)
    assert status == 'free'


@pytest.mark.asyncio
async def test_access_buy_after_free():
    await mark_free_used(TID, ACCESS_KEY)
    status = await get_access_status(TID, ACCESS_KEY)
    assert status == 'buy'


@pytest.mark.asyncio
async def test_mark_free_used_idempotent():
    """Ikki marta chaqirish xato chiqarmasin."""
    await mark_free_used(TID, ACCESS_KEY)
    await mark_free_used(TID, ACCESS_KEY)
    status = await get_access_status(TID, ACCESS_KEY)
    assert status == 'buy'


@pytest.mark.asyncio
async def test_access_paid_with_subscription():
    """Faol subscription bo'lsa 'paid' qaytarishi kerak."""
    purchase_id = await create_purchase(TID, 'daily', 10000, 'test_check')
    await confirm_purchase(purchase_id, 999)
    await grant_subscription(TID, 'daily', purchase_id)
    status = await get_access_status(TID, ACCESS_KEY)
    assert status == 'paid'


@pytest.mark.asyncio
async def test_get_active_subscription():
    sub = await get_active_subscription(TID)
    assert sub is not None
    assert sub.sub_type == 'daily'


@pytest.mark.asyncio
async def test_attestation_not_purchased():
    assert await has_attestation(TID, 'bolim_1') is False


@pytest.mark.asyncio
async def test_grant_and_check_attestation():
    await grant_attestation(TID, 'bolim_1', 'miniapp')
    assert await has_attestation(TID, 'bolim_1') is True


@pytest.mark.asyncio
async def test_attestation_bolim_isolated():
    """Har bo'lim mustaqil bo'lishi kerak."""
    assert await has_attestation(TID, 'bolim_2') is False
    await grant_attestation(TID, 'bolim_2', 'miniapp')
    assert await has_attestation(TID, 'bolim_2') is True
    assert await has_attestation(TID, 'bolim_3') is False


@pytest.mark.asyncio
async def test_grant_attestation_idempotent():
    """Bir xil bo'limni ikki marta grant qilsa xato bermaydi."""
    await grant_attestation(TID, 'bolim_1', 'miniapp')
    await grant_attestation(TID, 'bolim_1', 'miniapp')
    assert await has_attestation(TID, 'bolim_1') is True


@pytest.mark.asyncio
async def test_create_and_get_purchase():
    pid = await create_purchase(TID, 'daily', 10000, 'photo_file_id', retry_key='onatili:aralash:None')
    p = await get_purchase_by_id(pid)
    assert p is not None
    assert p.status == 'pending'
    assert p.amount == 10000
    assert p.product_type == 'daily'


@pytest.mark.asyncio
async def test_confirm_purchase():
    pid = await create_purchase(TID, 'monthly', 100000, 'photo2')
    await confirm_purchase(pid, 999)
    p = await get_purchase_by_id(pid)
    assert p.status == 'confirmed'
    assert p.confirmed_by == 999


@pytest.mark.asyncio
async def test_reject_purchase():
    pid = await create_purchase(TID, 'daily', 10000, 'photo3')
    await reject_purchase(pid, 999)
    p = await get_purchase_by_id(pid)
    assert p.status == 'rejected'


@pytest.mark.asyncio
async def test_get_purchase_not_found():
    p = await get_purchase_by_id(999999)
    assert p is None


@pytest.mark.asyncio
async def test_get_pending_purchases():
    await create_user(TID, "Access User")
    await create_purchase(TID, 'daily', 10000, 'pending_photo')
    pending = await get_pending_purchases()
    assert len(pending) >= 1


@pytest.mark.asyncio
async def test_reset_all_subscriptions():
    """Reset barcha subscription va attestation o'chirishi kerak."""
    await grant_attestation(TID, 'bolim_5', 'miniapp')
    assert await has_attestation(TID, 'bolim_5') is True
    await reset_all_subscriptions()
    assert await has_attestation(TID, 'bolim_5') is False
    sub = await get_active_subscription(TID)
    assert sub is None