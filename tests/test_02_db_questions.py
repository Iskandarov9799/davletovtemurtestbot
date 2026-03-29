"""
DB — savollar operatsiyalari testlari.
"""
import pytest
from database.db import (
    add_question, get_question_by_id, update_question, delete_question,
    get_questions, count_questions, get_questions_page, search_questions,
    get_all_questions, delete_questions_by_filter, delete_all_questions,
    mark_wrong_question, mark_correct_question,
)
from database.db import create_user

TID = 200001

SAMPLE_Q = dict(
    subject='onatili', category='mavzu', subcategory='fonetika',
    question_text='Tovushlar nechchaga bo\'linadi?',
    option_a='2 ta', option_b='3 ta', option_c='4 ta', option_d='5 ta',
    correct_answer='A',
)


@pytest.mark.asyncio
async def test_add_and_get_question():
    await add_question(**SAMPLE_Q)
    questions = await get_questions('onatili', 'mavzu', subcategory='fonetika', count=10)
    assert len(questions) >= 1
    q = questions[0]
    assert q.subject == 'onatili'
    assert q.correct_answer == 'A'


@pytest.mark.asyncio
async def test_count_questions():
    cnt = await count_questions(subject='onatili', category='mavzu', subcategory='fonetika')
    assert cnt >= 1


@pytest.mark.asyncio
async def test_get_question_by_id():
    questions = await get_questions('onatili', 'mavzu', subcategory='fonetika', count=1)
    qid = questions[0].id
    q = await get_question_by_id(qid)
    assert q is not None
    assert q.id == qid


@pytest.mark.asyncio
async def test_get_question_not_found():
    q = await get_question_by_id(999999)
    assert q is None


@pytest.mark.asyncio
async def test_update_question():
    questions = await get_questions('onatili', 'mavzu', subcategory='fonetika', count=1)
    qid = questions[0].id
    await update_question(qid, question_text="Yangilangan savol matni")
    q = await get_question_by_id(qid)
    assert q.question_text == "Yangilangan savol matni"


@pytest.mark.asyncio
async def test_update_question_invalid_field():
    questions = await get_questions('onatili', 'mavzu', subcategory='fonetika', count=1)
    qid = questions[0].id
    # Noto'g'ri field — xato chiqmasligi kerak, shunchaki o'zgarmaydi
    await update_question(qid, nonexistent_field="test")
    q = await get_question_by_id(qid)
    assert q is not None


@pytest.mark.asyncio
async def test_search_questions():
    await add_question(
        subject='onatili', category='mavzu', subcategory='imlo',
        question_text='Qaysi so\'z to\'g\'ri yozilgan?',
        option_a='kitob', option_b='kItob', option_c='KItob', option_d='KITOB',
        correct_answer='A',
    )
    results = await search_questions("to'g'ri yozilgan")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_search_questions_not_found():
    results = await search_questions("boshqa_unikal_matn_xyz_abc_123")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_get_questions_page():
    page = await get_questions_page(subject='onatili', offset=0, limit=5)
    assert isinstance(page, list)


@pytest.mark.asyncio
async def test_attestation_questions():
    await add_question(
        subject='attestation', category='attestation', subcategory='bolim_1',
        question_text='Attestatsiya 1-bo\'lim savoli',
        option_a='A', option_b='B', option_c='C', option_d='D',
        correct_answer='A', is_attestation=True, order_num=1
    )
    questions = await get_questions(
        'attestation', 'attestation',
        subcategory='bolim_1', is_attestation=True, count=35
    )
    assert len(questions) >= 1
    assert questions[0].is_attestation is True


@pytest.mark.asyncio
async def test_attestation_subcategory_filter():
    """Har bo'lim alohida filtrlanishi kerak."""
    await add_question(
        subject='attestation', category='attestation', subcategory='bolim_2',
        question_text='Attestatsiya 2-bo\'lim savoli',
        option_a='A', option_b='B', option_c='C', option_d='D',
        correct_answer='B', is_attestation=True, order_num=1
    )
    q_bolim1 = await get_questions('attestation', 'attestation',
                                    subcategory='bolim_1', is_attestation=True, count=35)
    q_bolim2 = await get_questions('attestation', 'attestation',
                                    subcategory='bolim_2', is_attestation=True, count=35)
    ids1 = {q.id for q in q_bolim1}
    ids2 = {q.id for q in q_bolim2}
    assert ids1.isdisjoint(ids2), "Bo'limlar bir-biriga aralashmasligi kerak"


@pytest.mark.asyncio
async def test_mark_wrong_and_correct():
    await create_user(TID, "Q User")
    questions = await get_questions('onatili', 'mavzu', subcategory='fonetika', count=1)
    qid = questions[0].id
    await mark_wrong_question(TID, qid)
    await mark_wrong_question(TID, qid)  # 2 marta
    await mark_correct_question(TID, qid)  # o'chirilishi kerak


@pytest.mark.asyncio
async def test_wrong_questions_priority():
    """Xato qilingan savollar birinchi kelishi kerak."""
    await create_user(TID, "Q User")
    # Savollar qo'shamiz
    for i in range(5):
        await add_question(
            subject='adabiyot', category='aralash',
            question_text=f'Adabiyot savol {i}',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A',
        )
    qs = await get_questions('adabiyot', 'aralash', count=10)
    if qs:
        await mark_wrong_question(TID, qs[0].id)
        result = await get_questions('adabiyot', 'aralash', count=10, telegram_id=TID)
        assert result[0].id == qs[0].id


@pytest.mark.asyncio
async def test_delete_question():
    await add_question(
        subject='onatili', category='aralash',
        question_text='O\'chiriladigan savol',
        option_a='A', option_b='B', option_c='C', option_d='D',
        correct_answer='A',
    )
    qs = await search_questions("O'chiriladigan savol")
    assert len(qs) >= 1
    qid = qs[0].id
    await delete_question(qid)
    q = await get_question_by_id(qid)
    assert q is None


@pytest.mark.asyncio
async def test_delete_questions_by_filter():
    subject = 'onatili'
    before = await count_questions(subject=subject, category='aralash')
    await delete_questions_by_filter(subject=subject, category='aralash')
    after = await count_questions(subject=subject, category='aralash')
    assert after == 0