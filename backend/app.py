from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse
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
import emotion as emotion_mod
import report as report_mod
import report_agent as report_agent_mod
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

orchestrator = MultiAgentCoordinator(emergency_hotline=risk.get_hotline())
security = HTTPBearer(auto_error=False)


def ok(data=None, msg="ok"):
    return {"code": 200, "data": data, "msg": msg}


def fail(code: int, msg: str):
    return {"code": code, "data": None, "msg": msg}


def _log_operation(user, action: str, detail: str = ""):
    """写一条后台操作日志；user 可为 None（未登录/失败态）。"""
    try:
        db.add_operation_log(
            username=(user or {}).get("username") or "-",
            role=(user or {}).get("role") or "-",
            action=action,
            detail=detail,
            user_id=(user or {}).get("id"),
        )
    except Exception:  # noqa: BLE001 日志失败不影响主流程
        pass


def _log_login(username, role, success, detail="", user_id=None, ip=None):
    try:
        db.add_login_log(username=username, role=role, success=success,
                         detail=detail, user_id=user_id, ip=ip)
    except Exception:  # noqa: BLE001
        pass


# 最近一次协商的 ACPs 协作日志缓存：session_id -> AIP 报文列表（供后台查看）
_last_collaboration: dict = {}


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if credentials is None:
        return None
    token = credentials.credentials
    return db.get_user_by_token(token)


def require_admin(user=Depends(get_current_user)):
    """管理员鉴权：非 admin 一律 403。"""
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


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
        _log_login(req.username, "student", False, "账号或密码错误")
        return fail(401, "账号或密码错误")
    if user["role"] != "student":
        _log_login(req.username, "student", False, "非学生角色")
        return fail(403, "该账号不是学生角色")
    _log_login(req.username, "student", True, "登录成功", user_id=user["id"])
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
        _log_login(req.username, "teacher", False, "账号或密码错误")
        return fail(401, "账号或密码错误")
    if user["role"] != "teacher":
        _log_login(req.username, "teacher", False, "非教师角色")
        return fail(403, "该账号不是教师角色")
    _log_login(req.username, "teacher", True, "登录成功", user_id=user["id"])
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
    if not req.username or not req.password or not req.name:
        return fail(400, "用户名、密码、姓名不能为空")
    if len(req.username) < 3:
        return fail(400, "用户名至少3个字符")
    if len(req.password) < 6:
        return fail(400, "密码至少6个字符")
    result, err = db.register_teacher(
        username=req.username,
        password=req.password,
        name=req.name,
        school=req.school,
        department=req.department,
        phone=req.phone,
    )
    if err:
        return fail(400, err)
    return ok(result, msg="教师注册成功")



@app.post("/api/admin/login")
def admin_login(req: LoginRequest):
    user = db.authenticate(req.username, req.password)
    if not user:
        _log_login(req.username, "admin", False, "账号或密码错误")
        return fail(401, "账号或密码错误")
    if user["role"] != "admin":
        _log_login(req.username, "admin", False, "非管理员角色")
        return fail(403, "该账号不是管理员角色")
    _log_login(req.username, "admin", True, "登录成功", user_id=user["id"])
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
    emo = emotion_mod.detect(user_text)
    db.add_message(session_id, "user", user_text, emotion=emo["emotion"])
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
    # 缓存本轮 ACPs 协作日志，供后台「协作日志」查看
    _last_collaboration[str(session_id)] = orchestrator.get_collaboration_log()
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
        "emotion": emo.get("emotion"),
        "emotion_cn": emo.get("label_cn"),
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
# 学生端：情景演练成长记录 / 测评记录 / 已发布资源
# ============================================================

class ScenarioRecordBody(BaseModel):
    student_id: int
    scene_id: str
    scene_name: str = ""
    good: int = 0
    mid: int = 0
    bad: int = 0
    summary: str = ""


@app.post("/api/scenario/record")
def scenario_record_add(body: ScenarioRecordBody):
    if not db.get_student(body.student_id):
        return fail(404, f"学生 {body.student_id} 不存在")
    record_id = db.add_scenario_record(
        body.student_id, body.scene_id.strip(), body.scene_name.strip(),
        good=body.good, mid=body.mid, bad=body.bad, summary=body.summary,
    )
    return ok({"record_id": record_id}, msg="成长记录已保存")


@app.get("/api/scenario/records")
def scenario_records(student_id: int):
    records = db.get_scenario_records(student_id)
    stats = db.get_student_scenario_stats(student_id)
    return ok({"records": records, "stats": stats})


class AssessmentRecordBody(BaseModel):
    student_id: int
    scale_id: str
    scale_name: str = ""
    score: int
    level: str = ""
    level_cn: str = ""


@app.post("/api/assessment/record")
def assessment_record_add(body: AssessmentRecordBody):
    if not db.get_student(body.student_id):
        return fail(404, f"学生 {body.student_id} 不存在")
    record_id = db.add_assessment_record(
        body.student_id, body.scale_id.strip(), body.scale_name.strip(),
        body.score, body.level, body.level_cn,
    )
    return ok({"record_id": record_id}, msg="测评结果已保存")


@app.get("/api/assessment/records")
def assessment_records(student_id: int):
    return ok(db.get_assessment_records(student_id))


@app.get("/api/resources")
def student_resources():
    """学生端可见的已发布心理资源（内容管理里 status='published'）。"""
    items = db.list_resources()
    return ok({"resources": [r for r in items if r.get("status") == "published"]})


# ============================================================
# 教师预警
# ============================================================

@app.get("/api/teacher/warnings")
def teacher_warnings():
    all_students = db.get_all_students()
    warnings = []
    level_cn_map = {"low": "绿", "medium": "黄", "high": "橙", "critical": "红"}
    min_level = db.get_warning_min_level()
    order = {"critical": 0, "high": 1, "medium": 2}
    min_idx = order.get(min_level, order["medium"])
    for s in all_students:
        latest_risk = db.get_student_risk_history(s["id"])
        if not latest_risk:
            continue
        latest = latest_risk[0]
        if latest["risk_level"] not in ("medium", "high", "critical"):
            continue
        if order.get(latest["risk_level"], 99) > min_idx:
            continue  # 低于教师设置的预警阈值，不列入名单
        review = db.get_latest_warning_review(s["id"])
        warnings.append({
            "assessment_id": latest["id"],
            "student_id": s["id"],
            "name": s["name"],
            "school": s.get("school", ""),
            "grade": s.get("grade", ""),
            "risk_level": latest["risk_level"],
            "risk_level_cn": level_cn_map.get(latest["risk_level"], latest["risk_level"]),
            "risk_score": latest["score"],
            "indicators": latest.get("indicators", ""),
            "assessed_at": latest["assessed_at"],
            "review_status": review["status"] if review else "pending",
            "review_note": review["note"] if review else "",
            "review_teacher": review["teacher_name"] if review else "",
            "review_at": review["created_at"] if review else "",
        })
    # 阈值之外的（含 review 状态便于排序）按风险 + 未复核优先
    warnings.sort(key=lambda x: (order.get(x["risk_level"], 9),
                                 x["review_status"] != "pending"))
    return ok(warnings)


class WarningReviewBody(BaseModel):
    status: str   # reviewed | followed_up
    note: str = ""


@app.post("/api/teacher/warnings/{assessment_id}/review")
def teacher_warning_review(assessment_id: int, body: WarningReviewBody):
    # 按 risk_assessment.id 反查 student_id
    row = db.get_risk_by_id(assessment_id)
    if not row:
        return fail(404, f"预警 {assessment_id} 不存在")
    if body.status not in ("reviewed", "followed_up"):
        return fail(400, "复核状态非法")
    rid = db.add_warning_review(assessment_id, row["student_id"],
                                "教师", body.status, body.note.strip())
    return ok({"review_id": rid}, msg="复核已记录")


class WarningConfigBody(BaseModel):
    min_level: str


@app.get("/api/teacher/warning-config")
def teacher_warning_config():
    return ok({"min_level": db.get_warning_min_level()})


@app.post("/api/teacher/warning-config")
def teacher_warning_config_set(body: WarningConfigBody):
    if not db.set_warning_min_level(body.min_level):
        return fail(400, "阈值应为 medium/high/critical")
    return ok({"min_level": db.get_warning_min_level()}, msg="预警阈值已更新")


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

    # —— 报告生成智能体 + 合规校验 ——
    risk_dist = {}
    latest_level, latest_score = "green", 0.0
    if risk_history:
        for r in risk_history:
            lv = r.get("risk_level", "low")
            risk_dist[lv] = risk_dist.get(lv, 0) + 1
        latest_level = risk_history[0].get("risk_level", "low")
        latest_score = risk_history[0].get("score", 0.0) or 0.0
    stats = {
        "name": student.get("name", "学生"),
        "latest_level": latest_level,
        "latest_score": latest_score,
        "session_count": len(sessions),
        "user_msg_count": sum(1 for m in messages if m["role"] == "user"),
        "risk_distribution": risk_dist,
    }
    analysis = report_agent_mod.report_agent_generate(stats)
    report_full_text = (
        f"{os.path.basename(filepath)}\n"
        f"风险分布:{risk_dist}\n"
        f"最新:{latest_level}({latest_score})\n"
        f"{report_mod.AI_WATERMARK if hasattr(report_mod, 'AI_WATERMARK') else ''}\n"
        f"{analysis}"
    )
    compliance = report_agent_mod.compliance_check(
        {"text": report_full_text, "report_type": "counseling"}
    )

    import database
    report_id = database.add_report(
        session_id=sessions[0]["id"] if sessions else None,
        report_type="counseling",
        title=os.path.basename(filepath),
        content=analysis,
        file_path=filepath,
    )
    return ok({
        "report_id": report_id,
        "filepath": filepath,
        "analysis": analysis,
        "compliance": compliance,
    })


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
    # 危机报告：由"报告生成智能体"输出一段处置/分析摘要，供合规校验与展示
    crisis_analysis = report_agent_mod.report_agent_generate(
        {
            "name": student.get("name", "该学生"),
            "latest_level": risk_record.get("risk_level", "high"),
            "latest_score": risk_record.get("score", 0.0) or 0.0,
            "session_count": 1,
            "user_msg_count": len([m for m in msgs if m["role"] == "user"]),
            "risk_distribution": {risk_record.get("risk_level", "high"): 1},
        }
    )
    # 危机报告合规校验（强制要求热线 + 水印 + 无诊断结论）
    crisis_full_text = (
        f"危机处置报告 {student['name']} 等级={risk_record.get('risk_level')}\n"
        f"400-161-9995 心理援助热线\n"
        f"{crisis_analysis}\n"
        f"AI 生成内容，仅供参考，不构成诊断结论。"
    )
    compliance = report_agent_mod.compliance_check(
        {"text": crisis_full_text, "report_type": "warning", "has_crisis": True}
    )
    report_id = db.add_report(
        session_id=req.session_id,
        report_type="warning",
        title=f"危机事件处置报告 — {student['name']}",
        content=(
            f"分析摘要（AI 生成，仅供参考，不构成诊断结论）：{crisis_analysis}\n"
            f"学生 {student['name']} 危机事件处置记录上报（风险等级="
            f"{risk_record.get('risk_level', '-')}，命中指标="
            f"{risk_record.get('indicators', '') or '-'}）"
        ),
        file_path=filepath,
    )
    return ok({
        "report_id": report_id,
        "filepath": filepath,
        "analysis": crisis_analysis,
        "compliance": compliance,
    })


@app.get("/api/report/list")
def report_list(student_id: int):
    student = db.get_student(student_id)
    if not student:
        return fail(404, f"学生 {student_id} 不存在")
    reports = db.get_reports_by_student(student_id)
    return ok(reports)


@app.get("/api/report/compliance/{report_id}")
def report_compliance(report_id: int):
    """报告合规体检查询：对已生成的报告全文做合规校验并返回明细。"""
    report = db.get_report(report_id)
    if not report:
        return fail(404, f"报告 {report_id} 不存在")
    text = report.get("content") or ""
    compliance = report_agent_mod.compliance_check(
        {"text": text, "report_type": "counseling", "has_crisis": False}
    )
    return ok(compliance)


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
# 后台管理 —— 用户管理（账户增删改查）
# ============================================================

class AdminUserCreate(BaseModel):
    role: str
    username: str
    password: str
    name: str | None = None
    gender: str | None = None
    age: int | None = None
    school: str | None = None
    grade: str | None = None


class AdminUserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role: str | None = None


@app.get("/api/admin/users")
def admin_users(role: str | None = None, admin: dict = Depends(require_admin)):
    return ok(db.list_accounts(role=role))


@app.post("/api/admin/users")
def admin_user_create(req: AdminUserCreate, admin: dict = Depends(require_admin)):
    uid, err = db.admin_create_account(
        role=req.role, username=req.username, password=req.password,
        name=req.name, gender=req.gender, age=req.age,
        school=req.school, grade=req.grade,
    )
    if err:
        return fail(400, err)
    _log_operation(admin, "创建账号", f"角色={req.role}, 用户名={req.username}")
    return ok({"user_id": uid}, msg="创建成功")


@app.put("/api/admin/users/{user_id}")
def admin_user_update(user_id: int, req: AdminUserUpdate, admin: dict = Depends(require_admin)):
    if req.username:
        ok_flag, err = db.update_account_username(user_id, req.username)
        if err:
            return fail(400, err)
    if req.password:
        db.update_account_password(user_id, req.password)
    if req.role:
        db.update_account_role(user_id, req.role)
    _log_operation(admin, "修改账号", f"id={user_id}")
    return ok(msg="更新成功")


@app.delete("/api/admin/users/{user_id}")
def admin_user_delete(user_id: int, admin: dict = Depends(require_admin)):
    if not db.delete_account(user_id):
        return fail(404, "账号不存在")
    _log_operation(admin, "删除账号", f"id={user_id}")
    return ok(msg="已删除")


# ============================================================
# 后台管理 —— 内容管理（树洞审核 / 心理资源）
# ============================================================

@app.get("/api/admin/treehole")
def admin_treehole(status: str | None = None, admin: dict = Depends(require_admin)):
    return ok(db.list_treehole_admin(status=status))


class TreeholeReviewBody(BaseModel):
    status: str  # approved | rejected | flagged


@app.post("/api/admin/treehole/{hole_id}/review")
def admin_treehole_review(hole_id: int, body: TreeholeReviewBody,
                          admin: dict = Depends(require_admin)):
    if not db.set_treehole_status(hole_id, body.status, reviewer=admin.get("username")):
        return fail(400, "审核状态非法或树洞不存在")
    _log_operation(admin, "树洞审核", f"id={hole_id} -> {body.status}")
    return ok(msg="已审核")


@app.delete("/api/admin/treehole/{hole_id}")
def admin_treehole_delete(hole_id: int, admin: dict = Depends(require_admin)):
    db.delete_treehole(hole_id)
    _log_operation(admin, "删除树洞", f"id={hole_id}")
    return ok(msg="已删除")


class ResourceCreate(BaseModel):
    title: str
    res_type: str = "article"
    url: str | None = None
    content: str | None = None
    status: str = "published"


class ResourceUpdate(BaseModel):
    title: str | None = None
    res_type: str | None = None
    url: str | None = None
    content: str | None = None
    status: str | None = None


@app.get("/api/admin/resources")
def admin_resources(admin: dict = Depends(require_admin)):
    return ok(db.list_resources())


@app.post("/api/admin/resources")
def admin_resource_create(req: ResourceCreate, admin: dict = Depends(require_admin)):
    if not req.title or not req.title.strip():
        return fail(400, "标题不能为空")
    rid = db.add_resource(req.title, req.res_type, req.url, req.content, req.status)
    _log_operation(admin, "发布资源", req.title)
    return ok({"id": rid}, msg="已发布")


@app.put("/api/admin/resources/{res_id}")
def admin_resource_update(res_id: int, req: ResourceUpdate,
                          admin: dict = Depends(require_admin)):
    if not db.update_resource(res_id, title=req.title, res_type=req.res_type,
                              url=req.url, content=req.content, status=req.status):
        return fail(404, "资源不存在或未变更")
    _log_operation(admin, "更新资源", f"id={res_id}")
    return ok(msg="已更新")


@app.delete("/api/admin/resources/{res_id}")
def admin_resource_delete(res_id: int, admin: dict = Depends(require_admin)):
    db.delete_resource(res_id)
    _log_operation(admin, "删除资源", f"id={res_id}")
    return ok(msg="已删除")


# ============================================================
# 后台管理 —— 日志（登录日志 / 操作日志）
# ============================================================

@app.get("/api/admin/logs/login")
def admin_logs_login(limit: int = 100, admin: dict = Depends(require_admin)):
    return ok(db.list_login_logs(limit=max(1, min(limit, 500))))


@app.get("/api/admin/logs/operation")
def admin_logs_operation(limit: int = 100, admin: dict = Depends(require_admin)):
    return ok(db.list_operation_logs(limit=max(1, min(limit, 500))))


# ============================================================
# 后台管理 —— 安全配置（危机热线 / 风险关键词）
# ============================================================

@app.get("/api/admin/config")
def admin_config(admin: dict = Depends(require_admin)):
    from backend.requirements import AI_WATERMARK, CRISIS_HOTLINE
    hotline = db.get_config("crisis_hotline") or CRISIS_HOTLINE
    return ok({
        "crisis_hotline": hotline,
        "ai_watermark": AI_WATERMARK,
        "llm": {
            "enabled": llm_client.is_enabled(),
            "status_text": llm_client.status_text(),
        },
    })


class HotlineBody(BaseModel):
    hotline: str


@app.post("/api/admin/config/hotline")
def admin_config_hotline(body: HotlineBody, admin: dict = Depends(require_admin)):
    hotline = (body.hotline or "").strip()
    if not hotline:
        return fail(400, "热线不能为空")
    db.set_config("crisis_hotline", hotline)
    orchestrator.emergency_hotline = hotline  # 立即生效
    _log_operation(admin, "配置危机热线", hotline)
    return ok(msg="已更新")


@app.get("/api/admin/risk-keywords")
def admin_risk_keywords(admin: dict = Depends(require_admin)):
    return ok(db.list_all_risk_keywords())


class RiskKeywordBody(BaseModel):
    level: str
    keyword: str


@app.post("/api/admin/risk-keywords")
def admin_risk_keyword_add(body: RiskKeywordBody, admin: dict = Depends(require_admin)):
    kid, err = db.add_risk_keyword(body.level, body.keyword)
    if err:
        return fail(400, err)
    _log_operation(admin, "新增风险关键词", f"{body.level}: {body.keyword}")
    return ok({"id": kid}, msg="已新增")


class RiskKeywordToggle(BaseModel):
    enabled: bool


@app.put("/api/admin/risk-keywords/{kid}")
def admin_risk_keyword_toggle(kid: int, body: RiskKeywordToggle,
                              admin: dict = Depends(require_admin)):
    if not db.set_risk_keyword_enabled(kid, body.enabled):
        return fail(404, "关键词不存在")
    _log_operation(admin, "启用/停用风险关键词", f"id={kid} enabled={body.enabled}")
    return ok(msg="已更新")


@app.delete("/api/admin/risk-keywords/{kid}")
def admin_risk_keyword_delete(kid: int, admin: dict = Depends(require_admin)):
    if not db.delete_risk_keyword(kid):
        return fail(404, "关键词不存在")
    _log_operation(admin, "删除风险关键词", f"id={kid}")
    return ok(msg="已删除")


@app.post("/api/admin/risk-keywords/seed")
def admin_risk_keyword_seed(admin: dict = Depends(require_admin)):
    """将内置默认关键词同步进数据库（幂等），便于后台展示与编辑基线。"""
    from backend.risk import KEYWORD_MAP
    added = 0
    for level, words in KEYWORD_MAP.items():
        for w in words:
            kid, err = db.add_risk_keyword(level, w)
            if err is None:
                added += 1
    _log_operation(admin, "初始化风险关键词", f"新增 {added} 条")
    return ok({"added": added}, msg=f"已同步 {added} 条内置关键词")


# ============================================================
# 后台管理 —— ACPs 协作日志（最近一次协商的 AIP 报文）
# ============================================================

@app.get("/api/admin/collaboration/latest")
def admin_collaboration(session_id: str | None = None, admin: dict = Depends(require_admin)):
    if session_id is not None and session_id in _last_collaboration:
        data = _last_collaboration[session_id]
    elif _last_collaboration:
        data = list(_last_collaboration.values())[-1]
    else:
        data = []
    return ok({"session_id": session_id, "messages": data})


# ============================================================
# 前端 SPA 托管（dist/ 目录）
# ============================================================

FRONTEND_DIST = os.path.join(PROJECT_ROOT, "Mindlsle_fronted", "frontend", "dist")

if os.path.isdir(FRONTEND_DIST):
    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback(request, exc):
        if exc.status_code == 404 and request.headers.get("accept", "").startswith("text/html"):
            return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
        # 非 SPA 场景：按原状态码返回统一 JSON 错误，避免异常处理器再次抛出变成 500
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "data": None, "msg": str(exc.detail or "请求错误")},
        )

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
