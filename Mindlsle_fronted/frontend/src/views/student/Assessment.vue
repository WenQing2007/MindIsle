<template>
  <div class="assessment-page">
    <el-page-header content="📝 测评小站" @back="$router.push('/student/home')"></el-page-header>

    <div class="assess-intro">
      <div class="intro-text">
        <h2>了解自己的心理状态</h2>
        <p>选择一个量表，根据最近两周的实际情况作答。结果仅供参考，不构成诊断。</p>
      </div>
    </div>

    <template v-if="!currentScale">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="12" v-for="scale in scales" :key="scale.id">
          <el-card shadow="hover" class="scale-card" @click="openScale(scale.id)">
            <div class="scale-emoji">{{ scale.emoji }}</div>
            <div class="scale-title">{{ scale.title }}</div>
            <div class="scale-desc">{{ scale.desc }}</div>
            <div class="scale-meta">
              <el-tag size="small">{{ scale.questions.length }} 题</el-tag>
              <el-tag size="small" type="success">约 {{ scale.questions.length * 5 }} 秒</el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <div class="history-section" v-if="historyList.length > 0">
        <div class="section-title">📋 我的测评记录</div>
        <el-card class="history-card" shadow="never">
          <div class="history-item" v-for="(h, i) in historyList" :key="i">
            <div class="history-info">
              <div class="history-scale">{{ h.scale_name }}</div>
              <div class="history-time">{{ h.time }}</div>
            </div>
            <div class="history-result" :class="'result-' + h.level">
              {{ h.score }} 分 · {{ h.level_cn }}
            </div>
          </div>
        </el-card>
      </div>
    </template>

    <template v-else>
      <el-card shadow="never" class="quiz-card">
        <div class="quiz-header">
          <el-button link type="primary" @click="currentScale = null">← 返回量表列表</el-button>
          <div class="quiz-progress">
            第 {{ currentIndex + 1 }} / {{ currentScale.questions.length }} 题
            <div class="mini-bar">
              <div class="mini-fill" :style="{ width: ((currentIndex + 1) / currentScale.questions.length * 100) + '%' }"></div>
            </div>
          </div>
        </div>

        <div class="question-area" v-if="currentIndex < currentScale.questions.length">
          <div class="question-num">Q{{ currentIndex + 1 }}</div>
          <div class="question-text">{{ currentScale.questions[currentIndex].text }}</div>
          <div class="question-tip">在过去两周内，这种情况发生的频率是？</div>
          <el-radio-group v-model="answers[currentIndex]" class="option-group">
            <el-radio
              v-for="opt in currentScale.options"
              :key="opt.value"
              :value="opt.value"
              class="option-item"
            >
              <span class="opt-label">{{ opt.label }}</span>
              <span class="opt-desc">{{ opt.desc }}</span>
            </el-radio>
          </el-radio-group>
        </div>

        <div class="result-area" v-else>
          <div class="result-emoji">{{ resultEmoji }}</div>
          <h3 class="result-title">{{ currentScale.title }} · 测评结果</h3>
          <div class="result-score" :class="'score-' + resultLevel">
            <span class="score-num">{{ totalScore }}</span>
            <span class="score-unit">分</span>
          </div>
          <div class="result-level" :class="'level-' + resultLevel">
            风险等级：{{ resultLevelCn }}
          </div>
          <div class="result-desc">{{ currentScale.resultDesc[resultLevel] }}</div>
          <div class="result-advice">
            <div class="advice-title">💡 建议</div>
            <ul>
              <li v-for="(a, i) in currentScale.advice[resultLevel]" :key="i">{{ a }}</li>
            </ul>
          </div>

          <div class="result-btns">
            <el-button @click="currentScale = null">再测一次</el-button>
            <el-button type="primary" @click="saveResult">💾 保存结果</el-button>
          </div>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { saveAssessmentRecord, getAssessmentRecords } from '@/api/student'

const studentId = () => parseInt(localStorage.getItem('student_id') || '1')

const scales = [
  {
    id: 'phq9',
    emoji: '💙',
    title: 'PHQ-9 抑郁筛查',
    desc: '9 个问题，帮助你了解最近两周的情绪状态',
    questions: [
      { text: '做事时提不起劲或没有兴趣' },
      { text: '感到心情低落、沮丧或绝望' },
      { text: '入睡困难、睡不安稳或睡眠过多' },
      { text: '感觉疲倦或没有活力' },
      { text: '食欲不振或吃太多' },
      { text: '觉得自己很糟或觉得自己是失败者' },
      { text: '注意力难以集中，例如看报、看电视都无法专心' },
      { text: '动作或说话迟缓，或变得容易烦躁' },
      { text: '有不如死掉或用某种方式伤害自己的念头' }
    ],
    options: [
      { value: 0, label: '完全不会', desc: '0 分' },
      { value: 1, label: '好几天', desc: '1 分' },
      { value: 2, label: '一半以上天数', desc: '2 分' },
      { value: 3, label: '几乎每天', desc: '3 分' }
    ],
    resultDesc: {
      none: '你的情绪状态看起来不错，继续保持良好的生活节奏哦～',
      mild: '有一些轻度的情绪波动，这是正常的。注意自我调节就好。',
      moderate: '有一定的情绪困扰，建议多关注自己，必要时可以找人聊聊。',
      severe: '情绪困扰比较明显，强烈建议联系专业心理咨询师或医生。'
    },
    advice: {
      none: ['保持规律作息', '多运动、多社交', '继续保持积极心态'],
      mild: ['每天留出 15 分钟做自己喜欢的事', '写日记记录情绪变化', '尝试放松训练'],
      moderate: ['主动和信任的人分享感受', '考虑做一次 AI 心理陪伴', '记录情绪变化趋势'],
      severe: ['请尽快联系学校心理老师或医生', '拨打心理援助热线 400-161-9995', '不要独处太久，找人陪伴']
    },
    levelMap: [
      { max: 4,  level: 'none',    cn: '无明显' },
      { max: 9,  level: 'mild',    cn: '轻度' },
      { max: 14, level: 'moderate', cn: '中度' },
      { max: 27, level: 'severe',  cn: '重度' }
    ]
  },
  {
    id: 'gad7',
    emoji: '💜',
    title: 'GAD-7 焦虑筛查',
    desc: '7 个问题，帮助你了解最近两周的焦虑程度',
    questions: [
      { text: '感到紧张、焦虑或烦躁' },
      { text: '不能停止或控制担忧' },
      { text: '对各种事情过度担忧' },
      { text: '难以放松' },
      { text: '坐立不安' },
      { text: '容易烦恼或易怒' },
      { text: '害怕有可怕的事情会发生' }
    ],
    options: [
      { value: 0, label: '完全不会', desc: '0 分' },
      { value: 1, label: '好几天', desc: '1 分' },
      { value: 2, label: '一半以上天数', desc: '2 分' },
      { value: 3, label: '几乎每天', desc: '3 分' }
    ],
    resultDesc: {
      none: '你的焦虑水平正常，继续保持就好～',
      mild: '有一些轻度焦虑，可能是考试或压力引起的，很常见。',
      moderate: '中等程度的焦虑，建议试试呼吸花园放松训练。',
      severe: '焦虑水平较高，建议寻求专业帮助。'
    },
    advice: {
      none: ['保持规律作息', '适度运动', '培养放松爱好'],
      mild: ['试试呼吸花园 5-5 放松练习', '减少咖啡因摄入', '规律运动 20 分钟'],
      moderate: ['每天 2 次呼吸训练', '写下担忧清单', '与信任的人谈谈'],
      severe: ['尽快联系专业心理咨询', '拨打 400-161-9995', '避免过度刺激环境']
    },
    levelMap: [
      { max: 4,  level: 'none',    cn: '无明显' },
      { max: 9,  level: 'mild',    cn: '轻度' },
      { max: 14, level: 'moderate', cn: '中度' },
      { max: 21, level: 'severe',  cn: '重度' }
    ]
  }
]

const currentScale = ref(null)
const currentIndex = ref(0)
const answers = ref([])
const historyList = ref([])

const openScale = (id) => {
  const s = scales.find(x => x.id === id)
  if (s) {
    currentScale.value = s
    currentIndex.value = 0
    answers.value = new Array(s.questions.length).fill(null)
  }
}

const totalScore = computed(() => {
  return answers.value.reduce((a, b) => a + (b || 0), 0)
})

const resultLevel = computed(() => {
  if (!currentScale.value) return 'none'
  for (const lm of currentScale.value.levelMap) {
    if (totalScore.value <= lm.max) return lm.level
  }
  return 'severe'
})

const resultLevelCn = computed(() => {
  if (!currentScale.value) return ''
  const item = currentScale.value.levelMap.find(l => l.level === resultLevel.value)
  return item ? item.cn : ''
})

const resultEmoji = computed(() => {
  return { none: '🌟', mild: '🌿', moderate: '🍃', severe: '🌧️' }[resultLevel.value] || '✨'
})

const saveResult = async () => {
  const record = {
    student_id: studentId(),
    scale_id: currentScale.value.id,
    scale_name: currentScale.value.title,
    score: totalScore.value,
    level: resultLevel.value,
    level_cn: resultLevelCn.value
  }
  try {
    const res = await saveAssessmentRecord(record)
    if (res.code === 200) {
      await loadHistory()
      ElMessage.success('结果已保存')
    } else {
      ElMessage.error(res.msg || '保存失败')
    }
  } catch (e) {
    // 后端不可用时回退到本地存储，保证可用性
    historyList.value.unshift({ ...record, time: new Date().toLocaleString('zh-CN') })
    localStorage.setItem('assessment_history', JSON.stringify(historyList.value.slice(0, 20)))
    ElMessage.success('已保存到本地（未连接后端）')
  }
}

const loadHistory = async () => {
  try {
    const res = await getAssessmentRecords(studentId())
    if (res.code === 200) {
      historyList.value = res.data.map(h => ({
        ...h,
        time: (h.created_at || '').replace('T', ' ')
      }))
      return true
    }
  } catch (e) { /* 忽略 */ }
  // 兜底：读本地历史
  const saved = localStorage.getItem('assessment_history')
  if (saved) {
    try { historyList.value = JSON.parse(saved) } catch {}
  }
  return false
}

onMounted(loadHistory)

</script>

<style scoped>
.assessment-page {
  padding: 20px 30px;
  max-width: 900px;
  margin: 0 auto;
}

.assess-intro {
  text-align: center;
  padding: 30px 20px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, #f5f0ff 0%, #f0f8ff 100%);
  border-radius: 20px;
}

.intro-text h2 {
  margin: 0 0 8px 0;
  color: var(--brand-text);
}

.intro-text p {
  margin: 0;
  color: var(--brand-text-soft);
  font-size: 14px;
}

.scale-card {
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 20px;
}

.scale-card:hover {
  transform: translateY(-4px);
}

.scale-emoji {
  font-size: 48px;
  margin-bottom: 10px;
}

.scale-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--brand-text);
  margin-bottom: 6px;
}

.scale-desc {
  font-size: 13px;
  color: var(--brand-text-soft);
  margin-bottom: 12px;
}

.scale-meta {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.quiz-card {
  padding: 20px;
}

.quiz-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.quiz-progress {
  font-size: 14px;
  color: var(--brand-text-soft);
  min-width: 200px;
}

.mini-bar {
  height: 6px;
  background: rgba(92, 184, 149, 0.15);
  border-radius: 20px;
  margin-top: 6px;
  overflow: hidden;
}

.mini-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brand-primary-light), var(--brand-primary));
  border-radius: 20px;
  transition: width 0.3s ease;
}

.question-area {
  padding: 30px 20px;
  text-align: center;
}

.question-num {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 20px;
  background: var(--brand-bg-soft);
  color: var(--brand-primary-dark);
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 16px;
}

.question-text {
  font-size: 20px;
  font-weight: 600;
  color: var(--brand-text);
  margin-bottom: 10px;
}

.question-tip {
  font-size: 13px;
  color: var(--brand-text-soft);
  margin-bottom: 28px;
}

.option-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 500px;
  margin: 0 auto;
}

.option-group :deep(.el-radio) {
  margin-right: 0;
  width: 100%;
}

.option-group :deep(.el-radio__input.is-checked + .el-radio__label) {
  color: var(--brand-primary-dark);
}

.option-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border: 2px solid var(--brand-border);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.option-item:hover {
  border-color: var(--brand-primary-light);
  background: var(--brand-bg-soft);
}

.opt-label {
  font-size: 15px;
  font-weight: 500;
}

.opt-desc {
  font-size: 12px;
  color: var(--brand-text-muted);
}

.result-area {
  padding: 30px 20px;
  text-align: center;
  animation: fadeInUp 0.5s ease;
}

.result-emoji {
  font-size: 64px;
  margin-bottom: 10px;
}

.result-title {
  margin: 0 0 20px 0;
  color: var(--brand-text);
}

.result-score {
  display: inline-flex;
  align-items: baseline;
  padding: 16px 40px;
  border-radius: 20px;
  margin-bottom: 12px;
}

.score-none     { background: #e8f8f0; color: #5cb895; }
.score-mild     { background: #f0f8ff; color: #5b9bd5; }
.score-moderate { background: #fff4e4; color: #e2a86e; }
.score-severe   { background: #fef0f0; color: #e07a7a; }

.score-num {
  font-size: 52px;
  font-weight: bold;
  line-height: 1;
}

.score-unit {
  font-size: 18px;
  margin-left: 6px;
}

.result-level {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 14px;
}

.level-none     { color: #5cb895; }
.level-mild     { color: #5b9bd5; }
.level-moderate { color: #e2a86e; }
.level-severe   { color: #e07a7a; }

.result-desc {
  max-width: 500px;
  margin: 0 auto 20px;
  font-size: 14px;
  color: var(--brand-text-soft);
  line-height: 1.7;
}

.result-advice {
  background: var(--brand-bg-soft);
  border-radius: 14px;
  padding: 20px;
  max-width: 500px;
  margin: 0 auto 24px;
  text-align: left;
}

.advice-title {
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--brand-text);
}

.result-advice ul {
  margin: 0;
  padding-left: 20px;
  color: var(--brand-text-soft);
  font-size: 14px;
  line-height: 1.8;
}

.result-btns {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.history-section {
  margin-top: 30px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--brand-text);
  margin-bottom: 14px;
}

.history-card {
  padding: 10px 20px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px dashed var(--brand-border);
}

.history-item:last-child {
  border-bottom: none;
}

.history-scale {
  font-weight: 500;
  color: var(--brand-text);
}

.history-time {
  font-size: 12px;
  color: var(--brand-text-muted);
}

.history-result {
  font-size: 14px;
  font-weight: 500;
}

.result-none     { color: #5cb895; }
.result-mild     { color: #5b9bd5; }
.result-moderate { color: #e2a86e; }
.result-severe   { color: #e07a7a; }
</style>