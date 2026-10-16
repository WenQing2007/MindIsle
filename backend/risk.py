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
    ],
    "orange": [
        "欺凌", "欺负", "被欺负", "被打", "挨打", "讨厌", "恨",
        "恐惧", "害怕", "怕", "威胁", "勒索", "孤立", "排挤",
        "家庭暴力", "被骂", "人身攻击",
    ],
    "red": [
        "自杀", "不想活", "想死", "跳楼", "割腕", "结束生命",
        "活不下去", "了断", "去死", "自伤", "自残",
    ],
}

LEVEL_DB_MAP: Dict[str, str] = {
    "green":  "low",
    "yellow": "medium",
    "orange": "high",
    "red":    "critical",
}

LEVEL_ORDER: List[str] = ["green", "yellow", "orange", "red"]


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

    best_level = "green"
    best_index = 0
    all_matched: List[str] = []

    for level in LEVEL_ORDER:
        keywords = KEYWORD_MAP[level]
        hits = [kw for kw in keywords if kw in text]
        if hits:
            all_matched.extend(hits)
            idx = LEVEL_ORDER.index(level)
            if idx > best_index:
                best_index = idx
                best_level = level

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