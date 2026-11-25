"""
backend/report_agent.py
MindIsle「报告生成智能体」与「合规校验引擎」

对应需求《2.1 功能5 —— 报告生成》:
  - 报告由"报告生成智能体"生成，并附带大模型生成的个性化分析；
  - 输出需通过"合规校验"（AI 透明性 / 免责声明 / 无诊断结论 / 危机处置提示）。

设计：
  1. report_agent_generate(student_stats) -> text
       —— 依据学生风险统计，由大模型生成一段"综合分析与辅导建议"；
          未配置 Key 或调用失败时回退到内置规则模板（保证离线可用）。
  2. compliance_check(payload) -> dict
       —— 对一份报告进行合规体检，返回 { passed, checks: [{code, ok, message}] }。
"""
from __future__ import annotations

from typing import Any, Dict, List

from ai_agents import llm as llm_client
from backend.requirements import AI_WATERMARK

# ============================================================
# 合规校验规则定义
# ============================================================
_COMPLIANCE_RULES: List[Dict[str, Any]] = [
    {
        "code": "WATERMARK",
        "desc": "报告应包含 AI 生成/仅供参考/不构成诊断的透明性标注",
        "keywords": ["AI", "仅供参考", "不构成诊断"],
    },
    {
        "code": "HOTLINE",
        "desc": "危机相关报告应附带 24h 心理援助热线",
        "keywords": ["400-161-9995", "心理援助热线"],
    },
    {
        "code": "NO_DIAGNOSIS",
        "desc": "不得出现明确的医学/精神疾病诊断性结论",
        "keywords": ["确诊", "患有抑郁症", "确诊为", "诊断结论：", "抑郁症患者"],
        "forbid": True,  # 命中表示不通过
    },
    {
        "code": "STRUCTURE",
        "desc": "报告结构完整（含基本信息 / 风险 / 建议）",
        "keywords": ["基本信息", "风险", "建议"],
    },
]


class _ComplianceResult:
    def __init__(self) -> None:
        self.checks: List[Dict[str, Any]] = []
        self.passed: bool = True


def _verify_block(block_text: str) -> _ComplianceResult:
    result = _ComplianceResult()
    text = block_text or ""
    for rule in _COMPLIANCE_RULES:
        code = rule["code"]
        desc = rule.get("desc", "")
        forbid = rule.get("forbid", False)
        hit = any(kw.lower() in text.lower() for kw in rule.get("keywords", []))
        ok = (not hit) if forbid else hit
        result.checks.append(
            {"code": code, "desc": desc, "ok": bool(ok), "hit": hit}
        )
        if not ok:
            result.passed = False
    return result


def compliance_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    报告合规体检入口。

    :param payload: 报告关键数据，支持：
        - text:         报告全文（用于关键词命中检测）
        - report_type:  counseling / weekly / warning
        - has_crisis:   是否危机报告（危机报告必须命中热线）
    :return: { "passed": bool, "checks": [...], "summary": str }
    """
    is_crisis = bool(payload.get("has_crisis") or payload.get("report_type") == "warning")
    text = payload.get("text") or ""

    required_checks = ["WATERMARK", "NO_DIAGNOSIS", "STRUCTURE"]
    if is_crisis:
        required_checks.append("HOTLINE")

    res = _verify_block(text)
    relevant = [c for c in res.checks if c["code"] in required_checks]
    passed = all(c["ok"] for c in relevant)
    summary = "报告通过合规校验" if passed else "报告存在合规告警，请人工复核"

    return {
        "passed": bool(passed),
        "checks": relevant,
        "summary": summary,
        "watermark": AI_WATERMARK,
    }


def _score_to_level(level: str, score: float) -> str:
    m = {
        "low": "整体平稳，偶有一般情绪波动，属正常范围",
        "medium": "存在一定压力或焦虑倾向，建议保持关注并适当疏导",
        "high": "情绪压力较明显，建议心理老师安排一对一约谈",
        "critical": "存在较高风险信号，需立即启动危机干预与家校协同",
    }
    return m.get(level, m["low"])


def report_agent_generate(student_stats: Dict[str, Any]) -> str:
    """
    报告生成智能体：生成一段"综合分析与辅导建议"。

    :param student_stats: 含 name / latest_level / latest_score / session_count /
                          user_msg_count / risk_distribution
    :return: 分析文本（大模型生成或规则兜底）
    """
    name = student_stats.get("name", "该学生")
    latest_level = student_stats.get("latest_level", "low")
    score = float(student_stats.get("latest_score") or 0.0)
    dist = student_stats.get("risk_distribution", {}) or {}
    sessions = student_stats.get("session_count", 0)
    user_msgs = student_stats.get("user_msg_count", 0)

    level_txt = _score_to_level(latest_level, score)
    dist_txt = "、".join(f"{k}={v}" for k, v in dist.items()) if dist else "暂无"

    # ---- 1) 优先尝试大模型生成（个性化）----
    system = (
        "你是一位专业、温和且克制的学校心理教师，负责为一份学生心理陪伴报告撰写"
        "「综合分析与辅导建议」。要求：不得下任何医学/精神疾病诊断结论，语气审慎"
        "鼓励，内容基于给出的统计数据，结尾提醒如遇紧急情况拨打心理援助热线。"
        "用中文，200 字以内。"
    )
    user_prompt = (
        f"学生：{name}；最新风险等级：{latest_level}（score={score}）；"
        f"风险分布：{dist_txt}；累计会话：{sessions} 次，学生发言 {user_msgs} 条。"
        "请据此撰写综合分析与辅导建议。"
    )
    ai_text = llm_client.safe_chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user_prompt}],
        fallback="",
        max_tokens=320,
        temperature=0.6,
    )
    if ai_text and len(ai_text.strip()) > 10:
        return (
            f"综合分析（AI 生成）：\n{ai_text.strip()}\n\n"
            "合规说明：本内容由大模型辅助生成，仅供参考，不构成诊断结论；"
            "如遇紧急情况请拨打 400-161-9995。"
        )

    # ---- 2) 规则兜底（离线 / 未配置 Key）----
    if latest_level in ("critical", "high"):
        suggestion = (
            "依据近期咨询数据，该学生风险信号较明显，建议心理老师 24 小时内安排一对一"
            "面谈，同时通知班主任与家长共同关注，必要时联系专业心理干预机构。"
        )
    elif latest_level == "medium":
        suggestion = (
            "该学生存在一定情绪压力，建议通过日常关心、团体辅导帮助其释放压力，"
            "并持续跟踪后续咨询情况。"
        )
    else:
        suggestion = "该学生整体情绪状态良好，建议继续保持日常关注，定期开展心理健康普查。"
    return (
        f"综合分析（智能体规则生成）：\n"
        f"  最新风险：{level_txt}（score={score}）。\n"
        f"  数据概览：累计会话 {sessions} 次、学生发言 {user_msgs} 条，风险分布 {dist_txt}。\n"
        f"  辅导建议：{suggestion}\n\n"
        "合规说明：本内容由系统自动生成，仅供参考，不构成诊断结论；"
        "如遇紧急情况请拨打 400-161-9995。"
    )


def build_compliance_block(report_type: str, text: str) -> Dict[str, Any]:
    """生成报告章节所需的合规数据：校验结果 + 水印 + AI 免责声明。"""
    result = compliance_check({"text": text, "report_type": report_type,
                               "has_crisis": report_type == "warning"})
    return {
        "check": result,
        "watermark": AI_WATERMARK,
        "disclaimer": (
            "【AI 生成内容，仅供参考，不构成诊断结论。】本报告由 MindIsle 多智能体系统"
            "辅助生成，其中「综合分析与辅导建议」部分可能由大模型生成；不替代专业心理"
            "诊断评估。如遇紧急情况请拨打全国 24 小时心理援助热线 400-161-9995。"
        ),
    }
