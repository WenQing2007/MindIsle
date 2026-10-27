from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PROJECT_ROOT)

import database as db
import risk
import report as report_mod
from src.agent_core import ACPSMultiAgentOrchestrator

db.init_db()
db.seed_default_users()

app = FastAPI(title="MindIsle 心屿后端", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = ACPSMultiAgentOrchestrator()
security = HTTPBearer(auto_error=False)


def ok(data=None, msg="ok"):
    return {"code": 200, "data": data, "msg": msg}


def fail(code: int, msg: str):
    return {"code": code, "data": None, "msg": msg}


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None:
        return None
    token = credentials.credentials
    return db.get_user_by_token(token)


# ============================================================
# 根 & 健康检查
# ============================================================

@app.get("/")
def root():
    return {"message": "心屿后端运行成功"}


@app.get("/health")
def health():
    stats = db.get_stats()
    return ok(stats)


# ============================================================
# 登录 / 登出
# ============================================================

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/student/login")
def student_login(req: LoginRequest):
    user = db.authenticate(req.username, req.password)
    if not user:
        return fail(401, "账号或密码错误")
    if user["role"] != "student":
        return fail(403, "该账号不是学生角色")
    student = db.get_student(user["student_id"]) if user.get("student_id") else None
    return ok({
        "token": user["token"],
        "userType": "student",
        "student_id": user.get("student_id"),
        "name": student["name"] if student else req.username,
    })


@app.post("/api/teacher/login")
def teacher_login(req: LoginRequest):
    user = db.authenticate(req.username, req.password)
    if not user:
        return fail(401, "账号或密码错误")
    if user["role"] != "teacher":
        return fail(403, "该账号不是教师角色")
    return ok({
        "token": user["token"],
        "userType": "teacher",
        "name": req.username,
    })


@app.post("/api/admin/login")
def admin_login(req: LoginRequest):
    user = db.authenticate(req.username, req.password)
    if not user:
        return fail(401, "账号或密码错误")
    if user["role"] != "admin":
        return fail(403, "该账号不是管理员角色")
    return ok({
        "token": user["token"],
        "userType": "admin",
        "name": req.username,
    })


@app.post("/api/logout")
def logout(user=Depends(get_current_user)):
    if user:
        db.clear_token(user["id"])
    return ok(msg="已登出")


# ============================================================
# 树洞
# ============================================================

class TreeHolePost(BaseModel):
    content: str


@app.get("/api/treehole/list")
def treehole_list():
    items = db.get_treehole_list()
    return ok(items)


@app.post("/api/treehole/add")
def treehole_add(post: TreeHolePost):
    if not post.content or not post.content.strip():
        return fail(400, "内容不能为空")
    hole_id = db.add_treehole(post.content.strip())
    return ok({"id": hole_id})


# ============================================================
# AI 聊天
# ============================================================

class ChatSendRequest(BaseModel):
    student_id: int
    message: str
    session_id: int | None = None


@app.post("/api/chat/send")
def chat_send(req: ChatSendRequest):
    if not req.message or not req.message.strip():
        return fail(400, "message 不能为空")

    student = db.get_student(req.student_id)
    if not student:
        return fail(404, f"学生 {req.student_id} 不存在")

    if req.session_id is None:
        session_id = db.create_session(req.student_id)
    else:
        session = db.get_session(req.session_id)
        if not session:
            return fail(404, f"会话 {req.session_id} 不存在")
        session_id = req.session_id

    user_text = req.message.strip()
    db.add_message(session_id, "user", user_text)

    risk_result = risk.assess(user_text)
    ai_result = orchestrator.process_dialogue(user_text)

    db.add_message(session_id, "assistant", ai_result["response_text"])
    db.add_risk_assessment(
        session_id,
        risk_level=risk_result["level_db"],
        score=risk_result["score"],
        indicators=",".join(risk_result["matched"]) if risk_result["matched"] else "",
    )

    is_vetoed = ai_result["is_vetoed"] or risk.is_critical(risk_result["level"])

    return ok({
        "session_id": session_id,
        "student_id": req.student_id,
        "reply": ai_result["response_text"],
        "risk_level": risk_result["level"],
        "risk_level_cn": {"green": "绿", "yellow": "黄", "orange": "橙", "red": "红"}.get(risk_result["level"], risk_result["level"]),
        "risk_score": risk_result["score"],
        "risk_matched": risk_result["matched"],
        "is_vetoed": is_vetoed,
        "action": ai_result["action"],
        "reason": ai_result["reason"],
        "crisis_hotline": "400-161-9995" if is_vetoed else None,
    })


@app.get("/api/chat/sessions")
def chat_list_sessions(student_id: int):
    sessions = db.get_sessions_by_student(student_id)
    return ok(sessions)


@app.get("/api/chat/history")
def chat_history(session_id: int):
    session = db.get_session(session_id)
    if not session:
        return fail(404, f"会话 {session_id} 不存在")
    messages = db.get_messages(session_id)
    return ok({"session": session, "messages": messages})


@app.post("/api/chat/sessions/{session_id}/end")
def chat_end(session_id: int):
    db.end_session(session_id)
    return ok({"session_id": session_id, "status": "ended"})


# ============================================================
# 教师预警
# ============================================================

@app.get("/api/teacher/warnings")
def teacher_warnings():
    all_students = db.get_all_students()
    warnings = []
    level_cn_map = {"low": "绿", "medium": "黄", "high": "橙", "critical": "红"}
    for s in all_students:
        sessions = db.get_sessions_by_student(s["id"])
        if not sessions:
            continue
        latest_risk = db.get_student_risk_history(s["id"])
        if not latest_risk:
            continue
        latest = latest_risk[0]
        if latest["risk_level"] in ("medium", "high", "critical"):
            warnings.append({
                "student_id": s["id"],
                "name": s["name"],
                "school": s.get("school", ""),
                "grade": s.get("grade", ""),
                "risk_level": latest["risk_level"],
                "risk_level_cn": level_cn_map.get(latest["risk_level"], latest["risk_level"]),
                "risk_score": latest["score"],
                "indicators": latest.get("indicators", ""),
                "assessed_at": latest["assessed_at"],
            })
    warnings.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2}.get(x["risk_level"], 9))
    return ok(warnings)


# ============================================================
# 报告
# ============================================================

@app.post("/api/report/student/{student_id}")
def gen_student_report(student_id: int):
    student = db.get_student(student_id)
    if not student:
        return fail(404, f"学生 {student_id} 不存在")
    sessions = db.get_sessions_by_student(student_id)
    messages = db.get_all_messages_for_student(student_id)
    risk_history = db.get_student_risk_history(student_id)
    filepath = report_mod.generate_student_report(student, sessions, messages, risk_history)
    import database
    report_id = database.add_report(
        session_id=sessions[0]["id"] if sessions else 0,
        report_type="counseling",
        title=os.path.basename(filepath),
        content="学生个体心理成长报告",
        file_path=filepath,
    )
    return ok({"report_id": report_id, "filepath": filepath})


@app.post("/api/report/class")
def gen_class_report(class_name: str):
    students = db.get_all_students()
    risk_records = []
    for s in students:
        risk_records.extend(db.get_student_risk_history(s["id"]))
    filepath = report_mod.generate_class_report(class_name, students, risk_records)
    return ok({"filepath": filepath})


@app.get("/api/report/download")
def download_report(filepath: str):
    if not os.path.isfile(filepath):
        return fail(404, "文件不存在")
    return FileResponse(filepath, media_type="application/pdf", filename=os.path.basename(filepath))


# ============================================================
# 学生列表（教师/管理员用）
# ============================================================

@app.get("/api/students")
def list_students():
    students = db.get_all_students()
    return ok(students)