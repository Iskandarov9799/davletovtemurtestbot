from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id   = Column(BigInteger, unique=True, nullable=False)
    phone_number  = Column(String(20))
    full_name     = Column(String(255))
    username      = Column(String(100))
    is_registered = Column(Boolean, default=False)
    registered_at = Column(DateTime, default=datetime.utcnow)


class Purchase(Base):
    __tablename__ = "purchases"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id  = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    # 'once' | 'daily' | 'monthly' | 'attestation_onatili' | 'attestation_adabiyot'
    product_type = Column(String(50), nullable=False)
    # 'onatili:mavzu:fonetika' kabi kalit (once uchun)
    retry_key    = Column(String(200))
    amount       = Column(Integer, nullable=False)
    check_photo  = Column(String(200))
    status       = Column(String(20), default="pending")  # pending|confirmed|rejected
    is_used      = Column(Boolean, default=False)           # once uchun: ishlatilganmi
    submitted_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)
    confirmed_by = Column(BigInteger)


class UserAccess(Base):
    """Bepul urinish holati"""
    __tablename__ = "user_access"
    __table_args__ = (UniqueConstraint("telegram_id", "access_key"),)
    id          = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    access_key  = Column(String(200), nullable=False)
    free_used   = Column(Boolean, default=False)


class Subscription(Base):
    """Kunlik / Oylik obuna"""
    __tablename__ = "subscriptions"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id  = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    # 'daily' | 'monthly'
    sub_type     = Column(String(20), nullable=False)
    started_at   = Column(DateTime, default=datetime.utcnow)
    expires_at   = Column(DateTime, nullable=False)
    purchase_id  = Column(Integer, ForeignKey("purchases.id"))


class AttestationAccess(Base):
    """Atestatsiya sotib olinganmi"""
    __tablename__ = "attestation_access"
    __table_args__ = (UniqueConstraint("telegram_id", "subject"),)
    id           = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id  = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    subject      = Column(String(50), nullable=False)
    format       = Column(String(20))
    purchased_at = Column(DateTime, default=datetime.utcnow)


class Question(Base):
    __tablename__ = "questions"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    subject        = Column(String(50), nullable=False)
    category       = Column(String(50), nullable=False)
    subcategory    = Column(String(50))
    difficulty     = Column(String(20))
    is_attestation = Column(Boolean, default=False)
    order_num      = Column(Integer)
    question_text  = Column(Text, nullable=False)
    option_a       = Column(Text)   # yozma savol uchun None bo'lishi mumkin
    option_b       = Column(Text)
    option_c       = Column(Text)
    option_d       = Column(Text)
    correct_answer = Column(String(1))  # yozma savol uchun None
    # Yozma savol uchun
    question_type  = Column(String(20), default='choice')  # 'choice' | 'written'
    written_parts  = Column(Integer, default=1)            # 1 yoki 2 (qism soni)
    keywords_1     = Column(Text)   # 1-qism kalit so'zlari (vergul bilan)
    keywords_2     = Column(Text)   # 2-qism kalit so'zlari (faqat 2 qismli uchun)
    image_file_id  = Column(String(200))
    created_at     = Column(DateTime, default=datetime.utcnow)


class UserWrongQuestion(Base):
    """Foydalanuvchi xato qilgan savollar"""
    __tablename__ = "user_wrong_questions"
    __table_args__ = (UniqueConstraint("telegram_id", "question_id"),)
    id          = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    wrong_count = Column(Integer, default=1)
    last_wrong  = Column(DateTime, default=datetime.utcnow)


class TestResult(Base):
    __tablename__ = "test_results"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id    = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    subject        = Column(String(50))
    category       = Column(String(50))
    subcategory    = Column(String(50))
    difficulty     = Column(String(20))
    is_attestation = Column(Boolean, default=False)
    total          = Column(Integer, default=35)
    correct        = Column(Integer, default=0)
    wrong          = Column(Integer, default=0)
    skipped        = Column(Integer, default=0)
    score          = Column(Numeric(5, 2), default=0)
    attempt_number = Column(Integer, default=1)
    started_at     = Column(DateTime)
    finished_at    = Column(DateTime, default=datetime.utcnow)