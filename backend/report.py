"""
backend/report.py
MindIsle PDF 心理报告生成

三种报告类型（对应数据库 report.report_type）：
    counseling - 学生个体心理成长报告
    weekly     - 班级心理氛围报告
    warning    - 危机事件处置报告
"""

import os
import re
from datetime import datetime
from typing import Any, Dict, List

from fpdf import FPDF

FONT_REGULAR = r"C:\Windows\Fonts\simhei.ttf"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


class ChinesePDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_font("CN", "", FONT_REGULAR)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("CN", size=8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, "MindIsle 心屿 · 心理健康报告", align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("CN", size=8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"第 {self.page_no()} 页", align="C")


def _safe_filename(name: str) -> str:
    bad = '<>:"/\\|?* '
    for ch in bad:
        name = name.replace(ch, "_")
    return name


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _clean(text: Any) -> str:
    t = str(text or "")
    t = t.replace("\u3000", " ").replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    return t


def _mx(pdf: FPDF, w, h, text, **kw):
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(w, h, text, **kw)
    pdf.set_x(pdf.l_margin)


def _build_pdf(title: str, sections: List[Dict[str, Any]]) -> str:
    pdf = ChinesePDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()

    pdf.set_font("CN", size=22)
    pdf.set_text_color(41, 65, 122)
    _mx(pdf, 0, 14, _clean(title), align="C")
    pdf.ln(4)

    pdf.set_font("CN", size=10)
    pdf.set_text_color(120, 120, 120)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _mx(pdf, 0, 8, f"生成时间：{now}", align="C")
    pdf.ln(4)

    pdf.set_draw_color(41, 65, 122)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(8)

    for sec in sections:
        heading = _clean(sec.get("heading", ""))
        body = _clean(sec.get("body", ""))
        table = sec.get("table")

        pdf.set_font("CN", size=14)
        pdf.set_text_color(41, 65, 122)
        _mx(pdf, 0, 10, heading)
        pdf.ln(2)

        pdf.set_font("CN", size=10)
        pdf.set_text_color(40, 40, 40)
        body_lines = body.split("\n") if body else []
        for line in body_lines:
            if line.strip():
                _mx(pdf, 0, 6, line)
            else:
                pdf.ln(3)

        if table:
            pdf.ln(2)
            col_w = table.get("col_widths", None)
            headers = [_clean(h) for h in table.get("headers", [])]
            rows = [[_clean(c) for c in row] for row in table.get("rows", [])]
            full_w = pdf.w - pdf.l_margin - pdf.r_margin

            if headers:
                n_col = len(headers)
                pdf.set_font("CN", size=9)
                pdf.set_fill_color(41, 65, 122)
                pdf.set_text_color(255, 255, 255)
                x0 = pdf.l_margin
                for i, h in enumerate(headers):
                    w = col_w[i] if col_w else full_w / n_col
                    pdf.set_x(x0 + sum((col_w[j] if col_w else full_w / n_col) for j in range(i)))
                    pdf.multi_cell(w, 8, h, border=1, fill=True, align="C")
                pdf.set_x(pdf.l_margin)

            pdf.set_font("CN", size=9)
            pdf.set_text_color(40, 40, 40)
            fill = False
            for row in rows:
                n_col = len(row) or 1
                row_h = 7
                if fill:
                    pdf.set_fill_color(235, 240, 250)
                x0 = pdf.l_margin
                y0 = pdf.get_y()
                cell_widths = []
                for i, cell in enumerate(row):
                    w = col_w[i] if col_w else full_w / n_col
                    cell_widths.append(w)
                for i, ct in enumerate(row):
                    pdf.set_x(x0 + sum(cell_widths[:i]))
                    pdf.set_y(y0)
                    pdf.multi_cell(cell_widths[i], row_h, str(ct)[:60], border=1, fill=fill, align="C")
                pdf.set_y(y0 + row_h)
                pdf.set_x(pdf.l_margin)
                fill = not fill
            pdf.ln(3)

        pdf.ln(4)

    _ensure_output_dir()
    filename = _safe_filename(title) + f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)
    pdf.output(filepath)
    return filepath


# ============================================================
# 1. 学生个体心理成长报告
# ============================================================
def generate_student_report(
    student: Dict[str, Any],
    sessions: List[Dict[str, Any]],
    messages: List[Dict[str, Any]],
    risk_history: List[Dict[str, Any]],
) -> str:
    """
    学生个体心理成长报告。

    :param student: {id, name, gender, age, school, grade}
    :param sessions: 该学生的全部会话
    :param messages: 该学生的全部聊天消息
    :param risk_history: 该学生的全部风险评估记录
    :return: PDF 文件路径
    """
    name = student.get("name", "未知")
    title = f"学生个体心理成长报告 — {name}"

    level_counts: Dict[str, int] = {}
    latest_level = "green"
    latest_score = 0.0
    if risk_history:
        for r in risk_history:
            lv = r.get("risk_level", "low")
            level_counts[lv] = level_counts.get(lv, 0) + 1
        latest = risk_history[0]
        latest_level = latest.get("risk_level", "low")
        latest_score = latest.get("score", 0.0) or 0.0

    level_cn = {"low": "绿（低风险）", "medium": "黄（中风险）", "high": "橙（较高风险）", "critical": "红（高风险）"}

    total_user_msg = sum(1 for m in messages if m["role"] == "user")
    total_assistant_msg = sum(1 for m in messages if m["role"] == "assistant")

    summary = (
        f"姓名：{name}\n"
        f"性别：{student.get('gender') or '-'}    年龄：{student.get('age') or '-'}\n"
        f"学校：{student.get('school') or '-'}    年级：{student.get('grade') or '-'}\n"
        f"建档时间：{student.get('created_at', '-')}\n\n"
        f"数据统计：\n"
        f"  累计咨询会话：{len(sessions)} 次\n"
        f"  累计学生发言：{total_user_msg} 条\n"
        f"  AI 陪伴回复：{total_assistant_msg} 条\n\n"
        f"最新风险评估：{level_cn.get(latest_level, latest_level)}（score={latest_score}）\n"
        f"风险分布：" + "、".join(f"{k}={v}" for k, v in level_counts.items())
    )

    chat_preview_lines = []
    for m in messages[-20:]:
        role = "学生" if m["role"] == "user" else "AI陪伴" if m["role"] == "assistant" else "系统"
        chat_preview_lines.append(f"[{role}] {m['content']}")
    chat_preview = "\n".join(chat_preview_lines) if chat_preview_lines else "暂无聊天记录"

    if latest_level in ("critical", "high"):
        suggestion = (
            "该学生近期存在较高风险情绪，建议心理老师尽快安排一对一面谈；"
            "同时通知班主任及家长共同关注，必要时联系专业心理干预机构。"
        )
    elif latest_level == "medium":
        suggestion = (
            "该学生存在一定情绪压力，建议通过团体辅导或日常关心帮助其释放压力，"
            "持续跟踪后续咨询情况。"
        )
    else:
        suggestion = "该学生整体情绪状态良好，建议继续保持关注，定期开展心理健康普查。"

    sections = [
        {"heading": "一、基本信息", "body": summary},
        {"heading": "二、近期聊天记录（最近 20 条）", "body": chat_preview},
        {
            "heading": "三、风险评估历史",
            "body": "历次会话的风险评估结果如下：",
            "table": {
                "headers": ["时间", "风险等级", "分数", "命中指标"],
                "rows": [
                    [
                        r.get("assessed_at", "")[:16],
                        level_cn.get(r.get("risk_level", ""), r.get("risk_level", "")),
                        f"{r.get('score', 0):.2f}",
                        (r.get("indicators") or "")[:30],
                    ]
                    for r in risk_history[:10]
                ] or [],
            },
        },
        {"heading": "四、辅导建议", "body": suggestion},
    ]

    return _build_pdf(title, sections)


# ============================================================
# 2. 班级心理氛围报告
# ============================================================
def generate_class_report(
    class_name: str,
    students: List[Dict[str, Any]],
    risk_records: List[Dict[str, Any]],
) -> str:
    """
    班级心理氛围报告（周报）。

    :param class_name: 班级名称，例如 "高一(3)班"
    :param students: 该班级学生列表
    :param risk_records: 该班级所有学生的风险评估记录
    :return: PDF 文件路径
    """
    title = f"班级心理氛围报告 — {class_name}"

    total = len(students)
    level_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for r in risk_records:
        lv = r.get("risk_level", "low")
        if lv in level_counts:
            level_counts[lv] += 1

    distribution_rows = [
        ["绿（低风险）", level_counts["low"], f"{(level_counts['low']/max(len(risk_records),1))*100:.1f}%"],
        ["黄（中风险）", level_counts["medium"], f"{(level_counts['medium']/max(len(risk_records),1))*100:.1f}%"],
        ["橙（较高风险）", level_counts["high"], f"{(level_counts['high']/max(len(risk_records),1))*100:.1f}%"],
        ["红（高风险）", level_counts["critical"], f"{(level_counts['critical']/max(len(risk_records),1))*100:.1f}%"],
    ]

    critical_students = []
    for s in students:
        sid = s["id"]
        for r in risk_records:
            if r.get("session_id") and r.get("risk_level") in ("high", "critical"):
                critical_students.append((s.get("name", f"#{sid}"), r.get("risk_level"), r.get("indicators", "")))
                break

    overview = (
        f"班级：{class_name}\n"
        f"学生总数：{total} 人\n"
        f"累计风险评估次数：{len(risk_records)}\n\n"
        f"整体结论："
    )

    if level_counts["critical"] > 0:
        overview += "本班出现红色高风险预警，需立即启动危机干预流程。"
    elif level_counts["high"] > 0:
        overview += "本班存在橙色较高风险学生，建议安排重点关注与心理约谈。"
    elif level_counts["medium"] / max(len(risk_records), 1) > 0.3:
        overview += "本班整体情绪偏焦虑，建议开展团体减压活动。"
    else:
        overview += "本班整体心理状态良好。"

    sections = [
        {"heading": "一、班级概况", "body": overview},
        {
            "heading": "二、风险等级分布",
            "body": "依据 MindIsle 系统采集的咨询数据统计：",
            "table": {
                "headers": ["风险等级", "评估次数", "占比"],
                "rows": distribution_rows,
            },
        },
        {
            "heading": "三、重点关注学生",
            "body": "以下学生近期评估为较高或高风险，建议班主任及心理老师重点关注：",
            "table": {
                "headers": ["姓名", "风险等级", "关键指标"],
                "rows": critical_students or [("暂无", "-", "-")],
            },
        },
        {
            "heading": "四、本周建议活动",
            "body": (
                "1. 团体心理辅导：开展一次班级减压活动，如正念呼吸、情绪匿名涂鸦。\n"
                "2. 个体约谈：对黄色及以上风险的学生逐一进行一对一面谈。\n"
                "3. 家校沟通：向家长推送心理健康小贴士，争取家庭端支持。"
            ),
        },
    ]

    return _build_pdf(title, sections)


# ============================================================
# 3. 危机事件处置报告
# ============================================================
def generate_crisis_report(
    student: Dict[str, Any],
    triggering_message: Dict[str, Any],
    risk_record: Dict[str, Any],
    session_messages: List[Dict[str, Any]],
) -> str:
    """
    危机事件处置报告。

    :param student: 触发危机的学生信息
    :param triggering_message: 触发 veto 的那条用户消息
    :param risk_record: 对应的风险评估记录
    :param session_messages: 本次会话全部消息
    :return: PDF 文件路径
    """
    name = student.get("name", "未知")
    title = f"危机事件处置报告 — {name}"

    incident = (
        f"学生姓名：{name}\n"
        f"性别：{student.get('gender') or '-'}    年龄：{student.get('age') or '-'}\n"
        f"学校/年级：{student.get('school') or '-'} / {student.get('grade') or '-'}\n\n"
        f"触发时间：{triggering_message.get('created_at', '-')}\n"
        f"触发类型：系统安全评估 Agent 一票否决（veto）\n"
        f"风险等级：红（critical）\n"
        f"命中指标：{risk_record.get('indicators', '-')}\n"
        f"风险分数：{risk_record.get('score', 1.0)}\n\n"
        f"触发内容：\n  {triggering_message.get('content', '')}"
    )

    transcript_lines = []
    for m in session_messages:
        role = "学生" if m["role"] == "user" else "AI"
        transcript_lines.append(f"[{role}] {m['content']}")
    transcript = "\n".join(transcript_lines) if transcript_lines else "无"

    action_plan = (
        "应急处置流程（需 24 小时内完成）：\n\n"
        "1. 【立即】通知学校心理干预小组组长，组建临时干预小组；\n"
        "2. 【1小时内】联系班主任老师确认学生当前安全状态（是否在校、是否有人陪伴）；\n"
        "3. 【2小时内】联系家长/监护人，告知情况并建议陪同；\n"
        "4. 【当日】心理老师与学生进行一次一对一深入面谈；\n"
        "5. 【48小时内】评估是否需要转介至专业精神卫生机构；\n"
        "6. 【一周内】持续跟踪回访，记录处置进展；\n\n"
        "紧急联络热线：\n"
        "  · 全国 24 小时心理援助热线：400-161-9995\n"
        "  · 北京心理危机研究与干预中心：010-82951332"
    )

    sections = [
        {"heading": "一、事件基本信息", "body": incident},
        {"heading": "二、触发时完整对话记录", "body": transcript},
        {"heading": "三、风险评估详情", "body": f"score={risk_record.get('score', 1.0)}\nindicators={risk_record.get('indicators', '')}"},
        {"heading": "四、处置行动计划", "body": action_plan},
        {
            "heading": "五、处置签字栏",
            "body": (
                "心理老师签字：________________    日期：_______________\n"
                "班主任签字：____________________    日期：_______________\n"
                "家长签字：______________________    日期：_______________"
            ),
        },
    ]

    return _build_pdf(title, sections)