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
            score REAL,
            total_questions INTEGER DEFAULT 30,
            correct_answers INTEGER,
            wrong_answers INTEGER,
            difficulty TEXT DEFAULT 'mixed',
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
            difficulty TEXT DEFAULT 'medium',
            image_file_id TEXT
        );
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialized!")

# ============ USER ============

def get_user(telegram_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return row

def create_user(telegram_id, full_name, username=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR IGNORE INTO users (telegram_id, full_name, username, registered_at) VALUES (?,?,?,?)",
            (telegram_id, full_name, username, datetime.now().isoformat())
        )
        conn.commit()
    finally:
        conn.close()

def update_user_phone(telegram_id, phone):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET phone_number=?, is_registered=1 WHERE telegram_id=?", (phone, telegram_id))
    conn.commit()
    conn.close()

def is_user_registered(telegram_id):
    u = get_user(telegram_id)
    return bool(u and u['is_registered'])

def is_user_paid(telegram_id):
    u = get_user(telegram_id)
    return bool(u and u['payment_confirmed'])

def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY registered_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

# ============ PAYMENT ============

def create_payment(telegram_id, check_photo_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO payments (telegram_id, check_photo_id, submitted_at) VALUES (?,?,?)",
        (telegram_id, check_photo_id, datetime.now().isoformat())
    )
    pid = cur.lastrowid
    cur.execute("UPDATE users SET is_paid=1 WHERE telegram_id=?", (telegram_id,))
    conn.commit()
    conn.close()
    return pid

def confirm_payment(telegram_id, admin_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE payments SET status='confirmed', confirmed_at=?, confirmed_by=? WHERE telegram_id=? AND status='pending'",
        (datetime.now().isoformat(), admin_id, telegram_id)
    )
    cur.execute(
        "UPDATE users SET payment_confirmed=1, paid_at=? WHERE telegram_id=?",
        (datetime.now().isoformat(), telegram_id)
    )
    conn.commit()
    conn.close()

def reject_payment(telegram_id, admin_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE payments SET status='rejected', confirmed_at=?, confirmed_by=? WHERE telegram_id=? AND status='pending'",
        (datetime.now().isoformat(), admin_id, telegram_id)
    )
    cur.execute("UPDATE users SET is_paid=0 WHERE telegram_id=?", (telegram_id,))
    conn.commit()
    conn.close()

def get_pending_payments():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.*, u.full_name, u.phone_number, u.username
        FROM payments p JOIN users u ON p.telegram_id=u.telegram_id
        WHERE p.status='pending' ORDER BY p.submitted_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

# ============ QUESTIONS ============

def get_random_questions(subject="ona_tili", count=30, difficulty=None):
    conn = get_connection()
    cur = conn.cursor()
    if difficulty and difficulty != 'mixed':
        cur.execute(
            "SELECT * FROM questions WHERE subject=? AND difficulty=? ORDER BY RANDOM() LIMIT ?",
            (subject, difficulty, count)
        )
    else:
        cur.execute(
            "SELECT * FROM questions WHERE subject=? ORDER BY RANDOM() LIMIT ?",
            (subject, count)
        )
    rows = cur.fetchall()
    conn.close()
    return rows

def add_question(subject, question_text, option_a, option_b, option_c, option_d,
                 correct_answer, difficulty="medium", image_file_id=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO questions
        (subject, question_text, option_a, option_b, option_c, option_d, correct_answer, difficulty, image_file_id)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (subject, question_text, option_a, option_b, option_c, option_d,
          correct_answer, difficulty, image_file_id))
    conn.commit()
    conn.close()

def get_questions_count(subject="ona_tili", difficulty=None):
    conn = get_connection()
    cur = conn.cursor()
    if difficulty:
        cur.execute("SELECT COUNT(*) FROM questions WHERE subject=? AND difficulty=?", (subject, difficulty))
    else:
        cur.execute("SELECT COUNT(*) FROM questions WHERE subject=?", (subject,))
    count = cur.fetchone()[0]
    conn.close()
    return count

# ============ TEST RESULTS ============

def save_test_result(telegram_id, correct, wrong, started_at, difficulty="mixed"):
    conn = get_connection()
    cur = conn.cursor()
    total = correct + wrong
    score = round((correct / total) * 100, 1) if total > 0 else 0
    cur.execute("""
        INSERT INTO test_results
        (telegram_id, score, correct_answers, wrong_answers, difficulty, started_at, finished_at)
        VALUES (?,?,?,?,?,?,?)
    """, (telegram_id, score, correct, wrong, difficulty, started_at, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_results(telegram_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM test_results WHERE telegram_id=?
        ORDER BY finished_at DESC LIMIT 5
    """, (telegram_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

# ============ LEADERBOARD ============

def get_leaderboard(limit=10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.full_name, u.username, MAX(r.score) as best_score,
               COUNT(r.id) as attempts, MAX(r.correct_answers) as best_correct
        FROM test_results r
        JOIN users u ON r.telegram_id = u.telegram_id
        GROUP BY r.telegram_id
        ORDER BY best_score DESC, best_correct DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

# ============ STATISTICS ============

def get_daily_stats():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DATE(registered_at) as date, COUNT(*) as new_users
        FROM users
        WHERE registered_at >= DATE('now', '-7 days')
        GROUP BY DATE(registered_at)
        ORDER BY date
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_full_stats():
    conn = get_connection()
    cur = conn.cursor()
    stats = {}
    cur.execute("SELECT COUNT(*) FROM users")
    stats['total_users'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE is_registered=1")
    stats['registered'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE payment_confirmed=1")
    stats['paid'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM payments WHERE status='pending'")
    stats['pending_payments'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM test_results")
    stats['total_tests'] = cur.fetchone()[0]
    cur.execute("SELECT AVG(score) FROM test_results")
    avg = cur.fetchone()[0]
    stats['avg_score'] = round(avg, 1) if avg else 0
    cur.execute("SELECT COUNT(*) FROM questions")
    stats['total_questions'] = cur.fetchone()[0]
    conn.close()
    return stats

# ============ QUESTION CRUD ============

def get_question_by_id(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
    row = cur.fetchone()
    conn.close()
    return row

def update_question(question_id, question_text=None, option_a=None, option_b=None,
                    option_c=None, option_d=None, correct_answer=None,
                    difficulty=None, image_file_id=None):
    conn = get_connection()
    cur = conn.cursor()
    fields = []
    values = []
    if question_text is not None:
        fields.append("question_text = ?"); values.append(question_text)
    if option_a is not None:
        fields.append("option_a = ?"); values.append(option_a)
    if option_b is not None:
        fields.append("option_b = ?"); values.append(option_b)
    if option_c is not None:
        fields.append("option_c = ?"); values.append(option_c)
    if option_d is not None:
        fields.append("option_d = ?"); values.append(option_d)
    if correct_answer is not None:
        fields.append("correct_answer = ?"); values.append(correct_answer)
    if difficulty is not None:
        fields.append("difficulty = ?"); values.append(difficulty)
    if image_file_id is not None:
        fields.append("image_file_id = ?"); values.append(image_file_id)
    if not fields:
        conn.close()
        return
    values.append(question_id)
    cur.execute(f"UPDATE questions SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()

def delete_question(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()

def search_questions(keyword, subject="ona_tili"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM questions
        WHERE subject = ? AND question_text LIKE ?
        ORDER BY id DESC LIMIT 20
    """, (subject, f"%{keyword}%"))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_questions_page(subject="ona_tili", offset=0, limit=5):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM questions WHERE subject = ?
        ORDER BY id DESC LIMIT ? OFFSET ?
    """, (subject, limit, offset))
    rows = cur.fetchall()
    conn.close()
    return rows