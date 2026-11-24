"""
backend/risk.py
MindIsle 风险等级判断模块

按关键词规则将学生输入评估为四级风险：
    绿 (green)  — 低风险：情绪积极
    黄 (yellow) — 中风险：压力/负面情绪
    橙 (orange) — 较高风险：恐惧/受欺凌
    红 (red)    — 高风险：自杀/自伤意念
"""

from typing import Any, Dict, List


KEYWORD_MAP: Dict[str, List[str]] = {
    "green": [
        "开心", "高兴", "很好", "不错", "喜欢", "满意",
        "快乐", "幸福", "棒", "还行", "挺好", "没事",
        "哈哈", "嘻嘻", "谢谢", "感激",
    ],
    "yellow": [
        "压力", "难过", "焦虑", "烦恼", "担心", "害怕考试",
        "累", "心累", "郁闷", "烦躁", "不开心", "不太好",
        "紧张", "迷茫", "孤独", "失落", "沮丧", "忧愁",
        "撑不下去", "撑不住", "扛不住", "坚持不下去", "熬不住", "挺不住",
    ],
    "orange": [
        "欺凌", "欺负", "被欺负", "被打", "挨打", "讨厌", "恨",
        "恐惧", "害怕", "怕", "威胁", "勒索", "孤立", "排挤",
        "家庭暴力", "被骂", "人身攻击",
    ],
    "red": [
        "自杀", "不想活", "想死", "跳楼", "割腕", "结束生命",
        "活不下去", "了断", "去死", "自伤", "自残",
        "上吊", "跳江", "吞药", "安眠药",
        "轻生", "寻短见", "坠楼", "结束自己", "跳河",
    ],
}

LEVEL_DB_MAP: Dict[str, str] = {
    "green":  "low",
    "yellow": "medium",
    "orange": "high",
    "red":    "critical",
}

LEVEL_ORDER: List[str] = ["green", "yellow", "orange", "red"]


# ---------------------------------------------------------------------------
# 后台可配置的风险规则（安全配置模块共用）
#   默认不配置时，effective_keywords() 与内置 KEYWORD_MAP 完全等价，
#   因此既有行为/测试不受影响；管理员在后台增删关键词后，评估即时生效。
# ---------------------------------------------------------------------------

def effective_keywords() -> Dict[str, List[str]]:
    """内置规则 + 后台自定义关键词（去重合并）。

    数据库不可用 / 无表 / 无自定义行时，等价于内置 KEYWORD_MAP。
    """
    base: Dict[str, List[str]] = {lv: list(ws) for lv, ws in KEYWORD_MAP.items()}
    try:
        from backend import database as _db
        rows = _db.list_enabled_risk_keywords()
    except Exception:  # 数据库未就绪等，退回内置规则
        return base
    if rows:
        for level, keyword in rows:
            if level in base and keyword and keyword not in base[level]:
                base[level].append(keyword)
    return base


def reload_rules() -> None:
    """后台修改关键词后调用；读取逻辑每次即时从库获取，这里仅作显式语义占位。"""
    return None


def get_hotline(default: str = "400-161-9995") -> str:
    """读取后台配置的危机热线；未配置时返回默认值。"""
    try:
        from backend import database as _db
        return _db.get_config("crisis_hotline") or default
    except Exception:
        return default


def assess(text: str) -> Dict[str, Any]:
    """
    对一段学生输入进行风险评估。

    :param text: 学生输入文本
    :return: 评估结果
        {
            "level":         str,           # "green" | "yellow" | "orange" | "red"
            "level_db":      str,           # 对应数据库字段 "low" | "medium" | "high" | "critical"
            "score":         float,         # 0.0 ~ 1.0，越高越危险
            "matched":       List[str],     # 命中的关键词列表
            "matched_level": str,           # 命中的最高等级
        }
    """
    text = text or ""

    # 收集全部命中（含位置），用于“最长匹配优先 + 区间重叠去重”。
    # 修复：'害怕考试'（黄）中同时含 '害怕'/'怕'（橙）子串，若简单叠加会
    # 把考试焦虑误拆成橙色“害怕”；按“最长匹配优先”后短字串被长词区间覆盖，
    # 从而正确命中更贴切的 yellow。
    kws = effective_keywords()
    hits: List[Any] = []
    for level in LEVEL_ORDER:
        li = LEVEL_ORDER.index(level)
        for kw in kws[level]:
            pos = text.find(kw)
            if pos != -1:
                hits.append((li, kw, pos, pos + len(kw)))

    # 关键字长度降序：越长的越优先，落在已采纳长区间内的短字串则被覆盖丢弃。
    hits.sort(key=lambda h: (-len(h[1]), h[0]))
    adopted: List[Any] = []
    for li, kw, s, e in hits:
        overlapped = any(s < e2 and s2 < e for (_, _, s2, e2) in adopted)
        if not overlapped:
            adopted.append((li, kw, s, e))

    adopted.sort(key=lambda h: (h[0], h[1]))  # 按风险等级有序呈现
    all_matched: List[str] = [kw for (_, kw, _, _) in adopted]
    best_level: str = LEVEL_ORDER[max(h[0] for h in adopted)] if adopted else "green"

    score_map = {"green": 0.1, "yellow": 0.35, "orange": 0.7, "red": 1.0}

    return {
        "level":         best_level,
        "level_db":      LEVEL_DB_MAP[best_level],
        "score":         score_map[best_level],
        "matched":       all_matched,
        "matched_level": best_level,
    }


def is_critical(level: str) -> bool:
    return level == "red"


if __name__ == "__main__":
    tests = [
        "今天考试考了 100 分，好开心！",
        "最近压力好大，晚上经常睡不着，有点难过。",
        "我被同学欺负了，很害怕去学校。",
        "我真的不想活了，感觉活着没意思。",
        "今天没什么特别的，还行吧。",
    ]
    for t in tests:
        r = assess(t)
        print(f"[{r['level']:6s}] score={r['score']:.2f}  hits={r['matched']}")
        print(f"          输入: {t}")
        print()