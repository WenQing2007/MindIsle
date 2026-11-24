"""
backend/emotion.py
MindIsle（心屿）文本情绪识别 —— 基于轻量关键词 + 面向 6-18 岁学生的日常表达。

需求 2.1「能区分开心、难过、生气、焦虑等主要情绪」、2.4.1「情绪识别应基本准确」。
采用确定性规则实现（无网络、可离线、可测试），后续可替换为模型识别而不改对外接口。

对外接口：
    detect(text) -> {
        "emotion":   str,   # happy | sad | angry | anxious | fearful | neutral
        "label_cn":  str,   # 中文情绪名（开心/难过/生气/焦虑/害怕/平稳）
        "matched":   list,  # 命中的情绪词
    }
"""
from __future__ import annotations

from typing import Any, Dict, List

# 情绪 → 触发词（按优先级：同名命中优先取靠前类别；命中多个取第一个出现的类别）
EMOTION_WORDS: Dict[str, List[str]] = {
    "happy": [
        "开心", "高兴", "快乐", "幸福", "棒", "很好", "不错", "满意",
        "哈哈", "嘻嘻", "太好啦", "太好了", "耶", "庆祝", "激动", "兴奋",
        "喜欢", "爱了", "爽", "给力", "顺利", "考得不错",
    ],
    "sad": [
        "难过", "伤心", "悲痛", "沮丧", "失落", "委屈", "想哭", "哭",
        "心碎", "郁闷", "不开心", "低落", "悲伤", "流泪",
    ],
    "angry": [
        "生气", "愤怒", "气死", "恼火", "气人", "发火", "憋屈", "恨",
        "讨厌", "烦死了", "气炸",
    ],
    "anxious": [
        "紧张", "焦虑", "担心", "害怕考试", "慌", "不安", "心慌",
        "烦躁", "压力", "失眠", "睡不着", "惶恐",
    ],
    "fearful": [
        "害怕", "恐惧", "怕",
    ],
    "neutral": [
        "还行", "挺好", "没事", "一般", "就这样", "平平",
    ],
}

EMOTION_LABEL_CN: Dict[str, str] = {
    "happy": "开心",
    "sad": "难过",
    "angry": "生气",
    "anxious": "焦虑",
    "fearful": "害怕",
    "neutral": "平稳",
}


def detect(text: str) -> Dict[str, Any]:
    """对一段文本做轻量情绪识别。

    :param text: 学生输入文本
    :return: {"emotion", "label_cn", "matched"}
    """
    text = text or ""
    # 收集所有命中（含各自优先级序号），按出现位置在前、类别顺序在后的方式排序，
    # 保证“既贴近学生先说出的情绪，又与其他类别一致时取定义顺序更靠前的类”。
    hits: List[tuple] = []
    for i, (emotion, words) in enumerate(EMOTION_WORDS.items()):
        for w in words:
            pos = text.find(w)
            if pos != -1:
                hits.append((pos, i, emotion, w))

    if not hits:
        return {"emotion": "neutral", "label_cn": "平稳", "matched": []}

    # 位置优先；位置相同则类别先后决
    hits.sort(key=lambda h: (h[0], h[1]))
    emotion = hits[0][2]
    matched = [w for (_, _, _, w) in hits]
    return {
        "emotion": emotion,
        "label_cn": EMOTION_LABEL_CN.get(emotion, emotion),
        "matched": matched,
    }


if __name__ == "__main__":
    samples = [
        "今天考试考了100分，太开心了！",
        "最近压力好大，晚上睡不着，有点难过。",
        "气死我了，他居然那样对我！",
        "我有点慌，害怕考不好。",
        "还行吧，没什么特别的。",
    ]
    for s in samples:
        r = detect(s)
        print(f"[{r['label_cn']:4s}] {s}  命中={r['matched']}")
