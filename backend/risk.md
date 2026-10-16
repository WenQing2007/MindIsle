✅ 第6步：风险判断 — 完成
新建了什么
backend/risk.py — 按你给的四级关键词规则实现：

等级	对外返回	存数据库	score	关键词示例
绿	green	low	0.1	开心、很好、还行
黄	yellow	medium	0.35	压力大、难过、焦虑
橙	orange	high	0.7	欺凌、被欺负、害怕
红	red	critical	1.0	自杀、不想活、跳楼
核心函数就一个：risk.assess(text)，返回等级、分数、命中的关键词。

改了 /chat 接口（backend/app.py）
之前：只有高危 veto 才写一条风险记录 现在：每一条用户消息都会过 risk.assess()，落一条 risk_assessment，响应里也带四级等级

text



POST /chat  "我最近压力好大"
       ↓
risk.assess()  →  level=yellow, score=0.35, matched=['压力']
       ↓
orchestrator.process_dialogue()  →  AI 共情回复
       ↓
db.add_risk_assessment()  →  level_db="medium", indicators="压力"
       ↓
返回 { risk_level:"yellow", risk_score:0.35, risk_matched:["压力"] }
验证结果
text



[OK] 期望=绿  实际=green  score=0.1  hits=['开心']
[OK] 期望=黄  实际=yellow score=0.35 hits=['压力', '难过']
[OK] 期望=橙  实际=orange score=0.7  hits=['欺负', '害怕']
[OK] 期望=红  实际=red    score=1.0  hits=['不想活']
数据库里也正确存成了 low / medium / high / critical（和 risk_assessment 表的 CHECK 约束一致）。后面想调灵敏度，直接在 risk.py 的 KEYWORD_MAP 里加/删关键词就行。

2 个文件已更改
