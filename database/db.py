import sqlite3
import os
from datetime import datetime

DB_PATH = "database/bot.db"

def get_connection():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            phone_number TEXT,
            full_name TEXT,
            username TEXT,
            is_registered INTEGER DEFAULT 0,
            is_paid INTEGER DEFAULT 0,
            payment_confirmed INTEGER DEFAULT 0,
            registered_at TEXT,
            paid_at TEXT
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            amount INTEGER DEFAULT 15000,
            check_photo_id TEXT,
            status TEXT DEFAULT 'pending',
            submitted_at TEXT,
            confirmed_at TEXT,
            confirmed_by INTEGER,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            score INTEGER,
            total_questions INTEGER DEFAULT 30,
            correct_answers INTEGER,
            wrong_answers INTEGER,
            started_at TEXT,
            finished_at TEXT,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            difficulty TEXT DEFAULT 'medium'
        );
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# ============ USER FUNCTIONS ============

def get_user(telegram_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(telegram_id: int, full_name: str, username: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO users (telegram_id, full_name, username, registered_at)
            VALUES (?, ?, ?, ?)
        """, (telegram_id, full_name, username, datetime.now().isoformat()))
        conn.commit()
    except Exception as e:
        print(f"Error creating user: {e}")
    finally:
        conn.close()

def update_user_phone(telegram_id: int, phone: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET phone_number = ?, is_registered = 1
        WHERE telegram_id = ?
    """, (phone, telegram_id))
    conn.commit()
    conn.close()

def is_user_registered(telegram_id: int) -> bool:
    user = get_user(telegram_id)
    return bool(user and user['is_registered'])

def is_user_paid(telegram_id: int) -> bool:
    user = get_user(telegram_id)
    return bool(user and user['payment_confirmed'])

# ============ PAYMENT FUNCTIONS ============

def create_payment(telegram_id: int, check_photo_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO payments (telegram_id, check_photo_id, submitted_at)
        VALUES (?, ?, ?)
    """, (telegram_id, check_photo_id, datetime.now().isoformat()))
    payment_id = cursor.lastrowid

    # Update user paid status (pending)
    cursor.execute("UPDATE users SET is_paid = 1 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()
    return payment_id

def confirm_payment(telegram_id: int, admin_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE payments
        SET status = 'confirmed', confirmed_at = ?, confirmed_by = ?
        WHERE telegram_id = ? AND status = 'pending'
    """, (datetime.now().isoformat(), admin_id, telegram_id))

    cursor.execute("""
        UPDATE users SET payment_confirmed = 1, paid_at = ?
        WHERE telegram_id = ?
    """, (datetime.now().isoformat(), telegram_id))

    conn.commit()
    conn.close()

def reject_payment(telegram_id: int, admin_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE payments
        SET status = 'rejected', confirmed_at = ?, confirmed_by = ?
        WHERE telegram_id = ? AND status = 'pending'
    """, (datetime.now().isoformat(), admin_id, telegram_id))

    cursor.execute("""
        UPDATE users SET is_paid = 0 WHERE telegram_id = ?
    """, (telegram_id,))

    conn.commit()
    conn.close()

def get_pending_payments():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, u.full_name, u.phone_number, u.username
        FROM payments p
        JOIN users u ON p.telegram_id = u.telegram_id
        WHERE p.status = 'pending'
        ORDER BY p.submitted_at DESC
    """)
    payments = cursor.fetchall()
    conn.close()
    return payments

# ============ TEST FUNCTIONS ============

def get_random_questions(subject: str = "ona_tili", count: int = 30):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM questions
        WHERE subject = ?
        ORDER BY RANDOM()
        LIMIT ?
    """, (subject, count))
    questions = cursor.fetchall()
    conn.close()
    return questions

def save_test_result(telegram_id: int, correct: int, wrong: int, started_at: str):
    conn = get_connection()
    cursor = conn.cursor()
    score = round((correct / 30) * 100, 1)
    cursor.execute("""
        INSERT INTO test_results
        (telegram_id, score, correct_answers, wrong_answers, started_at, finished_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (telegram_id, score, correct, wrong, started_at, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_results(telegram_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM test_results
        WHERE telegram_id = ?
        ORDER BY finished_at DESC
        LIMIT 5
    """, (telegram_id,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY registered_at DESC")
    users = cursor.fetchall()
    conn.close()
    return users