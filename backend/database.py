import sqlite3
import os
import hashlib
import secrets
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mindisle.db")


def _ensure_db_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_connection():
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS student (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            gender        TEXT,
            age           INTEGER,
            school        TEXT,
            grade         TEXT,
            created_at    TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_session (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            started_at    TEXT    NOT NULL,
            ended_at      TEXT,
            FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chat_message (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    INTEGER NOT NULL,
            role          TEXT    NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content       TEXT    NOT NULL,
            emotion       TEXT,
            created_at    TEXT    NOT NULL,
            FOREIGN KEY (session_id) REFERENCES chat_session(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS risk_assessment (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    INTEGER NOT NULL,
            risk_level    TEXT    NOT NULL CHECK(risk_level IN ('low', 'medium', 'high', 'critical')),
            score         REAL,
            indicators    TEXT,
            assessed_at   TEXT    NOT NULL,
            FOREIGN KEY (session_id) REFERENCES chat_session(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS report (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    INTEGER NOT NULL,
            report_type   TEXT    NOT NULL CHECK(report_type IN ('counseling', 'warning', 'weekly')),
            title         TEXT,
            content       TEXT    NOT NULL,
            file_path     TEXT,
            created_at    TEXT    NOT NULL,
            FOREIGN KEY (session_id) REFERENCES chat_session(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_account (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL CHECK(role IN ('student', 'teacher', 'admin')),
            student_id    INTEGER,
            token         TEXT,
            created_at    TEXT    NOT NULL,
            FOREIGN KEY (student_id) REFERENCES student(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS treehole (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            content       TEXT    NOT NULL,
            author_name   TEXT    DEFAULT '匿名用户',
            created_at    TEXT    NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_message_session ON chat_message(session_id);
        CREATE INDEX IF NOT EXISTS idx_assessment_session ON risk_assessment(session_id);
        CREATE INDEX IF NOT EXISTS idx_report_session    ON report(session_id);
        CREATE INDEX IF NOT EXISTS idx_session_student   ON chat_session(student_id);
        """)


# ============================================================
# 学生信息
# ============================================================

def add_student(name, gender=None, age=None, school=None, grade=None):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO student (name, gender, age, school, grade, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name, gender, age, school, grade, datetime.now().isoformat(timespec="seconds"))
        )
        return cur.lastrowid


def get_student(student_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM student WHERE id = ?", (student_id,)).fetchone()
        return dict(row) if row else None


def get_all_students():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM student ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def update_student(student_id, **kwargs):
    allowed = {"name", "gender", "age", "school", "grade"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [student_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE student SET {set_clause} WHERE id = ?", values)
        return True


def delete_student(student_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM student WHERE id = ?", (student_id,))


# ============================================================
# 聊天会话 & 消息
# ============================================================

def create_session(student_id):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO chat_session (student_id, started_at) VALUES (?, ?)",
            (student_id, datetime.now().isoformat(timespec="seconds"))
        )
        return cur.lastrowid


def end_session(session_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE chat_session SET ended_at = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), session_id)
        )


def add_message(session_id, role, content, emotion=None):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO chat_message (session_id, role, content, emotion, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, emotion, datetime.now().isoformat(timespec="seconds"))
        )
        return cur.lastrowid


def get_session(session_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM chat_session WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None


def get_sessions_by_student(student_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_session WHERE student_id = ? ORDER BY started_at DESC",
            (student_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_messages(session_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_message WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_messages_for_student(student_id):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT m.* FROM chat_message m
            JOIN chat_session s ON m.session_id = s.id
            WHERE s.student_id = ?
            ORDER BY m.created_at ASC
        """, (student_id,)).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# 风险评估
# ============================================================

def add_risk_assessment(session_id, risk_level, score=None, indicators=None):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO risk_assessment (session_id, risk_level, score, indicators, assessed_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, risk_level, score, indicators, datetime.now().isoformat(timespec="seconds"))
        )
        return cur.lastrowid


def get_risk_by_session(session_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM risk_assessment WHERE session_id = ? ORDER BY assessed_at DESC",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_latest_risk(session_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM risk_assessment WHERE session_id = ? ORDER BY assessed_at DESC LIMIT 1",
            (session_id,)
        ).fetchone()
        return dict(row) if row else None


def get_student_risk_history(student_id):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT r.* FROM risk_assessment r
            JOIN chat_session s ON r.session_id = s.id
            WHERE s.student_id = ?
            ORDER BY r.assessed_at DESC
        """, (student_id,)).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# 报告
# ============================================================

def add_report(session_id, report_type, title, content, file_path=None):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO report (session_id, report_type, title, content, file_path, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, report_type, title, content, file_path, datetime.now().isoformat(timespec="seconds"))
        )
        return cur.lastrowid


def get_report(report_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM report WHERE id = ?", (report_id,)).fetchone()
        return dict(row) if row else None


def get_reports_by_session(session_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM report WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_reports_by_student(student_id):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT r.* FROM report r
            JOIN chat_session s ON r.session_id = s.id
            WHERE s.student_id = ?
            ORDER BY r.created_at DESC
        """, (student_id,)).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# 统计 / 工具
# ============================================================

def get_stats():
    with get_connection() as conn:
        stats = {}
        stats["student_count"]  = conn.execute("SELECT COUNT(*) FROM student").fetchone()[0]
        stats["session_count"]  = conn.execute("SELECT COUNT(*) FROM chat_session").fetchone()[0]
        stats["message_count"]  = conn.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0]
        stats["report_count"]   = conn.execute("SELECT COUNT(*) FROM report").fetchone()[0]
        risk_rows = conn.execute(
            "SELECT risk_level, COUNT(*) FROM risk_assessment GROUP BY risk_level"
        ).fetchall()
        stats["risk_distribution"] = {row[0]: row[1] for row in risk_rows}
        return stats


# ============================================================
# 用户账号 & 登录
# ============================================================

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _gen_token() -> str:
    return secrets.token_hex(24)


def create_user(username: str, password: str, role: str, student_id: int | None = None):
    pw_hash = _hash_password(password)
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO user_account (username, password_hash, role, student_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, pw_hash, role, student_id, datetime.now().isoformat(timespec="seconds"))
        )
        return cur.lastrowid


def authenticate(username: str, password: str):
    pw_hash = _hash_password(password)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_account WHERE username = ? AND password_hash = ?",
            (username, pw_hash)
        ).fetchone()
        if not row:
            return None
        token = _gen_token()
        conn.execute("UPDATE user_account SET token = ? WHERE id = ?", (token, row["id"]))
        user = dict(row)
        user["token"] = token
        return user


def get_user_by_token(token: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_account WHERE token = ?", (token,)
        ).fetchone()
        return dict(row) if row else None


def clear_token(user_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE user_account SET token = NULL WHERE id = ?", (user_id,))


def seed_default_users():
    with get_connection() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM user_account").fetchone()[0]
        if existing > 0:
            return
        student_id = add_student("王小明", gender="男", age=16, school="示例中学", grade="高二(1)班")
        create_user("student", "123456", "student", student_id)
        create_user("teacher", "123456", "teacher")
        create_user("admin", "123456", "admin")


# ============================================================
# 树洞
# ============================================================

def add_treehole(content: str, author_name: str = "匿名用户"):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO treehole (content, author_name, created_at) VALUES (?, ?, ?)",
            (content, author_name, datetime.now().isoformat(timespec="seconds"))
        )
        return cur.lastrowid


def get_treehole_list(limit: int = 100):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, content, author_name, created_at FROM treehole ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def delete_treehole(hole_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM treehole WHERE id = ?", (hole_id,))


if __name__ == "__main__":
    init_db()
    seed_default_users()
    print(f"数据库初始化完成: {DB_PATH}")
    print("统计信息:", get_stats())