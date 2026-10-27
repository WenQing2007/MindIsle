from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PROJECT_ROOT)

import database as db
import risk
from ai_agents.coordinator import MultiAgentCoordinator

db.init_db()
# 确保演示登录账号存在（2025212121 / 123456），已存在则忽略
db.add_test_student()
app = FastAPI(title="MindIsle 心屿后端", version="0.1.0")

# 官方跨域中间件，删除了之前冲突的自定义CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = MultiAgentCoordinator()

# 登录请求体模型
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/student/login")
def student_login(req: LoginRequest):
    # 从数据库校验账号密码
    student = db.get_student_by_account(req.username, req.password)
    if not student:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    # 返回token和学生信息
    return {
        "code":200,
        "msg":"登录成功",
        "data":{
            "token": f"token_{student['id']}",
            "student_id": student["id"],
            "username": student["username"]
        }
    }

def _student_id_from_token(authorization: str | None) -> int | None:
    """从 Authorization: Bearer token_<id> 解析出 student_id；失败返回 None。"""
    if not authorization:
        return None
    # 兼容 "Bearer token_1" / "token_1"
    token = authorization.removeprefix("Bearer ").strip()
    if not token.startswith("token_"):
        return None
    suffix = token.removeprefix("token_")
    if not suffix.isdigit():
        return None
    return int(suffix)

class ChatRequest(BaseModel):
    student_id: int
    message: str
    session_id: int | None = None

@app.get("/")
def root():
    return {"message": "心屿后端运行成功"}

@app.get("/health")
def health():
    stats = db.get_stats()
    return {"status": "ok", "stats": stats}

@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message 不能为空")
    student = db.get_student(req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"学生 {req.student_id} 不存在")
    if req.session_id is None:
        session_id = db.create_session(req.student_id)
    else:
        session = db.get_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"会话 {req.session_id} 不存在")
        session_id = req.session_id
    user_text = req.message.strip()
    db.add_message(session_id, "user", user_text)
    risk_result = risk.assess(user_text)
    ai_result = orchestrator.process_dialogue(user_text, session_id=str(session_id))
    db.add_message(session_id, "assistant", ai_result["response_text"])
    db.add_risk_assessment(
        session_id,
        risk_level=risk_result["level_db"],
        score=risk_result["score"],
        indicators=",".join(risk_result["matched"]) if risk_result["matched"] else "",
    )
    is_vetoed = ai_result["is_vetoed"] or risk.is_critical(risk_result["level"])
    return {
        "session_id": session_id,
        "student_id": req.student_id,
        "reply": ai_result["response_text"],
        "risk_level": risk_result["level"],
        "risk_score": risk_result["score"],
        "risk_matched": risk_result["matched"],
        "is_vetoed": is_vetoed,
        "action": ai_result["action"],
        "reason": ai_result["reason"],
        "routed_agents": ai_result.get("routed_agents", []),
        "hotline": ai_result.get("hotline"),
        "collaboration_log": orchestrator.get_collaboration_log(),
    }

@app.get("/chat/sessions/{student_id}")
def list_sessions(student_id: int):
    sessions = db.get_sessions_by_student(student_id)
    return {"student_id": student_id, "sessions": sessions}

@app.get("/chat/{session_id}")
def get_chat_history(session_id: int):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    messages = db.get_messages(session_id)
    return {"session": session, "messages": messages}

@app.post("/chat/sessions/{session_id}/end")
def end_chat(session_id: int):
    db.end_session(session_id)
    return {"session_id": session_id, "status": "ended"}


# ============================================================
# 树洞
# ============================================================

class TreeHoleRequest(BaseModel):
    content: str
    is_anonymous: int = 1


@app.post("/api/treehole/add")
def add_treehole(req: TreeHoleRequest, authorization: str | None = Header(default=None)):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    student_id = _student_id_from_token(authorization)
    if student_id is None:
        # 前端未带 token 时无法记录发布人；回退为匿名发布
        student_id = None
    record = db.add_treehole(student_id, req.content.strip(), is_anonymous=req.is_anonymous)
    return {"code": 200, "msg": "发布成功", "data": record}


@app.get("/api/treehole/list")
def list_treeholes():
    records = db.get_all_treeholes()
    return {"code": 200, "msg": "ok", "data": records}


@app.get("/api/treehole/my")
def my_treeholes(authorization: str | None = Header(default=None)):
    student_id = _student_id_from_token(authorization)
    if student_id is None:
        raise HTTPException(status_code=401, detail="未登录")
    records = db.get_treeholes_by_student(student_id)
    return {"code": 200, "msg": "ok", "data": records}


# ============================================================
# 心理报告
# ============================================================

class ReportRequest(BaseModel):
    session_id: int
    report_type: str = "counseling"
    title: str = ""
    content: str = ""


@app.post("/api/report/add")
def add_report(req: ReportRequest):
    if not req.session_id:
        raise HTTPException(status_code=400, detail="session_id 不能为空")
    report_id = db.add_report(
        req.session_id,
        req.report_type,
        req.title or "心理报告",
        req.content,
    )
    row = db.get_report(report_id)
    return {"code": 200, "msg": "报告已生成", "data": row}


@app.get("/api/report/list/{session_id}")
def list_reports_by_session(session_id: int):
    records = db.get_reports_by_session(session_id)
    return {"code": 200, "msg": "ok", "data": records}


@app.get("/api/report/my")
def my_reports(authorization: str | None = Header(default=None)):
    student_id = _student_id_from_token(authorization)
    if student_id is None:
        raise HTTPException(status_code=401, detail="未登录")
    records = db.get_reports_by_student(student_id)
    return {"code": 200, "msg": "ok", "data": records}
