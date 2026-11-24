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
            session_id    INTEGER,
            report_type   TEXT    NOT NULL CHECK(report_type IN ('counseling', 'warning', 'weekly')),
            title         TEXT,
            content       TEXT    NOT NULL,
            file_path     TEXT,
            created_at    TEXT    NOT NULL,
            FOREIGN KEY (session_id) REFERENCES chat_session(id) ON DELETE SET NULL
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
            created_at    TEXT    NOT NULL,
            status        TEXT    NOT NULL DEFAULT 'approved',
            reviewed_by   TEXT,
            reviewed_at   TEXT
        );

        CREATE TABLE IF NOT EXISTS treehole_comment (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            hole_id       INTEGER NOT NULL,
            content       TEXT    NOT NULL,
            author_name   TEXT    DEFAULT '匿名树洞友',
            created_at    TEXT    NOT NULL,
            FOREIGN KEY (hole_id) REFERENCES treehole(id) ON DELETE CASCADE
        );

        -- 心理资源（内容管理：科普音频 / 放松训练 / 文字文章等）
        CREATE TABLE IF NOT EXISTS resource (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT    NOT NULL,
            res_type      TEXT    NOT NULL DEFAULT 'article',
            url           TEXT,
            content       TEXT,
            status        TEXT    NOT NULL DEFAULT 'published',
            created_at    TEXT    NOT NULL,
            updated_at    TEXT    NOT NULL
        );

        -- 登录日志
        CREATE TABLE IF NOT EXISTS login_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER,
            username      TEXT,
            role          TEXT,
            success       INTEGER NOT NULL DEFAULT 0,
            detail        TEXT,
            ip            TEXT,
            created_at    TEXT    NOT NULL
        );

        -- 操作日志（后台管理动作）
        CREATE TABLE IF NOT EXISTS operation_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER,
            username      TEXT,
            role          TEXT,
            action        TEXT    NOT NULL,
            detail        TEXT,
            created_at    TEXT    NOT NULL
        );

        -- 系统配置（安全配置：危机热线等）
        CREATE TABLE IF NOT EXISTS system_config (
            key           TEXT    PRIMARY KEY,
            value         TEXT,
            updated_at    TEXT    NOT NULL
        );

        -- 后台可管理的风险关键词（默认与内置规则一致；管理员增删后即时生效）
        CREATE TABLE IF NOT EXISTS risk_keyword (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            level         TEXT    NOT NULL CHECK(level IN ('green','yellow','orange','red')),
            keyword       TEXT    NOT NULL,
            enabled       INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT    NOT NULL,
            UNIQUE(level, keyword)
        );

        CREATE INDEX IF NOT EXISTS idx_message_session ON chat_message(session_id);
        CREATE INDEX IF NOT EXISTS idx_assessment_session ON risk_assessment(session_id);
        CREATE INDEX IF NOT EXISTS idx_report_session    ON report(session_id);
        CREATE INDEX IF NOT EXISTS idx_session_student   ON chat_session(student_id);
        CREATE INDEX IF NOT EXISTS idx_login_log_time    ON login_log(created_at);
        CREATE INDEX IF NOT EXISTS idx_operation_log_time ON operation_log(created_at);
        """)

        _migrate_report_session_nullable(conn)
        _migrate_treehole_status(conn)


def _migrate_treehole_status(conn):
    """为旧版 treehole 表补齐 status / reviewed_by / reviewed_at 审核字段（幂等）。"""
    cols = conn.execute("PRAGMA table_info(treehole)").fetchall()
    names = {c[1] for c in cols}
    if "status" not in names:
        conn.execute("ALTER TABLE treehole ADD COLUMN status TEXT NOT NULL DEFAULT 'approved'")
    if "reviewed_by" not in names:
        conn.execute("ALTER TABLE treehole ADD COLUMN reviewed_by TEXT")
    if "reviewed_at" not in names:
        conn.execute("ALTER TABLE treehole ADD COLUMN reviewed_at TEXT")


def _migrate_report_session_nullable(conn):
    """旧版 report 表 session_id 是 NOT NULL + CASCADE，导致无会话的学生无法生成报告。
    SQLite 不支持 ALTER COLUMN，这里通过重建表做一次幂等迁移。"""
    cols = conn.execute("PRAGMA table_info(report)").fetchall()
    session_col = next((c for c in cols if c[1] == "session_id"), None)
    if session_col and session_col[3] == 1:
        conn.executescript("""
            CREATE TABLE report_new (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id    INTEGER,
                report_type   TEXT    NOT NULL CHECK(report_type IN ('counseling', 'warning', 'weekly')),
                title         TEXT,
                content       TEXT    NOT NULL,
                file_path     TEXT,
                created_at    TEXT    NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_session(id) ON DELETE SET NULL
            );
            INSERT OR IGNORE INTO report_new SELECT * FROM report;
            DROP TABLE IF EXISTS report;
            ALTER TABLE report_new RENAME TO report;
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


def username_exists(username: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM user_account WHERE username = ?", (username,)).fetchone()
        return row[0] > 0


def create_user(username: str, password: str, role: str, student_id: int | None = None):
    pw_hash = _hash_password(password)
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO user_account (username, password_hash, role, student_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, pw_hash, role, student_id, datetime.now().isoformat(timespec="seconds"))
        )
        return cur.lastrowid


def register_student(username: str, password: str, name: str, gender=None, age=None, school=None, grade=None):
    if username_exists(username):
        return None, "用户名已被占用"
    student_id = add_student(name, gender=gender, age=age, school=school, grade=grade)
    user_id = create_user(username, password, "student", student_id)
    return {"user_id": user_id, "student_id": student_id}, None


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
    """学生端可见的树洞：仅返回已审核通过（approved）的条目。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, content, author_name, created_at FROM treehole "
            "WHERE status = 'approved' ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def list_treehole_admin(status: str | None = None, limit: int = 200):
    """后台：按审核状态列出全部树洞（含未审核/拒绝的）。"""
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM treehole WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM treehole ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["comment_count"] = conn.execute(
                "SELECT COUNT(*) FROM treehole_comment WHERE hole_id = ?", (d["id"],)
            ).fetchone()[0]
            result.append(d)
        return result


def set_treehole_status(hole_id: int, status: str, reviewer: str | None = None):
    """后台：审核树洞（approved/rejected/flagged），记录审核人。"""
    allowed = {"approved", "rejected", "flagged"}
    if status not in allowed:
        return False
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE treehole SET status = ?, reviewed_by = ?, reviewed_at = ? WHERE id = ?",
            (status, reviewer, datetime.now().isoformat(timespec="seconds"), hole_id)
        )
        return cur.rowcount > 0


def delete_treehole(hole_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM treehole WHERE id = ?", (hole_id,))


def add_treehole_comment(hole_id: int, content: str, author_name: str = "匿名树洞友"):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO treehole_comment (hole_id, content, author_name, created_at) VALUES (?, ?, ?, ?)",
            (hole_id, content, author_name, datetime.now().isoformat(timespec="seconds"))
        )
        return cur.lastrowid


def get_treehole_comments(hole_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, hole_id, content, author_name, created_at FROM treehole_comment WHERE hole_id = ? ORDER BY created_at ASC",
            (hole_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def count_treehole_comments(hole_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM treehole_comment WHERE hole_id = ?",
            (hole_id,)
        ).fetchone()
        return row["c"] if row else 0


# ============================================================
# 心理资源（内容管理）
# ============================================================

def add_resource(title: str, res_type: str = "article", url: str | None = None,
                 content: str | None = None, status: str = "published") -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO resource (title, res_type, url, content, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, res_type, url, content, status, now, now)
        )
        return cur.lastrowid


def list_resources(limit: int = 200):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM resource ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_resource(resource_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM resource WHERE id = ?", (resource_id,)).fetchone()
        return dict(row) if row else None


def update_resource(resource_id: int, **kwargs):
    allowed = {"title", "res_type", "url", "content", "status"}
    fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if "title" in fields and not str(fields["title"]).strip():
        fields.pop("title", None)
    if not fields:
        return False
    fields["updated_at"] = datetime.now().isoformat(timespec="seconds")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with get_connection() as conn:
        cur = conn.execute(
            f"UPDATE resource SET {set_clause} WHERE id = ?",
            list(fields.values()) + [resource_id]
        )
        return cur.rowcount > 0


def delete_resource(resource_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM resource WHERE id = ?", (resource_id,))
        return cur.rowcount > 0


# ============================================================
# 日志（登录日志 & 操作日志）
# ============================================================

def add_login_log(username: str, role: str, success: bool, detail: str = "",
                  user_id: int | None = None, ip: str | None = None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO login_log (user_id, username, role, success, detail, ip, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, role, 1 if success else 0, detail, ip,
             datetime.now().isoformat(timespec="seconds"))
        )


def list_login_logs(limit: int = 100):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM login_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def add_operation_log(username: str, role: str, action: str, detail: str = "",
                      user_id: int | None = None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO operation_log (user_id, username, role, action, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, role, action, detail,
             datetime.now().isoformat(timespec="seconds"))
        )


def list_operation_logs(limit: int = 100):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM operation_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# 系统配置（安全配置：危机热线等）
# ============================================================

def get_config(key: str, default: str | None = None) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM system_config WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default


def set_config(key: str, value: str):
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO system_config (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, now)
        )


# ============================================================
# 风险关键词（安全配置）
# ============================================================

def list_all_risk_keywords():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM risk_keyword ORDER BY CASE level "
            "WHEN 'green' THEN 0 WHEN 'yellow' THEN 1 WHEN 'orange' THEN 2 ELSE 3 END, "
            "created_at, id"
        ).fetchall()
        return [dict(r) for r in rows]


def list_enabled_risk_keywords():
    """返回当前启用的 (level, keyword) 列表，供 backend/risk.py 合并。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT level, keyword FROM risk_keyword WHERE enabled = 1"
        ).fetchall()
        return [(r["level"], r["keyword"]) for r in rows]


def add_risk_keyword(level: str, keyword: str) -> tuple[int | None, str | None]:
    if level not in ("green", "yellow", "orange", "red"):
        return None, "风险等级非法"
    keyword = (keyword or "").strip()
    if not keyword:
        return None, "关键词不能为空"
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO risk_keyword (level, keyword, enabled, created_at) VALUES (?, ?, 1, ?)",
                (level, keyword, datetime.now().isoformat(timespec="seconds"))
            )
            return cur.lastrowid, None
    except sqlite3.IntegrityError:
        return None, "该等级下已存在相同关键词"


def delete_risk_keyword(keyword_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM risk_keyword WHERE id = ?", (keyword_id,))
        return cur.rowcount > 0


def set_risk_keyword_enabled(keyword_id: int, enabled: bool) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE risk_keyword SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, keyword_id)
        )
        return cur.rowcount > 0


# ============================================================
# 用户管理（后台：账户 增删改查）
# ============================================================

def list_accounts(role: str | None = None):
    """后台查看账号：学生关联姓名；教师/管理员以用户名展示。"""
    with get_connection() as conn:
        sql = ("SELECT u.id, u.username, u.role, u.student_id, u.created_at, "
               "s.name AS student_name, s.gender, s.age, s.school, s.grade "
               "FROM user_account u LEFT JOIN student s ON u.student_id = s.id")
        params: list = []
        if role:
            sql += " WHERE u.role = ?"
            params.append(role)
        sql += " ORDER BY u.created_at DESC"
        rows = conn.execute(sql, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["display_name"] = d["student_name"] or d["username"]
            result.append(d)
        return result


def update_account_password(user_id: int, new_password: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE user_account SET password_hash = ? WHERE id = ?",
            (_hash_password(new_password), user_id)
        )
        return cur.rowcount > 0


def update_account_role(user_id: int, role: str) -> bool:
    if role not in ("student", "teacher", "admin"):
        return False
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE user_account SET role = ? WHERE id = ?", (role, user_id)
        )
        return cur.rowcount > 0


def update_account_username(user_id: int, username: str) -> tuple[bool, str | None]:
    username = (username or "").strip()
    if not username or len(username) < 3:
        return False, "用户名至少3个字符"
    with get_connection() as conn:
        try:
            cur = conn.execute(
                "UPDATE user_account SET username = ? WHERE id = ?", (username, user_id)
            )
            return cur.rowcount > 0, None
        except sqlite3.IntegrityError:
            return False, "用户名已被占用"


def admin_create_account(role: str, username: str, password: str,
                         name: str | None = None, gender: str | None = None,
                         age: int | None = None, school: str | None = None,
                         grade: str | None = None) -> tuple[int | None, str | None]:
    """后台创建账户：学生角色会同时创建 student 档案并关联。"""
    if role not in ("student", "teacher", "admin"):
        return None, "角色非法"
    if not username or len(username.strip()) < 3:
        return None, "用户名至少3个字符"
    if not password or len(password) < 6:
        return None, "密码至少6个字符"
    username = username.strip()
    if username_exists(username):
        return None, "用户名已被占用"
    student_id = None
    if role == "student":
        student_id = add_student(name or username, gender=gender, age=age,
                                 school=school, grade=grade)
    user_id = create_user(username, password, role, student_id)
    return user_id, None


def delete_account(user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM user_account WHERE id = ?", (user_id,))
        return cur.rowcount > 0


if __name__ == "__main__":
    init_db()
    seed_default_users()
    print(f"数据库初始化完成: {DB_PATH}")
    print("统计信息:", get_stats())