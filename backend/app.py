from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from typing import Optional
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PROJECT_ROOT)

def _load_dotenv(path: str) -> None:
    """极简 .env 加载器（不依赖 python-dotenv）：把 KEY=VALUE 写入进程环境变量，
    已存在的环境变量（如 shell 中显式导出）优先，不会被覆盖。"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key and not os.environ.get(key):
                os.environ[key] = value

# 启动时加载根目录 .env（LLM_API_KEY 等敏感配置放在这里，.gitignore 已忽略 .env）
_load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import database as db
import risk
import report as report_mod
from ai_agents.coordinator import MultiAgentCoordinator
from ai_agents import llm as llm_client
import voice

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

orchestrator = MultiAgentCoordinator()
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

@app.get("/health")
def health():
    stats = db.get_stats()
    llm_cfg = llm_client.get_config()
    return ok({
        "stats": stats,
        "llm": {
            "enabled": llm_client.is_enabled(),
            "status_text": llm_client.status_text(),
            "base": llm_cfg["base"],
            "model": llm_cfg["model"],
            "key_set": bool(llm_cfg["key"]),
        },
    })


# ============================================================
# 注册 / 登录 / 登出
# ============================================================

class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    school: Optional[str] = None
    grade: Optional[str] = None


@app.post("/api/student/register")
def student_register(req: RegisterRequest):
    if not req.username or not req.password or not req.name:
        return fail(400, "用户名、密码、姓名不能为空")
    if len(req.username) < 3:
        return fail(400, "用户名至少3个字符")
    if len(req.password) < 6:
        return fail(400, "密码至少6个字符")
    result, err = db.register_student(
        username=req.username,
        password=req.password,
        name=req.name,
        gender=req.gender,
        age=req.age,
        school=req.school,
        grade=req.grade,
    )
    if err:
        return fail(400, err)
    return ok(result, msg="注册成功")


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

class TeacherRegisterRequest(BaseModel):
    username: str
    password: str
    name: str
    school: str
    department: Optional[str] = None
    phone: Optional[str] = None


@app.post("/api/teacher/register")
def teacher_register(req: TeacherRegisterRequest):
    print("✅ 收到教师注册：", req.model_dump())
    return ok(msg="教师注册成功（临时测试，不存入数据库）")



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


class CommentPost(BaseModel):
    hole_id: int
    content: str


@app.get("/api/treehole/comments")
def treehole_comments(hole_id: int):
    comments = db.get_treehole_comments(hole_id)
    return ok(comments)


@app.post("/api/treehole/comment/add")
def treehole_comment_add(post: CommentPost):
    if not post.content or not post.content.strip():
        return fail(400, "评论内容不能为空")
    cid = db.add_treehole_comment(post.hole_id, post.content.strip())
    return ok({"id": cid})


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
    # 组装多轮对话历史（去掉刚插入的当前 user 消息），供 LLM 上下文记忆；
    # 协调器会自行截取最近 8 条。无历史时传空列表等价于首轮对话。
    raw_messages = db.get_messages(session_id)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in raw_messages[:-1]
        if m["role"] in ("user", "assistant")
    ]
    risk_result = risk.assess(user_text)
    ai_result = orchestrator.process_dialogue(
        user_text, session_id=str(session_id), history=history
    )
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
        session_id=sessions[0]["id"] if sessions else None,
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


class CrisisReportRequest(BaseModel):
    student_id: int
    session_id: Optional[int] = None  # 不传时自动定位该学生最近一次橙/红危机事件


@app.post("/api/report/crisis")
def gen_crisis_report(req: CrisisReportRequest):
    """危机事件处置报告：定位学生的危机（橙/红）事件并生成处置报告 PDF。"""
    student = db.get_student(req.student_id)
    if not student:
        return fail(404, f"学生 {req.student_id} 不存在")

    # 1) 定位目标会话：优先指定 session_id，否则取该学生最近一次橙/红风险所在的会话
    if req.session_id is not None:
        session_risks = db.get_risk_by_session(req.session_id)
    else:
        history = db.get_student_risk_history(req.student_id)
        crisis = next(
            (h for h in history if h["risk_level"] in ("critical", "high")), None
        )
        if not crisis:
            return fail(400, "该学生暂无危机（橙/红）事件记录，无法生成处置报告")
        req.session_id = crisis["session_id"]
        session_risks = db.get_risk_by_session(req.session_id)

    # 2) 取该会话中最近一次橙/红评估记录作为触发风险
    risk_record = next(
        (r for r in session_risks if r["risk_level"] in ("critical", "high")),
        None,
    )
    if not risk_record:
        return fail(400, "该会话无危机（橙/红）评估记录")

    # 3) 取完整对话，触发消息取该会话最后一条学生输入
    msgs = db.get_messages(req.session_id)
    user_msgs = [m for m in msgs if m["role"] == "user"]
    if not user_msgs:
        return fail(400, "该会话无对话内容")
    triggering = user_msgs[-1]

    # 4) 生成 PDF 并落库
    filepath = report_mod.generate_crisis_report(
        student, triggering, risk_record, msgs
    )
    report_id = db.add_report(
        session_id=req.session_id,
        report_type="warning",
        title=f"危机事件处置报告 — {student['name']}",
        content=(
            f"学生 {student['name']} 危机事件处置记录上报（风险等级="
            f"{risk_record.get('risk_level', '-')}，命中指标="
            f"{risk_record.get('indicators', '') or '-'}）"
        ),
        file_path=filepath,
    )
    return ok({"report_id": report_id, "filepath": filepath})


@app.get("/api/report/list")
def report_list(student_id: int):
    student = db.get_student(student_id)
    if not student:
        return fail(404, f"学生 {student_id} 不存在")
    reports = db.get_reports_by_student(student_id)
    return ok(reports)


@app.get("/api/report/detail")
def report_detail(report_id: int):
    report = db.get_report(report_id)
    if not report:
        return fail(404, f"报告 {report_id} 不存在")
    return ok(report)


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


# ============================================================
# 前端 SPA 托管（dist/ 目录）
# ============================================================

FRONTEND_DIST = os.path.join(PROJECT_ROOT, "Mindlsle_fronted", "frontend", "dist")

if os.path.isdir(FRONTEND_DIST):
    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback(request, exc):
        if exc.status_code == 404 and request.headers.get("accept", "").startswith("text/html"):
            return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
        raise exc

    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/")
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str = ""):
        target = os.path.join(FRONTEND_DIST, full_path) if full_path else os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))


# ============================================================
# 语音（STT / TTS）—— 方案 B：后端云端语音
#   TTS: edge-tts 合成中文 mp3，存 audio/tts_cache/ 供前端播放
#   STT: faster-whisper 识别上传音频，返回文字
# ============================================================

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None


@app.post("/api/voice/tts")
def voice_tts(req: TTSRequest):
    """把文本合成为中文语音 mp3，返回可播放的 URL。"""
    if not req.text or not req.text.strip():
        return fail(400, "text 不能为空")
    try:
        res = voice.text_to_speech(req.text, voice=req.voice or voice.DEFAULT_TTS_VOICE)
    except Exception as exc:
        return fail(500, f"语音合成失败: {exc}")
    return ok(res)


@app.get("/api/voice/audio/{filename}")
def voice_audio(filename: str):
    """播放语音模块合成的音频（仅允许 audio/tts_cache 目录内的合法音频文件）。"""
    safe = os.path.basename(filename)
    path = os.path.join(voice.TTS_CACHE_DIR, safe)
    if not voice.is_audio_filename(safe) or not os.path.isfile(path):
        return fail(404, "音频不存在")
    return FileResponse(path, media_type=voice.audio_media_type(path), filename=safe)


@app.post("/api/voice/stt")
async def voice_stt(file: UploadFile = File(...)):
    """上传一段音频（wav/mp3/m4a/ogg，建议≤60秒），返回识别出的文字。"""
    raw = await file.read()
    if not raw:
        return fail(400, "音频内容为空")
    if not voice.is_audio_filename(file.filename or ""):
        return fail(400, "不支持的音频格式，请上传 wav/mp3/m4a/ogg")
    try:
        text = voice.transcribe_upload(raw, file.filename or "upload.wav")
    except Exception as exc:
        return fail(500, f"语音识别失败: {exc}")
    return ok({"text": text, "language": "zh"})
