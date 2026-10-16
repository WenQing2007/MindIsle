from fastapi import FastAPI, HTTPException
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
from src.agent_core import ACPSMultiAgentOrchestrator

db.init_db()

app = FastAPI(title="MindIsle 心屿后端", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = ACPSMultiAgentOrchestrator()


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

    ai_result = orchestrator.process_dialogue(user_text)

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