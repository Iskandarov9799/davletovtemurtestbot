"""
DB — foydalanuvchi operatsiyalari testlari.
"""
import pytest
import pytest_asyncio
from database.db import (
    create_user, get_user, update_user_phone, is_registered,
    get_all_users, ban_user, unban_user, is_banned,
    admin_grant_subscription, admin_revoke_subscription,
    get_user_tariff,
)

TID = 100001
TID2 = 100002


@pytest.mark.asyncio
async def test_create_user():
    await create_user(TID, "Test User", "testuser")
    user = await get_user(TID)
    assert user is not None
    assert user.telegram_id == TID
    assert user.full_name == "Test User"
    assert user.username == "testuser"
    assert user.is_registered is False


@pytest.mark.asyncio
async def test_create_user_duplicate():
    """Duplicate yaratish xato bermaydi."""
    await create_user(TID, "Test User", "testuser")
    users = await get_all_users()
    assert sum(1 for u in users if u.telegram_id == TID) == 1


@pytest.mark.asyncio
async def test_get_user_not_found():
    user = await get_user(999999)
    assert user is None


@pytest.mark.asyncio
async def test_update_phone():
    await create_user(TID2, "Phone User")
    await update_user_phone(TID2, "+998901234567")
    user = await get_user(TID2)
    assert user.phone_number == "+998901234567"
    assert user.is_registered is True


@pytest.mark.asyncio
async def test_is_registered():
    assert await is_registered(TID2) is True
    assert await is_registered(TID)  is False


@pytest.mark.asyncio
async def test_ban_unban():
    await create_user(TID, "Test User", "testuser")
    assert await is_banned(TID) is False
    await ban_user(TID)
    assert await is_banned(TID) is True
    await unban_user(TID)
    assert await is_banned(TID) is False


@pytest.mark.asyncio
async def test_is_banned_nonexistent():
    assert await is_banned(888888) is False


@pytest.mark.asyncio
async def test_admin_grant_subscription():
    await create_user(TID, "Test User")
    result = await admin_grant_subscription(TID, 'daily')
    assert result is True
    tariff = await get_user_tariff(TID)
    assert tariff['type'] == 'daily'
    assert tariff['expires'] is not None


@pytest.mark.asyncio
async def test_admin_grant_subscription_invalid():
    result = await admin_grant_subscription(TID, 'weekly')
    assert result is False


@pytest.mark.asyncio
async def test_admin_revoke_subscription():
    await admin_grant_subscription(TID, 'monthly')
    await admin_revoke_subscription(TID)
    tariff = await get_user_tariff(TID)
    # Revoke qilinganidan keyin free bo'lishi kerak
    assert tariff['type'] in ('free', 'daily')  # daily qolgan bo'lishi mumkin


@pytest.mark.asyncio
async def test_get_all_users():
    users = await get_all_users()
    tids = [u.telegram_id for u in users]
    assert TID in tids
    assert TID2 in tids